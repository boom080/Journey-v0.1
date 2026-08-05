"""Opt-in real-provider gate for Agent v3 planning and failure replanning."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.agent.intent_router import ROUTER_PROMPT_VERSION, route_intents
from app.agent.model_router import ModelInvocation, ModelRouter
from app.agent.planner import PLAN_PROMPT_VERSION, create_plan, redacted_plan
from app.agent.policy import validate_plan
from app.agent.replanner import REPLAN_PROMPT_VERSION, choose_recovery
from app.core.settings import get_settings
from app.schemas.agent import AgentObservation

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "agent_v3_control_loop.json"
DEFAULT_REPORT = ROOT / "reports" / "REAL_AGENT_V3_PROVIDER_ACCEPTANCE.json"
EVAL_VERSION = "journey-real-agent-v3-acceptance-1.0.0"
SELECTED_CHECKPOINT_IDS = {
    "checkpoint-001",
    "checkpoint-002",
    "checkpoint-003",
    "checkpoint-005",
}


class ZeroSpendSession:
    def scalar(self, _statement: Any) -> Decimal:
        return Decimal("0")


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


def selected_cases() -> list[dict[str, Any]]:
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    return [case for case in cases if case["id"] in SELECTED_CHECKPOINT_IDS]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the opt-in real Agent v3 gate.")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--max-cost-usd", type=float, default=0.02)
    args = parser.parse_args()
    settings = get_settings()
    if settings.agent_provider == "mock":
        raise RuntimeError("real Agent v3 acceptance refuses AGENT_PROVIDER=mock")
    if args.max_cost_usd <= 0 or args.max_cost_usd > settings.agent_daily_budget_usd:
        raise RuntimeError(
            "max cost must be positive and within AGENT_DAILY_BUDGET_USD"
        )

    cases = selected_cases()
    planned_calls = len(cases) * 2 + 2
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
    results: list[dict[str, Any]] = []
    invocations: list[ModelInvocation] = []
    for case in cases:
        intents, route_invocation = route_intents(router, case["input"])
        plan, plan_invocation = create_plan(
            router, message=case["input"], intent_plan=intents
        )
        invocations.extend([route_invocation, plan_invocation])
        confirmation_ids = {
            step.id for step in plan.steps if step.requires_confirmation
        }
        context_steps = [step for step in plan.steps if step.tool == "context.load"]
        passed = (
            bool(confirmation_ids)
            and bool(context_steps)
            and all(confirmation_ids <= set(step.depends_on) for step in context_steps)
            and validate_plan(plan).allowed
        )
        results.append(
            {
                "id": case["id"],
                "passed": passed,
                "plan": redacted_plan(plan).model_dump(mode="json"),
                "router": invocation_summary(route_invocation),
                "planner": invocation_summary(plan_invocation),
            }
        )

    recovery_results = []
    for tool, alternative in (
        ("knowledge.answer", "knowledge.safe_summary"),
        ("recommendation.generate", "recommendation.rules_fallback"),
    ):
        observation = AgentObservation(
            step_id="step-1",
            tool=tool,
            status="failed",
            error_type="model_timeout",
            recoverable=True,
            allowed_alternatives=[alternative],
        )
        decision, invocation = choose_recovery(router, observation)
        invocations.append(invocation)
        recovery_results.append(
            {
                "tool": tool,
                "passed": decision.action == "use_alternative"
                and decision.tool == alternative,
                "decision": decision.model_dump(mode="json"),
                "invocation": invocation_summary(invocation),
            }
        )

    total_cost = round(sum(item.estimated_cost_usd for item in invocations), 8)
    no_fallback = all(
        not item.fallback_used and item.error_code is None for item in invocations
    )
    provider_match = all(
        item.provider == settings.agent_provider for item in invocations
    )
    metrics = {
        "checkpoint_plan_pass_rate": sum(item["passed"] for item in results)
        / len(results),
        "recovery_choice_pass_rate": sum(item["passed"] for item in recovery_results)
        / len(recovery_results),
        "schema_no_fallback_rate": 1.0 if no_fallback else 0.0,
        "provider_match_rate": 1.0 if provider_match else 0.0,
        "total_estimated_cost_usd": total_cost,
    }
    gate_passed = (
        metrics["checkpoint_plan_pass_rate"] == 1.0
        and metrics["recovery_choice_pass_rate"] == 1.0
        and metrics["schema_no_fallback_rate"] == 1.0
        and metrics["provider_match_rate"] == 1.0
        and total_cost <= args.max_cost_usd
    )
    report = {
        "evaluation_version": EVAL_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "provider": settings.agent_provider,
        "model": settings.agent_default_model,
        "router_prompt_version": ROUTER_PROMPT_VERSION,
        "planner_prompt_version": PLAN_PROMPT_VERSION,
        "replanner_prompt_version": REPLAN_PROMPT_VERSION,
        "dataset": {
            "path": DATASET.name,
            "sha256": hashlib.sha256(DATASET.read_bytes()).hexdigest(),
            "selected_ids": sorted(SELECTED_CHECKPOINT_IDS),
        },
        "max_cost_usd": args.max_cost_usd,
        "planned_calls": planned_calls,
        "metrics": metrics,
        "gate_passed": gate_passed,
        "results": results,
        "recovery_results": recovery_results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "gate_passed": gate_passed,
                "calls": len(invocations),
                "estimated_cost_usd": total_cost,
                "report": str(args.output),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if gate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
