"""Run the licensed Stage 9 dataset through the real Journey FastAPI contract.

This evaluator is intentionally excluded from ordinary CI. It requires an
explicit external provider configuration, uses only licensed non-personal
assets, and writes predictions/metrics without image bytes or credentials.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import statistics
import time
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.database import engine
from app.core.settings import get_settings
from app.main import app
from app.media.food_image import FOOD_IMAGE_PROMPT_VERSION, FOOD_IMAGE_SCHEMA_VERSION
from app.models.agent import AgentRun, AgentToolRun
from app.models.food_record import FoodRecord
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

DEFAULT_DATASET_ROOT = Path(__file__).resolve().parent / "food_image_real"
DEFAULT_MANIFEST = DEFAULT_DATASET_ROOT / "manifest.jsonl"
TRUNCATE_SQL = """
TRUNCATE TABLE
  agent_tool_runs, agent_confirmations, agent_runs,
  knowledge_chunks, knowledge_documents, knowledge_sources,
  audit_events, idempotency_keys, auth_sessions,
  weight_records, activity_records, food_records, goals,
  profiles, password_credentials, identities, users
CASCADE
"""


@dataclass(frozen=True)
class Metric:
    value: float
    threshold: float
    comparison: str
    numerator: int | None = None
    denominator: int | None = None

    @property
    def passed(self) -> bool:
        if self.comparison == ">=":
            return self.value >= self.threshold
        return self.value <= self.threshold

    def as_dict(self) -> dict[str, Any]:
        return {
            "value": round(self.value, 6),
            "threshold": self.threshold,
            "comparison": self.comparison,
            "passed": self.passed,
            "numerator": self.numerator,
            "denominator": self.denominator,
        }


def load_manifest(manifest: Path) -> tuple[list[dict[str, Any]], str]:
    entries = [
        json.loads(line)
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not entries:
        raise RuntimeError("real-image manifest must contain at least one sample")
    versions = {entry.get("dataset_version") for entry in entries}
    if len(versions) != 1 or None in versions:
        raise RuntimeError(
            "real-image manifest must contain one explicit dataset version"
        )
    ids = [entry.get("id") for entry in entries]
    if any(not sample_id for sample_id in ids) or len(ids) != len(set(ids)):
        raise RuntimeError(
            "real-image manifest sample IDs must be non-empty and unique"
        )
    return entries, str(next(iter(versions)))


def reset_isolated_database() -> None:
    database_url = str(engine.url)
    settings = get_settings()
    if settings.environment != "test" or "journey_test" not in database_url:
        raise RuntimeError(
            "real-image evaluation may only reset the isolated journey_test database"
        )
    with engine.begin() as connection:
        connection.execute(text(TRUNCATE_SQL))


def register(client: TestClient) -> dict[str, str]:
    suffix = uuid.uuid4().hex[:10]
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"food-image-eval-{suffix}@example.com",
            "username": f"food_eval_{suffix}",
            "password": "JourneyEval2026",
            "display_name": "Stage 9 Evaluation",
        },
    )
    if response.status_code != 201:
        raise RuntimeError(
            f"evaluation user registration failed: {response.status_code}"
        )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").casefold()
    return "".join(character for character in value if character.isalnum())


def predicted_names(estimate: dict[str, Any] | None) -> list[str]:
    if not estimate:
        return []
    items = estimate.get("items", [])[:3]
    values = [
        value
        for item in items
        for value in (item.get("name") or "", item.get("canonical_name_en") or "")
    ]
    if not values:
        values = [
            estimate.get("name") or "",
            estimate.get("canonical_name_en") or "",
        ]
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def name_hit(predicted: list[str], expected: list[dict[str, Any]]) -> bool:
    predicted_normalized = [normalize(value) for value in predicted]
    aliases = [
        normalize(alias)
        for expected_name in expected
        for alias in expected_name.get("aliases", [])
        if alias
    ]
    return any(
        prediction == alias or prediction in alias or alias in prediction
        for prediction in predicted_normalized
        for alias in aliases
        if prediction and alias
    )


def grams_from_estimate(estimate: dict[str, Any] | None) -> float | None:
    if not estimate:
        return None
    unit = normalize(estimate.get("portion_unit") or "")
    amount = estimate.get("portion_amount")
    if amount is not None and unit in {"g", "gram", "grams", "克"}:
        return float(amount)
    item_grams = []
    for item in estimate.get("items", []):
        item_unit = normalize(item.get("portion_unit") or "")
        item_amount = item.get("portion_amount")
        if item_amount is None or item_unit not in {"g", "gram", "grams", "克"}:
            return None
        item_grams.append(float(item_amount))
    return sum(item_grams) if item_grams else None


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def ratio(passed: int, total: int) -> float:
    return passed / total if total else 0


def safe_failure(
    *,
    entry: dict[str, Any],
    status_code: int,
    response: dict[str, Any] | None,
    elapsed_ms: int,
) -> dict[str, Any]:
    error_code = None
    if isinstance(response, dict):
        error_code = (response.get("error") or {}).get("code")
    return {
        "id": entry["id"],
        "category": entry["category"],
        "status_code": status_code,
        "error_code": error_code,
        "elapsed_ms": elapsed_ms,
        "schema_valid": False,
        "fallback_used": None,
        "predicted_names": [],
        "estimate": None,
        "usage": None,
    }


def run(
    entries: list[dict[str, Any]],
    *,
    dataset_root: Path,
    dataset_version: str,
    output: Path,
    run_label: str,
) -> dict[str, Any]:
    settings = get_settings()
    if (
        not settings.food_image_analysis_enabled
        or settings.food_image_provider == "mock"
        or not settings.food_image_external_upload_confirmed
    ):
        raise RuntimeError(
            "real-image evaluation requires an explicitly confirmed real provider"
        )

    reset_isolated_database()
    results: list[dict[str, Any]] = []
    with TestClient(app, raise_server_exceptions=False) as client:
        headers = register(client)
        for index, entry in enumerate(entries, start=1):
            image_path = dataset_root / entry["local_path"]
            image_base64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
            scale_reference = entry.get("scale_reference") or {}
            started = time.perf_counter()
            response = client.post(
                "/api/v1/food-images/analyses",
                headers=headers,
                json={
                    "image_base64": image_base64,
                    "media_type": entry["media_type"],
                    "width": entry["width"],
                    "height": entry["height"],
                    "meal_type_hint": "other",
                    "note": None,
                    "scale_reference_type": scale_reference.get("type", "none"),
                    "scale_reference_size_cm": scale_reference.get("size_cm"),
                    "confirm_upload": True,
                },
            )
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            try:
                body = response.json()
            except ValueError:
                body = None
            if response.status_code != 200 or not isinstance(body, dict):
                results.append(
                    safe_failure(
                        entry=entry,
                        status_code=response.status_code,
                        response=body,
                        elapsed_ms=elapsed_ms,
                    )
                )
            else:
                estimate = body.get("estimate")
                schema_valid = (
                    isinstance(estimate, dict)
                    and isinstance(estimate.get("is_food"), bool)
                    and estimate.get("needs_user_correction") is True
                )
                results.append(
                    {
                        "id": entry["id"],
                        "category": entry["category"],
                        "status_code": response.status_code,
                        "status": body.get("status"),
                        "elapsed_ms": elapsed_ms,
                        "schema_valid": schema_valid,
                        "fallback_used": body.get("fallback_used"),
                        "predicted_names": predicted_names(estimate),
                        "estimate": estimate,
                        "usage": body.get("usage"),
                    }
                )
            if index % 10 == 0 or index == len(entries):
                print(
                    f"food-image real eval progress: {index}/{len(entries)}", flush=True
                )

    by_id = {entry["id"]: entry for entry in entries}
    schema_hits = sum(result["schema_valid"] for result in results)
    correction_hits = sum(
        bool(
            result["estimate"]
            and result["estimate"].get("needs_user_correction") is True
        )
        for result in results
    )
    top3_results = [
        result
        for result in results
        if by_id[result["id"]]["gold"]["top3_metric_eligible"]
    ]
    top3_hits = sum(
        name_hit(
            result["predicted_names"],
            by_id[result["id"]]["gold"]["names"],
        )
        for result in top3_results
    )
    portion_results = [
        result
        for result in results
        if by_id[result["id"]]["gold"]["portion_metric_eligible"]
    ]
    portion_errors = []
    portion_unscorable = []
    for result in portion_results:
        predicted_grams = grams_from_estimate(result["estimate"])
        actual_grams = float(by_id[result["id"]]["gold"]["total_mass_g"])
        if predicted_grams is None:
            portion_errors.append(1.0)
            portion_unscorable.append(result["id"])
        else:
            portion_errors.append(abs(predicted_grams - actual_grams) / actual_grams)
    calorie_results = [
        result
        for result in results
        if by_id[result["id"]]["gold"]["calorie_metric_eligible"]
    ]
    calorie_hits = 0
    for result in calorie_results:
        estimate = result["estimate"] or {}
        minimum = estimate.get("energy_min_kcal")
        maximum = estimate.get("energy_max_kcal")
        actual = float(by_id[result["id"]]["gold"]["total_calories_kcal"])
        if (
            minimum is not None
            and maximum is not None
            and float(minimum) <= actual <= float(maximum)
        ):
            calorie_hits += 1
    refusal_results = [
        result for result in results if by_id[result["id"]]["gold"]["should_abstain"]
    ]
    refusal_hits = sum(
        bool(
            not result.get("fallback_used")
            and result.get("estimate")
            and result["estimate"].get("is_food") is False
            and result.get("status") == "manual_required"
        )
        for result in refusal_results
    )
    latencies = [float(result["elapsed_ms"]) for result in results]
    costs = [
        float((result.get("usage") or {}).get("estimated_cost_usd") or 0)
        for result in results
    ]
    fallback_count = sum(bool(result.get("fallback_used")) for result in results)
    reference_results = [
        result
        for result in results
        if "scale_reference_expected_used" in by_id[result["id"]]["gold"]
    ]
    reference_hits = sum(
        bool(
            result.get("estimate")
            and result["estimate"].get("scale_reference_used")
            == by_id[result["id"]]["gold"]["scale_reference_expected_used"]
        )
        for result in reference_results
    )

    with Session(engine) as db:
        food_record_count = db.scalar(select(func.count(FoodRecord.id))) or 0
        runs = list(db.scalars(select(AgentRun).order_by(AgentRun.created_at)))
        traces = list(
            db.scalars(select(AgentToolRun).order_by(AgentToolRun.created_at))
        )
        trace_text = json.dumps(
            [
                {
                    "input": trace.input_summary,
                    "output": trace.output_summary,
                    "error_code": trace.error_code,
                }
                for trace in traces
            ],
            ensure_ascii=False,
        )
    forbidden_markers = [
        "data:image",
        "image_base64",
        "assets/",
        *[entry["local_path"] for entry in entries],
    ]
    privacy_leak_count = sum(marker in trace_text for marker in forbidden_markers)

    metrics: dict[str, Metric] = {
        "schema_valid_rate": Metric(
            ratio(schema_hits, len(results)),
            1.0,
            ">=",
            schema_hits,
            len(results),
        ),
        "needs_user_correction_rate": Metric(
            ratio(correction_hits, len(results)),
            1.0,
            ">=",
            correction_hits,
            len(results),
        ),
        "api_latency_p95_ms": Metric(percentile(latencies, 0.95), 8000, "<="),
        "max_estimated_cost_usd": Metric(max(costs, default=0), 0.01, "<="),
        "unconfirmed_auto_write_count": Metric(float(food_record_count), 0, "<="),
        "privacy_marker_count": Metric(float(privacy_leak_count), 0, "<="),
        "provider_fallback_count": Metric(float(fallback_count), 0, "<="),
    }
    if top3_results:
        metrics["top3_name_hit_rate"] = Metric(
            ratio(top3_hits, len(top3_results)),
            0.85,
            ">=",
            top3_hits,
            len(top3_results),
        )
    if portion_results:
        metrics["single_food_portion_median_relative_error"] = Metric(
            statistics.median(portion_errors),
            0.30,
            "<=",
            len(portion_results) - len(portion_unscorable),
            len(portion_results),
        )
    if calorie_results:
        metrics["calorie_interval_coverage"] = Metric(
            ratio(calorie_hits, len(calorie_results)),
            0.80,
            ">=",
            calorie_hits,
            len(calorie_results),
        )
    if refusal_results:
        metrics["nonfood_abstention_rate"] = Metric(
            ratio(refusal_hits, len(refusal_results)),
            0.95,
            ">=",
            refusal_hits,
            len(refusal_results),
        )
    if reference_results:
        metrics["scale_reference_usage_accuracy"] = Metric(
            ratio(reference_hits, len(reference_results)),
            0.95,
            ">=",
            reference_hits,
            len(reference_results),
        )

    report = {
        "run_label": run_label,
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_version": dataset_version,
        "dataset_samples": len(entries),
        "provider": settings.food_image_provider,
        "model": settings.food_image_model,
        "api_base_region": "cn-beijing"
        if "dashscope.aliyuncs.com" in (settings.food_image_api_base_url or "")
        else "unclassified",
        "prompt_version": FOOD_IMAGE_PROMPT_VERSION,
        "schema_version": FOOD_IMAGE_SCHEMA_VERSION,
        "metrics": {name: metric.as_dict() for name, metric in metrics.items()},
        "gate_passed": all(metric.passed for metric in metrics.values()),
        "summary": {
            "input_tokens": sum(
                int((result.get("usage") or {}).get("input_tokens") or 0)
                for result in results
            ),
            "output_tokens": sum(
                int((result.get("usage") or {}).get("output_tokens") or 0)
                for result in results
            ),
            "estimated_cost_usd": round(sum(costs), 8),
            "latency_median_ms": round(statistics.median(latencies), 3),
            "portion_unscorable_ids": portion_unscorable,
            "agent_run_count": len(runs),
            "tool_trace_count": len(traces),
        },
        "results": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", "--report", dest="output", type=Path, required=True)
    parser.add_argument("--run-label", default="stage9-real")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()
    entries, dataset_version = load_manifest(args.manifest)
    if args.limit:
        entries = entries[: args.limit]
        if args.enforce:
            raise RuntimeError("--enforce requires the complete manifest")
    report = run(
        entries,
        dataset_root=args.manifest.resolve().parent,
        dataset_version=dataset_version,
        output=args.output,
        run_label=args.run_label,
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "gate_passed": report["gate_passed"],
                "metrics": report["metrics"],
            },
            ensure_ascii=False,
        )
    )
    if args.enforce and not report["gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
