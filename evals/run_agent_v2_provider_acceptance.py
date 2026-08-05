"""Opt-in real-provider gate for the Agent v2 router and planner."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
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
from app.agent.planner import PLAN_PROMPT_VERSION, create_plan
from app.agent.policy import MAX_AGENT_STEPS, validate_plan
from app.agent.tool_registry import TOOL_REGISTRY
from app.core.settings import get_settings

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "agent_v2_plans.json"
DEFAULT_REPORT = ROOT / "reports" / "REAL_AGENT_V2_PROVIDER_ACCEPTANCE_2.json"
EVAL_VERSION = "journey-real-agent-v2-acceptance-1.0.1"
SELECTED_IDS = {
    "plan-001",
    "plan-002",
    "plan-003",
    "plan-004",
    "plan-006",
    "plan-007",
    "plan-009",
    "plan-012",
}


class ZeroSpendSession:
    """Budget-check seam; this evaluator never writes application data."""

    def scalar(self, _statement: Any) -> Decimal:
        return Decimal("0")


def selected_cases() -> list[dict[str, Any]]:
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    return [case for case in cases if case["id"] in SELECTED_IDS]


def invocation_summary(invocation: ModelInvocation) -> dict[str, Any]:
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


def metric(
    value: float, threshold: float, *, lower_is_better: bool = False
) -> dict[str, Any]:
    passed = value <= threshold if lower_is_better else value >= threshold
    return {"value": round(value, 6), "threshold": threshold, "passed": passed}


def p95(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]


def score(
    results: list[dict[str, Any]],
    *,
    expected_provider: str,
    expected_model: str,
    max_cost_usd: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    invocations = [
        invocation
        for result in results
        for invocation in (result["router_invocation"], result["planner_invocation"])
    ]
    total_calls = len(invocations)
    total_cost = round(sum(item["estimated_cost_usd"] for item in invocations), 8)
    latencies = [item["latency_ms"] for item in invocations]
    metrics = {
        "intent_exact_accuracy": metric(
            sum(result["intent_passed"] for result in results) / len(results), 0.875
        ),
        "plan_schema_validity": metric(
            sum(result["schema_valid"] for result in results) / len(results), 1.0
        ),
        "tool_sequence_accuracy": metric(
            sum(result["tools_passed"] for result in results) / len(results), 0.875
        ),
        "policy_and_confirmation_pass_rate": metric(
            sum(result["policy_passed"] for result in results) / len(results), 1.0
        ),
        "provider_model_match_rate": metric(
            sum(
                item["provider"] == expected_provider
                and item["model"] == expected_model
                for item in invocations
            )
            / total_calls,
            1.0,
        ),
        "schema_no_fallback_rate": metric(
            sum(
                not item["fallback_used"] and item["error_code"] is None
                for item in invocations
            )
            / total_calls,
            1.0,
        ),
        "usage_capture_rate": metric(
            sum(
                item["input_tokens"] > 0 and item["output_tokens"] > 0
                for item in invocations
            )
            / total_calls,
            1.0,
        ),
        "latency_p95_ms": metric(float(p95(latencies)), 8000.0, lower_is_better=True),
        "total_estimated_cost_usd": metric(
            total_cost, max_cost_usd, lower_is_better=True
        ),
    }
    summary = {
        "cases": len(results),
        "calls": total_calls,
        "input_tokens": sum(item["input_tokens"] for item in invocations),
        "output_tokens": sum(item["output_tokens"] for item in invocations),
        "retries": sum(item["retries"] for item in invocations),
        "fallbacks": sum(item["fallback_used"] for item in invocations),
        "latency_p95_ms": p95(latencies),
        "estimated_cost_usd": total_cost,
    }
    return metrics, summary


def run_case(router: ModelRouter, case: dict[str, Any]) -> dict[str, Any]:
    intent_plan, router_invocation = route_intents(
        router, case["input"], case.get("memory_context")
    )
    plan, planner_invocation = create_plan(
        router,
        message=case["input"],
        intent_plan=intent_plan,
        memory_context=case.get("memory_context"),
    )
    actual_intents = [item.intent for item in intent_plan.intents]
    actual_tools = [step.tool for step in plan.steps]
    expected_tools = case["expected_tools"]
    expected_intents = sorted(
        {
            tool.split(".", 1)[0]
            for tool in expected_tools
            if tool
            not in {"context.load", "knowledge.retrieve", "recommendation.generate"}
        }
        | ({"recommendation"} if "recommendation.generate" in expected_tools else set())
    )
    decision = validate_plan(plan)
    confirmation_valid = all(
        step.requires_confirmation == TOOL_REGISTRY[step.tool].requires_confirmation
        for step in plan.steps
        if step.tool in TOOL_REGISTRY
    )
    policy_passed = (
        decision.allowed
        and confirmation_valid
        and len(plan.steps) <= MAX_AGENT_STEPS
        and all(TOOL_REGISTRY[step.tool].read_only for step in plan.steps)
    )
    return {
        "id": case["id"],
        "expected_intents": expected_intents,
        "actual_intents": actual_intents,
        "intent_passed": sorted(actual_intents) == expected_intents,
        "expected_tools": expected_tools,
        "actual_tools": actual_tools,
        "tools_passed": actual_tools == expected_tools,
        "schema_valid": plan.model_validate(plan.model_dump(mode="json")) is not None,
        "policy_passed": policy_passed,
        "policy_violations": list(decision.violations),
        "plan": plan.model_copy(
            update={
                "goal": "[REDACTED]",
                "steps": [
                    step.model_copy(update={"segment": None}) for step in plan.steps
                ],
            }
        ).model_dump(mode="json"),
        "router_invocation": invocation_summary(router_invocation),
        "planner_invocation": invocation_summary(planner_invocation),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the opt-in real Agent v2 acceptance gate."
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--max-cost-usd", type=float, default=0.02)
    args = parser.parse_args()

    settings = get_settings()
    if settings.agent_provider == "mock":
        raise RuntimeError("real Agent v2 acceptance refuses AGENT_PROVIDER=mock")
    if args.max_cost_usd <= 0 or args.max_cost_usd > settings.agent_daily_budget_usd:
        raise RuntimeError(
            "max cost must be positive and not exceed AGENT_DAILY_BUDGET_USD"
        )

    cases = selected_cases()
    planned_calls = len(cases) * 2
    if not args.execute:
        print(
            json.dumps(
                {
                    "status": "dry_run",
                    "provider": settings.agent_provider,
                    "model": settings.agent_default_model,
                    "cases": len(cases),
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
    for case in cases:
        results.append(run_case(router, case))
        print(f"real Agent v2 acceptance: {len(results)}/{len(cases)}", flush=True)

    expected_model = router.model_for("task_planning")
    metrics, summary = score(
        results,
        expected_provider=settings.agent_provider,
        expected_model=expected_model,
        max_cost_usd=args.max_cost_usd,
    )
    report = {
        "evaluation_version": EVAL_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "provider": settings.agent_provider,
        "model": expected_model,
        "prompt_version": PROMPT_VERSION,
        "router_prompt_version": ROUTER_PROMPT_VERSION,
        "planner_prompt_version": PLAN_PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "dataset": {
            "path": DATASET.name,
            "sha256": hashlib.sha256(DATASET.read_bytes()).hexdigest(),
            "selected_ids": sorted(SELECTED_IDS),
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
                **summary,
                "report": str(args.output),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if report["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
