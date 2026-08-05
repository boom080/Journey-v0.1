import argparse
import hashlib
import json
import math
import re
import time
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.agent.intent_router import ROUTER_PROMPT_VERSION, route_intents
from app.agent.model_router import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    ModelInvocation,
    ModelRouter,
)
from app.agent.tools import _activity_fallback, _food_fallback
from app.core.settings import get_settings
from app.schemas.agent import ActivityParsed, FoodParsed

ROOT = Path(__file__).resolve().parent
DATASET_ROOT = ROOT / "datasets"
DEFAULT_REPORT = ROOT / "reports" / "REAL_TEXT_PROVIDER_ACCEPTANCE.json"
EVAL_VERSION = "journey-real-text-provider-acceptance-1.0.0"


class ZeroSpendSession:
    """Minimal budget-check seam; the evaluator never writes application data."""

    def scalar(self, _statement: Any) -> Decimal:
        return Decimal("0")


def _load(name: str) -> list[dict[str, Any]]:
    return json.loads((DATASET_ROOT / name).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", value.casefold())


def _name_matches(actual: str, expected: str) -> bool:
    actual_normalized = _normalize(actual)
    expected_normalized = _normalize(expected)
    return bool(
        actual_normalized
        and expected_normalized
        and (
            actual_normalized in expected_normalized
            or expected_normalized in actual_normalized
        )
    )


def _number_matches(actual: float, expected: float) -> bool:
    return math.isclose(actual, expected, rel_tol=0.05, abs_tol=1.0)


def _p95(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]


def select_router_cases(
    cases: list[dict[str, Any]], *, per_expected_group: int = 2
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    counts: dict[tuple[str, ...], int] = defaultdict(int)
    for case in cases:
        group = tuple(case["expected"])
        if counts[group] >= per_expected_group:
            continue
        selected.append(case)
        counts[group] += 1
    return selected


def _invocation_result(invocation: ModelInvocation) -> dict[str, Any]:
    return {
        "provider": invocation.provider,
        "model": invocation.model,
        "input_tokens": invocation.input_tokens,
        "output_tokens": invocation.output_tokens,
        "retries": invocation.retries,
        "latency_ms": invocation.latency_ms,
        "estimated_cost_usd": invocation.estimated_cost_usd,
        "fallback_used": invocation.fallback_used,
        "error_code": invocation.error_code,
    }


def _metric(
    value: float, threshold: float, *, lower_is_better: bool = False
) -> dict[str, Any]:
    passed = value <= threshold if lower_is_better else value >= threshold
    return {"value": value, "threshold": threshold, "passed": passed}


def score(
    results: list[dict[str, Any]],
    *,
    expected_provider: str,
    expected_model: str,
    max_cost_usd: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    router = [item for item in results if item["capability"] == "intent_classification"]
    food = [item for item in results if item["capability"] == "food_text_parse"]
    activity = [item for item in results if item["capability"] == "activity_text_parse"]
    invocations = [item["invocation"] for item in results]
    provider_model_matches = sum(
        item["provider"] == expected_provider and item["model"] == expected_model
        for item in invocations
    )
    no_fallback = sum(
        not item["fallback_used"] and item["error_code"] is None for item in invocations
    )
    usage_captured = sum(
        item["input_tokens"] > 0 and item["output_tokens"] > 0 for item in invocations
    )
    total = len(invocations)
    total_cost = round(sum(item["estimated_cost_usd"] for item in invocations), 8)
    metrics = {
        "router_exact_accuracy": _metric(
            sum(item["passed"] for item in router) / len(router), 0.90
        ),
        "food_parse_accuracy": _metric(
            sum(item["passed"] for item in food) / len(food), 0.80
        ),
        "activity_parse_accuracy": _metric(
            sum(item["passed"] for item in activity) / len(activity), 0.80
        ),
        "provider_model_match_rate": _metric(provider_model_matches / total, 1.0),
        "schema_no_fallback_rate": _metric(no_fallback / total, 1.0),
        "usage_capture_rate": _metric(usage_captured / total, 1.0),
        "latency_p95_ms": _metric(
            float(_p95([item["latency_ms"] for item in invocations])),
            8000.0,
            lower_is_better=True,
        ),
        "total_estimated_cost_usd": _metric(
            total_cost, max_cost_usd, lower_is_better=True
        ),
    }
    summary = {
        "calls": total,
        "input_tokens": sum(item["input_tokens"] for item in invocations),
        "output_tokens": sum(item["output_tokens"] for item in invocations),
        "retries": sum(item["retries"] for item in invocations),
        "fallbacks": total - no_fallback,
        "latency_median_ms": sorted(item["latency_ms"] for item in invocations)[
            total // 2
        ],
        "latency_p95_ms": _p95([item["latency_ms"] for item in invocations]),
        "estimated_cost_usd": total_cost,
    }
    return metrics, summary


def _run_router_case(router: ModelRouter, case: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    plan, invocation = route_intents(router, case["input"])
    actual = [item.intent for item in plan.intents]
    expected = case["expected"]
    return {
        "id": case["id"],
        "capability": "intent_classification",
        "expected": expected,
        "actual": actual,
        "passed": sorted(actual) == sorted(expected),
        "wall_latency_ms": int((time.perf_counter() - started) * 1000),
        "invocation": _invocation_result(invocation),
    }


def _run_food_case(router: ModelRouter, case: dict[str, Any]) -> dict[str, Any]:
    invocation = router.generate(
        "food_text_parse",
        FoodParsed,
        system_prompt="解析饮食为结构化候选，不执行写入。",
        user_prompt=case["input"],
        fallback_factory=lambda: _food_fallback(case["input"]),
    )
    actual = FoodParsed.model_validate(invocation.output)
    expected = case["expected"]
    passed = (
        actual.meal_type == expected["meal_type"]
        and _name_matches(actual.name, expected["name"])
        and _number_matches(actual.energy_kcal, expected["energy_kcal"])
    )
    return {
        "id": case["id"],
        "capability": "food_text_parse",
        "expected": expected,
        "actual": actual.model_dump(mode="json"),
        "passed": passed,
        "invocation": _invocation_result(invocation),
    }


def _run_activity_case(router: ModelRouter, case: dict[str, Any]) -> dict[str, Any]:
    invocation = router.generate(
        "activity_text_parse",
        ActivityParsed,
        system_prompt="解析运动为结构化候选，不执行写入。",
        user_prompt=case["input"],
        fallback_factory=lambda: _activity_fallback(case["input"]),
    )
    actual = ActivityParsed.model_validate(invocation.output)
    expected = case["expected"]
    passed = (
        _name_matches(actual.name, expected["name"])
        and actual.duration_minutes == expected["duration_minutes"]
        and actual.intensity == expected["intensity"]
        and _number_matches(actual.energy_kcal, expected["energy_kcal"])
    )
    return {
        "id": case["id"],
        "capability": "activity_text_parse",
        "expected": expected,
        "actual": actual.model_dump(mode="json"),
        "passed": passed,
        "invocation": _invocation_result(invocation),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the opt-in real text-provider release acceptance gate."
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--max-cost-usd", type=float, default=0.02)
    args = parser.parse_args()

    settings = get_settings()
    if settings.agent_provider == "mock":
        raise RuntimeError("real text acceptance refuses AGENT_PROVIDER=mock")
    if args.max_cost_usd <= 0 or args.max_cost_usd > settings.agent_daily_budget_usd:
        raise RuntimeError(
            "max cost must be positive and not exceed AGENT_DAILY_BUDGET_USD"
        )

    router_cases = select_router_cases(_load("intent_router.json"))
    food_cases = _load("food_parsing.json")[:5]
    activity_cases = _load("activity_parsing.json")[:5]
    planned_calls = len(router_cases) + len(food_cases) + len(activity_cases)
    if not args.execute:
        print(
            json.dumps(
                {
                    "status": "dry_run",
                    "provider": settings.agent_provider,
                    "model": settings.agent_default_model,
                    "planned_calls": planned_calls,
                    "provider_calls": 0,
                    "max_cost_usd": args.max_cost_usd,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0

    if args.output.exists():
        raise RuntimeError(f"refusing to overwrite existing report: {args.output}")

    router = ModelRouter(ZeroSpendSession(), settings=settings)
    results = []
    for case in router_cases:
        results.append(_run_router_case(router, case))
        print(f"real text acceptance: {len(results)}/{planned_calls}", flush=True)
    for case in food_cases:
        results.append(_run_food_case(router, case))
        print(f"real text acceptance: {len(results)}/{planned_calls}", flush=True)
    for case in activity_cases:
        results.append(_run_activity_case(router, case))
        print(f"real text acceptance: {len(results)}/{planned_calls}", flush=True)

    metrics, summary = score(
        results,
        expected_provider=settings.agent_provider,
        expected_model=settings.agent_default_model,
        max_cost_usd=args.max_cost_usd,
    )
    report = {
        "evaluation_version": EVAL_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "provider": settings.agent_provider,
        "model": settings.agent_default_model,
        "prompt_version": PROMPT_VERSION,
        "router_prompt_version": ROUTER_PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "datasets": {
            name: {
                "sha256": _sha256(DATASET_ROOT / name),
                "selected_samples": count,
            }
            for name, count in {
                "intent_router.json": len(router_cases),
                "food_parsing.json": len(food_cases),
                "activity_parsing.json": len(activity_cases),
            }.items()
        },
        "max_cost_usd": args.max_cost_usd,
        "metrics": metrics,
        "summary": summary,
        "gate_passed": all(item["passed"] for item in metrics.values()),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "gate_passed": report["gate_passed"],
                "provider": report["provider"],
                "model": report["model"],
                "calls": summary["calls"],
                "estimated_cost_usd": summary["estimated_cost_usd"],
                "report": str(args.output),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if report["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
