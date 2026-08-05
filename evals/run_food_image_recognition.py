"""Run ADR-031's sealed recognition-only holdout exactly once.

The evaluator is isolated from Journey's public API and database. It sends only
the sealed, licensed images to the frozen Qwen snapshot, never sends gold
labels, and records no image bytes, credentials, or raw model text.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import re
import statistics
import time
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from app.agent.provider_profiles import get_provider_profile, litellm_model_name
from app.core.settings import Settings, get_settings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_litellm import ChatLiteLLMRouter
from litellm import Router as LiteLLMRouter
from pydantic import BaseModel, ConfigDict, Field, model_validator

DEFAULT_DATASET_ROOT = (
    Path(__file__).resolve().parent / "food_image_recognition_holdout"
)
DEFAULT_MANIFEST = DEFAULT_DATASET_ROOT / "manifest.jsonl"
DEFAULT_RECEIPT = DEFAULT_DATASET_ROOT / "run_receipt.json"
DEFAULT_STATE = (
    Path(__file__).resolve().parent.parent
    / "artifacts"
    / "food-image-recognition"
    / "formal-run-state.json"
)

DATASET_VERSION = "journey-food-image-recognition-holdout-v2"
PROMPT_VERSION = "journey-food-image-recognition-eval-1.0.0"
SCHEMA_VERSION = "journey-food-image-recognition-schema-1"
SCORE_VERSION = "journey-food-image-recognition-score-1.0.0"
MODEL_ALIAS = "qwen3.7-flash"
MODEL_SNAPSHOT = "qwen3.7-flash-2026-07-15"
EXPECTED_SAMPLES = 60
EXPECTED_COHORTS = {
    "chinese_home_meal": 20,
    "single_food": 15,
    "mixed_meal": 10,
    "packaged_food": 10,
    "nonfood": 5,
}
EXPECTED_ENDPOINT = "https://dashscope.aliyuncs.com/compatible-mode/v1"
CNY_PER_USD = 7.2
OFFICIAL_INPUT_USD_PER_MILLION = 0.2 / CNY_PER_USD
OFFICIAL_OUTPUT_USD_PER_MILLION = 0.8 / CNY_PER_USD
MAX_DAILY_BUDGET_USD = 1.0 / CNY_PER_USD

SYSTEM_PROMPT = (
    "你是 Journey 的食物名称识别评测器，只识别图片中的食物，不分析人物、身体、身份或"
    "健康状况。仅输出一个 JSON 对象，不要 Markdown。严格使用这些键："
    "is_food；candidates；confidence；should_abstain；needs_user_correction。"
    "candidates 最多 3 项，每项严格使用 name_zh、name_en、confidence；confidence 只能是"
    " low 或 medium。若图片主要内容不是食物，is_food=false、candidates=[]、"
    "should_abstain=true；否则 is_food=true、should_abstain=false。"
    "needs_user_correction 必须为 true。禁止输出、猜测或暗示克重、份量、体积、热量、"
    "营养素、价格或医学结论，也不要声称结果已经自动写入。"
)
USER_INSTRUCTION = (
    "识别这张图片中的食物，按最可能顺序给出不超过 3 个通用名称候选。"
    "混合餐优先给出整道菜或餐食名称；不确定时保持 low/medium 并要求用户确认。"
)


class FoodCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name_zh: str = Field(min_length=1, max_length=80)
    name_en: str = Field(default="", max_length=80)
    confidence: Literal["low", "medium"]


class RecognitionPrediction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_food: bool
    candidates: list[FoodCandidate] = Field(max_length=3)
    confidence: Literal["low", "medium"]
    should_abstain: bool
    needs_user_correction: Literal[True]

    @model_validator(mode="after")
    def consistent_food_state(self) -> RecognitionPrediction:
        if self.is_food:
            if self.should_abstain or not self.candidates:
                raise ValueError(
                    "food responses require candidates and may not abstain"
                )
        elif not self.should_abstain or self.candidates:
            raise ValueError("nonfood responses must abstain with no candidates")
        return self


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def metric(
    value: float,
    threshold: float,
    comparison: Literal[">=", "<="],
    *,
    numerator: int | None = None,
    denominator: int | None = None,
) -> dict[str, Any]:
    passed = value >= threshold if comparison == ">=" else value <= threshold
    return {
        "value": round(value, 6),
        "threshold": threshold,
        "comparison": comparison,
        "passed": passed,
        "numerator": numerator,
        "denominator": denominator,
    }


def load_and_verify_manifest(path: Path) -> tuple[list[dict[str, Any]], str]:
    raw = path.read_bytes()
    entries = read_jsonl(path)
    if len(entries) != EXPECTED_SAMPLES:
        raise RuntimeError(
            f"expected {EXPECTED_SAMPLES} sealed samples, found {len(entries)}"
        )
    if {entry.get("dataset_version") for entry in entries} != {DATASET_VERSION}:
        raise RuntimeError("recognition holdout dataset version changed")
    if len({entry.get("id") for entry in entries}) != len(entries):
        raise RuntimeError("recognition holdout contains duplicate sample IDs")

    cohorts: dict[str, int] = {}
    dataset_root = path.resolve().parent
    for entry in entries:
        cohorts[entry["cohort"]] = cohorts.get(entry["cohort"], 0) + 1
        if (
            not entry.get("sealed")
            or entry.get("holdout_role") != "sealed_recognition_only"
            or entry.get("prompt_tuning_allowed") is not False
        ):
            raise RuntimeError(
                f"sample is not sealed against prompt tuning: {entry['id']}"
            )
        if (
            entry["privacy_review"].get("status") != "passed"
            or entry["visual_qa"].get("status") != "passed"
        ):
            raise RuntimeError(f"sample QA changed: {entry['id']}")
        if (
            entry["gold"].get("model_must_not_output_mass") is not True
            or entry["gold"].get("model_must_not_output_calorie_point_estimate")
            is not True
        ):
            raise RuntimeError(f"recognition-only gold boundary changed: {entry['id']}")
        if not entry["source"].get("license_url") or not entry["source"].get(
            "source_page"
        ):
            raise RuntimeError(f"source/license evidence missing: {entry['id']}")
        image = (dataset_root / entry["local_path"]).read_bytes()
        if sha256(image) != entry["sha256"]:
            raise RuntimeError(f"asset hash mismatch: {entry['id']}")
    if cohorts != EXPECTED_COHORTS:
        raise RuntimeError(f"cohort composition changed: {cohorts}")
    return entries, sha256(raw)


def provider_ready(settings: Settings, max_estimated_cost_usd: float) -> None:
    if settings.food_image_provider != "qwen":
        raise RuntimeError(
            "recognition evaluation is frozen to FOOD_IMAGE_PROVIDER=qwen"
        )
    if settings.food_image_model not in {MODEL_ALIAS, MODEL_SNAPSHOT}:
        raise RuntimeError(
            f"recognition evaluation requires {MODEL_ALIAS} or {MODEL_SNAPSHOT}"
        )
    if settings.food_image_api_base_url != EXPECTED_ENDPOINT:
        raise RuntimeError(
            "recognition evaluation requires the confirmed Beijing endpoint"
        )
    if not settings.food_image_external_upload_confirmed:
        raise RuntimeError("external image upload must be explicitly confirmed")
    if not settings.food_image_api_key:
        raise RuntimeError("a confirmed Qwen API key is required")
    if not math.isclose(
        settings.food_image_input_usd_per_million,
        OFFICIAL_INPUT_USD_PER_MILLION,
        rel_tol=0,
        abs_tol=0.000001,
    ):
        raise RuntimeError(
            "Qwen input pricing does not match the reviewed Beijing price"
        )
    if not math.isclose(
        settings.food_image_output_usd_per_million,
        OFFICIAL_OUTPUT_USD_PER_MILLION,
        rel_tol=0,
        abs_tol=0.000001,
    ):
        raise RuntimeError(
            "Qwen output pricing does not match the reviewed Beijing price"
        )
    if (
        settings.food_image_daily_budget_usd <= 0
        or settings.food_image_daily_budget_usd > MAX_DAILY_BUDGET_USD + 0.000001
    ):
        raise RuntimeError("food image daily budget must remain at or below CNY 1")
    if max_estimated_cost_usd <= 0:
        raise RuntimeError("run cost cap must be positive")
    if max_estimated_cost_usd > settings.food_image_daily_budget_usd:
        raise RuntimeError("run cost cap cannot exceed the configured daily budget")


def build_chat(settings: Settings) -> ChatLiteLLMRouter:
    profile = get_provider_profile(settings.food_image_provider)
    route_name = f"journey-recognition-eval-{MODEL_SNAPSHOT}"
    params: dict[str, Any] = {
        "model": litellm_model_name(profile, MODEL_SNAPSHOT),
        "api_key": settings.food_image_api_key,
        "api_base": settings.food_image_api_base_url,
        "timeout": settings.agent_timeout_seconds,
        "max_retries": 0,
        "max_tokens": 300,
        "temperature": 0,
        "seed": 1234,
        "extra_body": {"enable_thinking": False},
    }
    router = LiteLLMRouter(
        model_list=[{"model_name": route_name, "litellm_params": params}],
        num_retries=0,
        max_fallbacks=0,
        timeout=settings.agent_timeout_seconds,
        cache_responses=False,
        disable_cooldowns=True,
    )
    return ChatLiteLLMRouter(
        router=router,
        model=route_name,
        temperature=0,
        request_timeout=settings.agent_timeout_seconds,
        max_retries=0,
    )


def raw_json_object(raw: object) -> dict[str, Any] | None:
    content = getattr(raw, "content", None)
    if isinstance(content, dict):
        return content
    if isinstance(content, list):
        content = "".join(
            str(item.get("text") or "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        )
    if not isinstance(content, str):
        return None
    candidate = content.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        candidate = "\n".join(lines[1:-1]).strip()
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def contains_forbidden_estimate(value: object) -> bool:
    forbidden_keys = {
        "mass",
        "massg",
        "weight",
        "grams",
        "portion",
        "portionmassg",
        "calorie",
        "calories",
        "kcal",
        "energy",
        "nutrition",
        "nutrients",
        "克重",
        "重量",
        "份量",
        "热量",
        "营养",
    }
    forbidden_value_markers = ("kcal", "千卡", "大卡", "克重", "重量")
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = "".join(
                character for character in key.casefold() if character.isalnum()
            )
            if normalized in forbidden_keys or contains_forbidden_estimate(item):
                return True
    elif isinstance(value, list):
        return any(contains_forbidden_estimate(item) for item in value)
    elif isinstance(value, str):
        lowered = value.casefold()
        return any(marker in lowered for marker in forbidden_value_markers) or bool(
            re.search(r"\d+(?:\.\d+)?\s*(?:g|克|kcal|千卡|大卡)\b", lowered)
        )
    return False


def invoke(
    *,
    chat: ChatLiteLLMRouter,
    settings: Settings,
    image_path: Path,
    media_type: str,
) -> dict[str, Any]:
    data_url = (
        f"data:{media_type};base64,"
        f"{base64.b64encode(image_path.read_bytes()).decode('ascii')}"
    )
    started = time.perf_counter()
    input_tokens = 0
    output_tokens = 0
    estimated_cost = 0.0
    try:
        result = chat.with_structured_output(
            RecognitionPrediction,
            method="json_mode",
            include_raw=True,
        ).invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(
                    content=[
                        {"type": "text", "text": USER_INSTRUCTION},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ]
                ),
            ]
        )
        raw = result.get("raw") if isinstance(result, dict) else None
        usage = getattr(raw, "usage_metadata", None) or {}
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        estimated_cost = (
            input_tokens * settings.food_image_input_usd_per_million
            + output_tokens * settings.food_image_output_usd_per_million
        ) / 1_000_000
        raw_object = raw_json_object(raw)
        forbidden = contains_forbidden_estimate(raw_object)
        parsed = result.get("parsed") if isinstance(result, dict) else None
        if not isinstance(parsed, RecognitionPrediction):
            parsed = RecognitionPrediction.model_validate(raw_object)
        if forbidden:
            raise ValueError("forbidden mass/calorie estimate detected")
        response_metadata = getattr(raw, "response_metadata", None) or {}
        return {
            "schema_valid": True,
            "forbidden_estimate_detected": False,
            "fallback_used": False,
            "error_code": None,
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "provider_response_model": response_metadata.get("model_name")
            or response_metadata.get("model"),
            "prediction": parsed.model_dump(mode="json"),
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost_usd": round(estimated_cost, 8),
            },
        }
    except Exception as error:  # Provider/transport/schema errors are scored failures.
        return {
            "schema_valid": False,
            "forbidden_estimate_detected": "forbidden mass/calorie" in str(error),
            "fallback_used": True,
            "error_code": type(error).__name__,
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "provider_response_model": None,
            "prediction": None,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost_usd": round(estimated_cost, 8),
            },
        }


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").casefold()
    return "".join(character for character in value if character.isalnum())


def predicted_names(result: dict[str, Any]) -> list[str]:
    prediction = result.get("prediction") or {}
    return [
        value
        for candidate in prediction.get("candidates") or []
        for value in (candidate.get("name_zh") or "", candidate.get("name_en") or "")
        if value
    ]


def name_hit(predicted: list[str], expected: list[dict[str, Any]]) -> bool:
    predictions = [normalize(value) for value in predicted if value]
    aliases = [
        normalize(value)
        for name in expected
        for value in [name.get("canonical_en") or "", *(name.get("aliases") or [])]
        if value
    ]
    return any(
        prediction == alias or prediction in alias or alias in prediction
        for prediction in predictions
        for alias in aliases
        if prediction and alias
    )


def score(
    entries: list[dict[str, Any]],
    results: list[dict[str, Any]],
    *,
    max_estimated_cost_usd: float,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    by_id = {entry["id"]: entry for entry in entries}
    if len(results) != EXPECTED_SAMPLES or len(
        {result["id"] for result in results}
    ) != len(results):
        raise RuntimeError("score requires exactly one result for every sealed sample")

    schema_hits = sum(bool(result["schema_valid"]) for result in results)
    correction_hits = sum(
        bool(
            result.get("prediction")
            and result["prediction"].get("needs_user_correction") is True
        )
        for result in results
    )
    forbidden_free_hits = sum(
        bool(result.get("schema_valid"))
        and not bool(result.get("forbidden_estimate_detected"))
        for result in results
    )
    food_results = [
        result
        for result in results
        if by_id[result["id"]]["gold"]["top3_metric_eligible"]
    ]
    food_hits = sum(
        name_hit(predicted_names(result), by_id[result["id"]]["gold"]["names"])
        for result in food_results
    )
    chinese_results = [
        result
        for result in food_results
        if by_id[result["id"]]["cohort"] == "chinese_home_meal"
    ]
    chinese_hits = sum(
        name_hit(predicted_names(result), by_id[result["id"]]["gold"]["names"])
        for result in chinese_results
    )
    nonfood_results = [
        result for result in results if by_id[result["id"]]["gold"]["should_abstain"]
    ]
    nonfood_hits = sum(
        bool(
            result.get("prediction")
            and result["prediction"].get("is_food") is False
            and result["prediction"].get("should_abstain") is True
            and result["prediction"].get("candidates") == []
        )
        for result in nonfood_results
    )
    fallback_count = sum(bool(result["fallback_used"]) for result in results)
    latencies = [float(result["latency_ms"]) for result in results]
    costs = [float(result["usage"]["estimated_cost_usd"]) for result in results]
    usage_hits = sum(
        int(result["usage"]["input_tokens"]) > 0
        and int(result["usage"]["output_tokens"]) > 0
        for result in results
    )
    total_cost = sum(costs)

    metrics = {
        "schema_valid_rate": metric(
            schema_hits / EXPECTED_SAMPLES,
            1.0,
            ">=",
            numerator=schema_hits,
            denominator=EXPECTED_SAMPLES,
        ),
        "needs_user_correction_rate": metric(
            correction_hits / EXPECTED_SAMPLES,
            1.0,
            ">=",
            numerator=correction_hits,
            denominator=EXPECTED_SAMPLES,
        ),
        "forbidden_estimate_free_rate": metric(
            forbidden_free_hits / EXPECTED_SAMPLES,
            1.0,
            ">=",
            numerator=forbidden_free_hits,
            denominator=EXPECTED_SAMPLES,
        ),
        "overall_food_top3_name_hit_rate": metric(
            food_hits / len(food_results),
            0.85,
            ">=",
            numerator=food_hits,
            denominator=len(food_results),
        ),
        "chinese_home_meal_top3_name_hit_rate": metric(
            chinese_hits / len(chinese_results),
            0.80,
            ">=",
            numerator=chinese_hits,
            denominator=len(chinese_results),
        ),
        "nonfood_abstention_rate": metric(
            nonfood_hits / len(nonfood_results),
            0.95,
            ">=",
            numerator=nonfood_hits,
            denominator=len(nonfood_results),
        ),
        "provider_fallback_count": metric(float(fallback_count), 0, "<="),
        "latency_p95_ms": metric(percentile(latencies, 0.95), 8_000, "<="),
        "usage_capture_rate": metric(
            usage_hits / EXPECTED_SAMPLES,
            1.0,
            ">=",
            numerator=usage_hits,
            denominator=EXPECTED_SAMPLES,
        ),
        "total_estimated_cost_usd": metric(
            total_cost,
            max_estimated_cost_usd,
            "<=",
        ),
        "unconfirmed_auto_write_count": metric(0.0, 0, "<="),
    }
    summary = {
        "input_tokens": sum(result["usage"]["input_tokens"] for result in results),
        "output_tokens": sum(result["usage"]["output_tokens"] for result in results),
        "estimated_cost_usd_recorded": round(total_cost, 8),
        "estimated_cost_usd_complete": usage_hits == EXPECTED_SAMPLES,
        "usage_missing_calls": EXPECTED_SAMPLES - usage_hits,
        "latency_median_ms": round(statistics.median(latencies), 3),
        "provider_calls": len(results),
        "valid_predictions": schema_hits,
        "fallback_count": fallback_count,
    }
    return metrics, summary


def run_fingerprint(
    *,
    manifest_sha256: str,
    max_estimated_cost_usd: float,
) -> dict[str, Any]:
    return {
        "dataset_version": DATASET_VERSION,
        "manifest_sha256": manifest_sha256,
        "model": MODEL_SNAPSHOT,
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": sha256((SYSTEM_PROMPT + USER_INSTRUCTION).encode()),
        "schema_version": SCHEMA_VERSION,
        "schema_sha256": sha256(
            json.dumps(
                RecognitionPrediction.model_json_schema(),
                ensure_ascii=False,
                sort_keys=True,
            ).encode()
        ),
        "max_estimated_cost_usd": max_estimated_cost_usd,
    }


def atomic_json_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def load_or_create_state(
    path: Path,
    fingerprint: dict[str, Any],
) -> dict[str, Any]:
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("fingerprint") != fingerprint:
            raise RuntimeError(
                "existing formal-run state belongs to a different evaluation"
            )
        if state.get("status") == "completed":
            raise RuntimeError("formal recognition evaluation is already completed")
        return state
    state = {
        "status": "in_progress",
        "started_at": datetime.now(UTC).isoformat(),
        "fingerprint": fingerprint,
        "results": [],
    }
    atomic_json_write(path, state)
    return state


def execute(
    *,
    entries: list[dict[str, Any]],
    dataset_root: Path,
    manifest_sha256: str,
    output: Path,
    receipt: Path,
    state_path: Path,
    max_estimated_cost_usd: float,
) -> dict[str, Any]:
    if output.exists():
        raise RuntimeError(f"refusing to overwrite one-run report: {output}")
    if receipt.exists():
        raise RuntimeError(f"formal recognition run receipt already exists: {receipt}")
    settings = get_settings()
    provider_ready(settings, max_estimated_cost_usd)
    fingerprint = run_fingerprint(
        manifest_sha256=manifest_sha256,
        max_estimated_cost_usd=max_estimated_cost_usd,
    )
    state = load_or_create_state(state_path, fingerprint)
    results = list(state.get("results") or [])
    completed_ids = {result["id"] for result in results}
    if len(completed_ids) != len(results):
        raise RuntimeError("formal-run state contains duplicate sample results")
    if not completed_ids <= {entry["id"] for entry in entries}:
        raise RuntimeError("formal-run state contains an unknown sample")
    spent = sum(float(result["usage"]["estimated_cost_usd"]) for result in results)
    if spent > max_estimated_cost_usd:
        raise RuntimeError("resumed formal run already exceeds its cost cap")

    chat = build_chat(settings)
    for entry in entries:
        if entry["id"] in completed_ids:
            continue
        result = invoke(
            chat=chat,
            settings=settings,
            image_path=dataset_root / entry["local_path"],
            media_type=entry["media_type"],
        )
        result = {
            "id": entry["id"],
            "cohort": entry["cohort"],
            "gold_names": entry["gold"]["names"],
            "gold_should_abstain": entry["gold"]["should_abstain"],
            **result,
        }
        results.append(result)
        spent += float(result["usage"]["estimated_cost_usd"])
        if spent > max_estimated_cost_usd:
            raise RuntimeError("formal recognition run exceeded its estimated cost cap")
        state["results"] = results
        atomic_json_write(state_path, state)
        print(
            json.dumps(
                {
                    "progress": f"{len(results)}/{EXPECTED_SAMPLES}",
                    "estimated_cost_usd": round(spent, 8),
                    "schema_valid": result["schema_valid"],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

    metrics, summary = score(
        entries,
        results,
        max_estimated_cost_usd=max_estimated_cost_usd,
    )
    report = {
        "run_label": "stage9-qwen-recognition-v2",
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_version": DATASET_VERSION,
        "dataset_samples": len(entries),
        "provider": settings.food_image_provider,
        "configured_model": settings.food_image_model,
        "model": MODEL_SNAPSHOT,
        "api_base_region": "cn-beijing",
        "adapter_scope": "isolated_recognition_evaluation_only_public_api_unchanged",
        **fingerprint,
        "score_version": SCORE_VERSION,
        "sealed_holdout_prompt_tuning_allowed": False,
        "automatic_database_writes": 0,
        "metrics": metrics,
        "gate_passed": all(value["passed"] for value in metrics.values()),
        "summary": summary,
        "results": results,
    }
    atomic_json_write(output, report)
    report_hash = sha256(output.read_bytes())
    completed_at = datetime.now(UTC).isoformat()
    receipt_value = {
        "status": "completed",
        "completed_at": completed_at,
        "dataset_version": DATASET_VERSION,
        "manifest_sha256": manifest_sha256,
        "report_file": output.name,
        "report_sha256": report_hash,
        "provider_calls": len(results),
        "model": MODEL_SNAPSHOT,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "gate_passed": report["gate_passed"],
    }
    atomic_json_write(receipt, receipt_value)
    state["status"] = "completed"
    state["completed_at"] = completed_at
    state["report_sha256"] = report_hash
    atomic_json_write(state_path, state)
    return report


def dry_run(manifest: Path, max_estimated_cost_usd: float) -> dict[str, Any]:
    entries, manifest_hash = load_and_verify_manifest(manifest)
    settings = get_settings()
    provider_ready(settings, max_estimated_cost_usd)
    return {
        "status": "dry_run_passed_no_provider_calls",
        "dataset_version": DATASET_VERSION,
        "manifest_sha256": manifest_hash,
        "samples": len(entries),
        "planned_calls": len(entries),
        "provider": settings.food_image_provider,
        "configured_model": settings.food_image_model,
        "frozen_model": MODEL_SNAPSHOT,
        "api_base_region": "cn-beijing",
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "max_estimated_cost_usd": max_estimated_cost_usd,
        "configured_daily_budget_usd": settings.food_image_daily_budget_usd,
        "provider_calls": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--max-estimated-cost-usd", type=float, default=0.02)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        print(
            json.dumps(
                dry_run(args.manifest, args.max_estimated_cost_usd),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return
    if args.output is None:
        parser.error("--output is required with --execute")

    entries, manifest_hash = load_and_verify_manifest(args.manifest)
    dataset_root = args.manifest.resolve().parent
    report = execute(
        entries=entries,
        dataset_root=dataset_root,
        manifest_sha256=manifest_hash,
        output=args.output,
        receipt=args.receipt,
        state_path=args.state,
        max_estimated_cost_usd=args.max_estimated_cost_usd,
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "gate_passed": report["gate_passed"],
                "metrics": report["metrics"],
                "summary": report["summary"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
