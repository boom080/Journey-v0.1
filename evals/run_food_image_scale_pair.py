"""Run the sealed centimeter-ruler holdout through an isolated Qwen adapter.

This evaluator deliberately does not call Journey's public API and does not
extend the production scale-reference enum. It may run once against the sealed
v1 holdout after a no-provider dry-run has passed.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from app.agent.provider_profiles import get_provider_profile, litellm_model_name
from app.core.settings import Settings, get_settings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_litellm import ChatLiteLLMRouter
from litellm import Router as LiteLLMRouter
from pydantic import BaseModel, Field

DEFAULT_DATASET_ROOT = Path(__file__).resolve().parent / "food_image_scale_holdout"
DEFAULT_MANIFEST = DEFAULT_DATASET_ROOT / "manifest.jsonl"
PROMPT_VERSION = "journey-food-image-scale-ruler-eval-1.0.0"
SCHEMA_VERSION = "journey-food-image-scale-ruler-schema-1"
EXPECTED_PAIRS = 30
EXPECTED_CALLS = 60

SYSTEM_PROMPT = (
    "你是 Journey 的食物份量隔离评测器，只分析食物，不分析人物、身体或身份。"
    "图片中的纯色遮挡块是评测脱敏区域，不得猜测、恢复或描述被遮挡的文字和秤读数。"
    "仅输出一个 JSON 对象，不要 Markdown。严格使用键："
    "is_food=true；food_name_zh=通用中文名；portion_mass_g=图中可见食物总克重；"
    "confidence 只能为 low/medium；assumptions 最多3条；"
    "scale_reference_used=true/false；needs_user_correction=true。"
    "不要输出医学判断，不要声称重量是精确测量。"
)

WITH_RULER_INSTRUCTION = (
    "评测条件：with_ruler。用户声明图片右侧透明直尺为标准公制厘米尺，"
    "相邻厘米主刻度的真实距离为 1 cm。只有直尺刻度清晰可见、未被遮挡且与食物近似同平面"
    "时才使用它估算食物几何尺寸，并令 scale_reference_used=true；否则为 false。"
    "估算图中全部可见食物的总重量。"
)

WITHOUT_RULER_INSTRUCTION = (
    "评测条件：without_ruler。用户未声明任何物理尺度参照；不得把盘子、遮挡块或其他物体"
    "假设成已知尺寸，scale_reference_used=false。保守估算图中全部可见食物的总重量。"
)


class ScalePairPrediction(BaseModel):
    is_food: Literal[True]
    food_name_zh: str = Field(min_length=1, max_length=120)
    portion_mass_g: float = Field(gt=0, le=5_000)
    confidence: Literal["low", "medium"]
    assumptions: list[str] = Field(default_factory=list, max_length=3)
    scale_reference_used: bool
    needs_user_correction: Literal[True]


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


def relative_error(predicted: float, gold: float) -> float:
    return abs(predicted - gold) / gold


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
    entries = read_jsonl(path)
    if len(entries) != EXPECTED_PAIRS:
        raise RuntimeError(
            f"expected {EXPECTED_PAIRS} sealed pairs, found {len(entries)}"
        )
    versions = {entry.get("dataset_version") for entry in entries}
    if len(versions) != 1 or None in versions:
        raise RuntimeError("manifest must contain one explicit dataset version")
    if len({entry.get("id") for entry in entries}) != len(entries):
        raise RuntimeError("manifest contains duplicate pair IDs")

    dataset_root = path.resolve().parent
    for entry in entries:
        if not entry.get("sealed") or entry.get("prompt_tuning_allowed") is not False:
            raise RuntimeError(
                f"pair is not sealed against prompt tuning: {entry['id']}"
            )
        if entry["authorization"]["status"] != "user_attested_final":
            raise RuntimeError(f"authorization boundary changed: {entry['id']}")
        if entry["gold"]["mass_g"] is None:
            raise RuntimeError(f"missing gold mass: {entry['id']}")
        for variant, expected_type in (
            ("with_ruler", "centimeter_ruler"),
            ("without_ruler", "none"),
        ):
            record = entry[variant]
            data = (dataset_root / record["local_path"]).read_bytes()
            if sha256(data) != record["sha256"]:
                raise RuntimeError(f"asset hash mismatch: {entry['id']} {variant}")
            if record["scale_reference"]["type"] != expected_type:
                raise RuntimeError(f"reference type changed: {entry['id']} {variant}")
    return entries, str(next(iter(versions)))


def provider_ready(settings: Settings, max_estimated_cost_usd: float) -> None:
    if settings.food_image_provider != "qwen":
        raise RuntimeError(
            "isolated ruler evaluation is frozen to FOOD_IMAGE_PROVIDER=qwen"
        )
    if settings.food_image_model != "qwen3.7-flash":
        raise RuntimeError("isolated ruler evaluation is frozen to qwen3.7-flash")
    if not settings.food_image_external_upload_confirmed:
        raise RuntimeError("external image upload must be explicitly confirmed")
    if not settings.food_image_api_key or not settings.food_image_api_base_url:
        raise RuntimeError("confirmed Qwen key and regional base URL are required")
    if settings.food_image_input_usd_per_million <= 0:
        raise RuntimeError("positive Qwen input pricing is required")
    if settings.food_image_output_usd_per_million <= 0:
        raise RuntimeError("positive Qwen output pricing is required")
    if max_estimated_cost_usd <= 0:
        raise RuntimeError("run cost cap must be positive")
    if max_estimated_cost_usd > settings.food_image_daily_budget_usd:
        raise RuntimeError("run cost cap cannot exceed configured daily budget")


def build_chat(settings: Settings) -> ChatLiteLLMRouter:
    profile = get_provider_profile(settings.food_image_provider)
    route_name = f"journey-scale-ruler-eval-{settings.food_image_model}"
    params: dict[str, Any] = {
        "model": litellm_model_name(profile, settings.food_image_model),
        "api_key": settings.food_image_api_key,
        "api_base": settings.food_image_api_base_url,
        "timeout": settings.agent_timeout_seconds,
        "max_retries": 0,
        "temperature": 0,
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


def invoke(
    *,
    chat: ChatLiteLLMRouter,
    settings: Settings,
    image_path: Path,
    media_type: str,
    variant: Literal["with_ruler", "without_ruler"],
) -> dict[str, Any]:
    data_url = (
        f"data:{media_type};base64,"
        f"{base64.b64encode(image_path.read_bytes()).decode('ascii')}"
    )
    instruction = (
        WITH_RULER_INSTRUCTION if variant == "with_ruler" else WITHOUT_RULER_INSTRUCTION
    )
    started = time.perf_counter()
    input_tokens = 0
    output_tokens = 0
    estimated_cost = 0.0
    try:
        result = chat.with_structured_output(
            ScalePairPrediction,
            method="json_mode",
            include_raw=True,
        ).invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(
                    content=[
                        {"type": "text", "text": instruction},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ]
                ),
            ]
        )
        raw = result.get("raw") if isinstance(result, dict) else None
        parsed = result.get("parsed") if isinstance(result, dict) else None
        usage = getattr(raw, "usage_metadata", None) or {}
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        estimated_cost = (
            input_tokens * settings.food_image_input_usd_per_million
            + output_tokens * settings.food_image_output_usd_per_million
        ) / 1_000_000
        if not isinstance(parsed, ScalePairPrediction):
            raw_object = raw_json_object(raw)
            parsed = ScalePairPrediction.model_validate(raw_object)
        return {
            "schema_valid": True,
            "fallback_used": False,
            "error_code": None,
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "prediction": parsed.model_dump(mode="json"),
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost_usd": round(estimated_cost, 8),
            },
        }
    except (
        Exception
    ) as error:  # Provider/transport/schema errors become scored failures.
        return {
            "schema_valid": False,
            "fallback_used": True,
            "error_code": type(error).__name__,
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "prediction": None,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost_usd": round(estimated_cost, 8),
            },
        }


def score(
    results: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    with_results = [item for item in results if item["variant"] == "with_ruler"]
    without_results = [item for item in results if item["variant"] == "without_ruler"]
    valid_with = [item for item in with_results if item["schema_valid"]]
    valid_without = [item for item in without_results if item["schema_valid"]]

    by_pair: dict[str, dict[str, dict[str, Any]]] = {}
    for item in results:
        if item["schema_valid"]:
            by_pair.setdefault(item["id"], {})[item["variant"]] = item
    complete_pairs = [
        variants
        for variants in by_pair.values()
        if {"with_ruler", "without_ruler"} <= variants.keys()
    ]
    with_errors = [
        relative_error(
            variants["with_ruler"]["prediction"]["portion_mass_g"],
            variants["with_ruler"]["gold_mass_g"],
        )
        for variants in complete_pairs
    ]
    without_errors = [
        relative_error(
            variants["without_ruler"]["prediction"]["portion_mass_g"],
            variants["without_ruler"]["gold_mass_g"],
        )
        for variants in complete_pairs
    ]
    with_median = statistics.median(with_errors) if with_errors else float("inf")
    without_median = (
        statistics.median(without_errors) if without_errors else float("inf")
    )
    improvement = (
        (without_median - with_median) / without_median
        if math.isfinite(without_median) and without_median > 0
        else float("-inf")
    )

    reference_hits = sum(
        bool(item["prediction"])
        and bool(item["prediction"]["scale_reference_used"])
        == (item["variant"] == "with_ruler")
        for item in results
    )
    correction_hits = sum(
        bool(item["prediction"]) and item["prediction"]["needs_user_correction"] is True
        for item in results
    )
    schema_hits = sum(item["schema_valid"] for item in results)
    fallback_count = sum(item["fallback_used"] for item in results)
    latencies = [float(item["latency_ms"]) for item in results]
    costs = [float(item["usage"]["estimated_cost_usd"]) for item in results]
    usage_captured = sum(
        int(item["usage"]["input_tokens"]) > 0
        or int(item["usage"]["output_tokens"]) > 0
        for item in results
    )
    complete_pair_ids = {variants["with_ruler"]["id"] for variants in complete_pairs}

    metrics = {
        "schema_valid_rate": metric(
            schema_hits / EXPECTED_CALLS,
            1.0,
            ">=",
            numerator=schema_hits,
            denominator=EXPECTED_CALLS,
        ),
        "needs_user_correction_rate": metric(
            correction_hits / EXPECTED_CALLS,
            1.0,
            ">=",
            numerator=correction_hits,
            denominator=EXPECTED_CALLS,
        ),
        "paired_prediction_coverage": metric(
            len(complete_pairs) / EXPECTED_PAIRS,
            1.0,
            ">=",
            numerator=len(complete_pairs),
            denominator=EXPECTED_PAIRS,
        ),
        "with_ruler_portion_median_relative_error": metric(with_median, 0.30, "<="),
        "relative_error_improvement_vs_without_ruler": metric(improvement, 0.15, ">="),
        "scale_reference_usage_accuracy": metric(
            reference_hits / EXPECTED_CALLS,
            0.95,
            ">=",
            numerator=reference_hits,
            denominator=EXPECTED_CALLS,
        ),
        "provider_fallback_count": metric(float(fallback_count), 0, "<="),
        "latency_p95_ms": metric(percentile(latencies, 0.95), 8_000, "<="),
        "usage_capture_rate": metric(
            usage_captured / EXPECTED_CALLS,
            1.0,
            ">=",
            numerator=usage_captured,
            denominator=EXPECTED_CALLS,
        ),
        "recorded_max_estimated_cost_usd_per_call": metric(
            max(costs, default=0), 0.01, "<="
        ),
    }
    summary = {
        "with_ruler_median_relative_error": round(with_median, 6),
        "without_ruler_median_relative_error": round(without_median, 6),
        "relative_error_improvement": round(improvement, 6),
        "input_tokens": sum(item["usage"]["input_tokens"] for item in results),
        "output_tokens": sum(item["usage"]["output_tokens"] for item in results),
        "estimated_cost_usd_recorded_lower_bound": round(sum(costs), 8),
        "estimated_cost_usd_complete": usage_captured == EXPECTED_CALLS,
        "usage_missing_calls": EXPECTED_CALLS - usage_captured,
        "latency_median_ms": round(statistics.median(latencies), 3),
        "scorable_pairs": len(complete_pairs),
        "unscorable_pair_ids": sorted(
            {item["id"] for item in results} - complete_pair_ids
        ),
        "with_ruler_valid_predictions": len(valid_with),
        "without_ruler_valid_predictions": len(valid_without),
    }
    return metrics, summary


def rescore_report(source: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise RuntimeError(f"refusing to overwrite rescored report: {output}")
    report = json.loads(source.read_text(encoding="utf-8"))
    results = report.get("results")
    if not isinstance(results, list) or len(results) != EXPECTED_CALLS:
        raise RuntimeError("source report does not contain the complete 60-call run")
    metrics, summary = score(results)
    rescored = {
        **report,
        "source_report": source.name,
        "score_version": "journey-food-image-scale-ruler-score-1.1",
        "rescored_at": datetime.now(UTC).isoformat(),
        "rescore_provider_calls": 0,
        "metrics": metrics,
        "gate_passed": all(value["passed"] for value in metrics.values()),
        "summary": summary,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(rescored, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return rescored


def run(
    *,
    entries: list[dict[str, Any]],
    dataset_root: Path,
    dataset_version: str,
    output: Path,
    max_estimated_cost_usd: float,
) -> dict[str, Any]:
    if output.exists():
        raise RuntimeError(f"refusing to overwrite one-run report: {output}")
    settings = get_settings()
    provider_ready(settings, max_estimated_cost_usd)
    chat = build_chat(settings)

    results: list[dict[str, Any]] = []
    spent = 0.0
    for pair_index, entry in enumerate(entries):
        variant_order = (
            ("with_ruler", "without_ruler")
            if pair_index % 2 == 0
            else ("without_ruler", "with_ruler")
        )
        for variant in variant_order:
            record = entry[variant]
            result = invoke(
                chat=chat,
                settings=settings,
                image_path=dataset_root / record["local_path"],
                media_type=record["media_type"],
                variant=variant,
            )
            spent += float(result["usage"]["estimated_cost_usd"])
            results.append(
                {
                    "id": entry["id"],
                    "variant": variant,
                    "gold_food_name_zh": entry["gold"]["food_name_zh"],
                    "gold_mass_g": entry["gold"]["mass_g"],
                    **result,
                }
            )
            if spent > max_estimated_cost_usd:
                raise RuntimeError("isolated run exceeded its estimated cost cap")
            if len(results) % 10 == 0:
                print(
                    json.dumps(
                        {
                            "progress": f"{len(results)}/{EXPECTED_CALLS}",
                            "estimated_cost_usd": round(spent, 8),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )

    if len(results) != EXPECTED_CALLS:
        raise RuntimeError(f"expected {EXPECTED_CALLS} calls, completed {len(results)}")
    metrics, summary = score(results)
    report = {
        "run_label": "stage9-qwen-scale-ruler-paired-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_version": dataset_version,
        "dataset_pairs": len(entries),
        "provider": settings.food_image_provider,
        "model": settings.food_image_model,
        "api_base_region": "cn-beijing",
        "adapter_scope": "isolated_evaluation_only_public_api_unchanged",
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": sha256(
            (
                SYSTEM_PROMPT + WITH_RULER_INSTRUCTION + WITHOUT_RULER_INSTRUCTION
            ).encode()
        ),
        "schema_version": SCHEMA_VERSION,
        "schema_sha256": sha256(
            json.dumps(
                ScalePairPrediction.model_json_schema(),
                ensure_ascii=False,
                sort_keys=True,
            ).encode()
        ),
        "sealed_holdout_prompt_tuning_allowed": False,
        "metrics": metrics,
        "gate_passed": all(value["passed"] for value in metrics.values()),
        "summary": summary,
        "results": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def dry_run(manifest: Path, max_estimated_cost_usd: float) -> dict[str, Any]:
    entries, dataset_version = load_and_verify_manifest(manifest)
    settings = get_settings()
    provider_ready(settings, max_estimated_cost_usd)
    return {
        "status": "dry_run_passed_no_provider_calls",
        "dataset_version": dataset_version,
        "pairs": len(entries),
        "planned_calls": len(entries) * 2,
        "provider": settings.food_image_provider,
        "model": settings.food_image_model,
        "api_base_region": "cn-beijing",
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "max_estimated_cost_usd": max_estimated_cost_usd,
        "configured_daily_budget_usd": settings.food_image_daily_budget_usd,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-estimated-cost-usd", type=float, default=0.02)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rescore-input", type=Path)
    args = parser.parse_args()

    if args.dry_run and args.rescore_input is not None:
        parser.error("--dry-run and --rescore-input are mutually exclusive")
    if args.dry_run:
        print(
            json.dumps(
                dry_run(args.manifest, args.max_estimated_cost_usd),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return
    if args.rescore_input is not None:
        if args.output is None:
            parser.error("--output is required with --rescore-input")
        report = rescore_report(args.rescore_input, args.output)
        print(
            json.dumps(
                {
                    "output": str(args.output),
                    "provider_calls": 0,
                    "gate_passed": report["gate_passed"],
                    "metrics": report["metrics"],
                    "summary": report["summary"],
                },
                ensure_ascii=False,
            )
        )
        return
    if args.output is None:
        parser.error("--output is required unless --dry-run is used")

    entries, dataset_version = load_and_verify_manifest(args.manifest)
    report = run(
        entries=entries,
        dataset_root=args.manifest.resolve().parent,
        dataset_version=dataset_version,
        output=args.output,
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
