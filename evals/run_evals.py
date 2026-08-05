"""Run deterministic Agent/RAG quality gates without external model calls."""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_SECRET_KEY", "local-test-secret-at-least-32-characters")
os.environ.setdefault("SEED_TEST_ACCOUNT", "false")
os.environ.setdefault("AGENT_PROVIDER", "mock")
os.environ.setdefault("AGENT_API_KEY", "")
os.environ.setdefault("AGENT_DAILY_BUDGET_USD", "0")

from app.agent.intent_router import deterministic_intent_plan  # noqa: E402
from app.agent.execution_graph import run_execution_graph_v3  # noqa: E402
from app.agent.planner import deterministic_plan, redacted_plan  # noqa: E402
from app.agent.policy import MAX_AGENT_STEPS, validate_plan  # noqa: E402
from app.agent.tool_registry import TOOL_REGISTRY  # noqa: E402
from app.agent.tool_registry import ToolExecution  # noqa: E402
from app.agent.model_router import (  # noqa: E402
    KNOWLEDGE_VERSION,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    MockModelAdapter,
    ModelInvocation,
    ModelRouter,
)
from app.agent.tools import _activity_fallback, _food_fallback  # noqa: E402
from app.agent.workflows import run_knowledge  # noqa: E402
from app.core.database import engine  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.knowledge.ingest import ingest_builtin_knowledge  # noqa: E402
from app.knowledge.retriever import retrieve  # noqa: E402
from app.models.knowledge import KnowledgeChunk  # noqa: E402
from app.schemas.agent import (  # noqa: E402
    ActivityParsed,
    AgentPlan,
    AgentPlanStep,
    AgentRecoveryDecision,
    FoodParsed,
)
from app.schemas.media import FoodImageEstimate  # noqa: E402

ROOT = Path(__file__).resolve().parent
DATASETS = ROOT / "datasets"


@dataclass
class Metric:
    name: str
    value: float
    threshold: float
    comparison: str = ">="

    @property
    def passed(self) -> bool:
        return (
            self.value >= self.threshold
            if self.comparison == ">="
            else self.value <= self.threshold
        )


def load(name: str) -> list[dict[str, Any]]:
    return json.loads((DATASETS / name).read_text(encoding="utf-8"))


def ratio(passed: int, total: int) -> float:
    return round(passed / total, 4) if total else 0.0


def exact_intents(cases: list[dict[str, Any]], failures: list[dict[str, Any]]) -> float:
    correct = 0
    for case in cases:
        actual = [
            item.intent for item in deterministic_intent_plan(case["input"]).intents
        ]
        expected = case["expected"]
        if set(actual) == set(expected):
            correct += 1
        else:
            failures.append(
                {
                    "dataset": "intent",
                    "id": case["id"],
                    "expected": expected,
                    "actual": actual,
                }
            )
    return ratio(correct, len(cases))


def parsing_metrics(
    cases: list[dict[str, Any]],
    parser,
    schema: type[BaseModel],
    dataset: str,
    failures: list[dict[str, Any]],
) -> tuple[float, float]:
    schema_valid = 0
    exact = 0
    for case in cases:
        try:
            parsed = schema.model_validate(parser(case["input"]))
            schema_valid += 1
            actual = parsed.model_dump()
            expected = case["expected"]
            if all(actual[key] == value for key, value in expected.items()):
                exact += 1
            else:
                failures.append(
                    {
                        "dataset": dataset,
                        "id": case["id"],
                        "expected": expected,
                        "actual": actual,
                    }
                )
        except (
            Exception
        ) as error:  # evaluation must retain the case instead of aborting
            failures.append(
                {"dataset": dataset, "id": case["id"], "error": type(error).__name__}
            )
    return ratio(schema_valid, len(cases)), ratio(exact, len(cases))


def fallback_metric(
    cases: list[dict[str, Any]], failures: list[dict[str, Any]]
) -> float:
    passed = 0
    with Session(engine) as db:
        for case in cases:
            schema = FoodParsed if case["schema"] == "food" else ActivityParsed
            factory = (
                (lambda: _food_fallback("午餐吃苹果 80 千卡"))
                if case["schema"] == "food"
                else (lambda: _activity_fallback("跑步 30 分钟 180 千卡"))
            )
            router = ModelRouter(db, adapter=MockModelAdapter(failure=case["failure"]))
            result = router.generate(
                case["capability"],
                schema,
                system_prompt="stage7-failure-eval",
                user_prompt="synthetic",
                fallback_factory=factory,
            )
            valid = (
                result.fallback_used
                and result.estimated_cost_usd == 0
                and result.error_code is not None
                and isinstance(schema.model_validate(result.output), schema)
            )
            if valid:
                passed += 1
            else:
                failures.append(
                    {"dataset": "failure", "id": case["id"], "actual": asdict(result)}
                )
    return ratio(passed, len(cases))


def rag_metrics(
    cases: list[dict[str, Any]], failures: list[dict[str, Any]]
) -> tuple[float, float, float, list[int]]:
    answerable = [case for case in cases if case["answerable"]]
    no_answer = [case for case in cases if not case["answerable"]]
    recall_hits = 0
    citation_hits = 0
    no_answer_hits = 0
    latencies: list[int] = []
    with Session(engine) as db:
        ingest_builtin_knowledge(db)
        chunk_text = {
            str(chunk_id): text
            for chunk_id, text in db.execute(
                select(KnowledgeChunk.id, KnowledgeChunk.text)
            ).all()
        }
        for case in answerable:
            started = time.perf_counter()
            retrieved = retrieve(db, case["input"], limit=3)
            latencies.append(int((time.perf_counter() - started) * 1000))
            if case["expected_slug"] in {item.source_slug for item in retrieved}:
                recall_hits += 1
            else:
                failures.append(
                    {
                        "dataset": "rag_recall",
                        "id": case["id"],
                        "actual": [item.source_slug for item in retrieved],
                    }
                )
            result = run_knowledge(db, ModelRouter(db), case["input"])
            supported = bool(result.citations) and all(
                citation.source_slug == case["expected_slug"]
                and citation.excerpt == chunk_text.get(citation.chunk_id, "")[:300]
                for citation in result.citations
            )
            if supported:
                citation_hits += 1
            else:
                failures.append(
                    {
                        "dataset": "rag_citation",
                        "id": case["id"],
                        "actual": [item.source_slug for item in result.citations],
                    }
                )
        for case in no_answer:
            result = run_knowledge(db, ModelRouter(db), case["input"])
            if not result.citations and "没有足够相关资料" in result.answer:
                no_answer_hits += 1
            else:
                failures.append(
                    {
                        "dataset": "rag_no_answer",
                        "id": case["id"],
                        "citation_count": len(result.citations),
                    }
                )
    return (
        ratio(recall_hits, len(answerable)),
        ratio(citation_hits, len(answerable)),
        ratio(no_answer_hits, len(no_answer)),
        latencies,
    )


def percentile(values: list[int], percent: float) -> float:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * percent)))
    return float(ordered[index])


def food_image_contract_metrics(
    cases: list[dict[str, Any]], failures: list[dict[str, Any]]
) -> tuple[float, float, float, float]:
    contract_correct = 0
    correction_correct = 0
    range_correct = 0
    abstention_correct = 0
    food_total = sum(
        case["expected_is_food"] and case["expected_valid"] for case in cases
    )
    nonfood_total = sum(
        not case["expected_is_food"] and case["expected_valid"] for case in cases
    )
    valid_total = sum(case["expected_valid"] for case in cases)
    for case in cases:
        try:
            estimate = FoodImageEstimate.model_validate(case["output"])
            accepted = True
        except Exception as error:
            estimate = None
            accepted = False
            if case["expected_valid"]:
                failures.append(
                    {
                        "dataset": "food_image_contract",
                        "id": case["id"],
                        "error": type(error).__name__,
                    }
                )
        if accepted == case["expected_valid"]:
            contract_correct += 1
        elif not case["expected_valid"]:
            failures.append(
                {
                    "dataset": "food_image_contract",
                    "id": case["id"],
                    "error": "invalid output was accepted",
                }
            )
        if estimate is None:
            continue
        if estimate.needs_user_correction is True:
            correction_correct += 1
        if case["expected_is_food"]:
            if (
                estimate.is_food
                and estimate.portion_amount is not None
                and bool(estimate.portion_unit)
                and estimate.energy_min_kcal is not None
                and estimate.energy_kcal is not None
                and estimate.energy_max_kcal is not None
                and estimate.energy_min_kcal
                <= estimate.energy_kcal
                <= estimate.energy_max_kcal
            ):
                range_correct += 1
            else:
                failures.append({"dataset": "food_image_range", "id": case["id"]})
        elif (
            not estimate.is_food and not estimate.items and estimate.energy_kcal is None
        ):
            abstention_correct += 1
        else:
            failures.append({"dataset": "food_image_abstention", "id": case["id"]})
    return (
        ratio(contract_correct, len(cases)),
        ratio(correction_correct, valid_total),
        ratio(range_correct, food_total),
        ratio(abstention_correct, nonfood_total),
    )


def agent_v2_plan_metrics(
    cases: list[dict[str, Any]], failures: list[dict[str, Any]]
) -> tuple[float, float, float, float, float]:
    schema_valid = 0
    tool_selection_correct = 0
    parameter_correct = 0
    policy_correct = 0
    bounded_correct = 0
    for case in cases:
        try:
            intent_plan = deterministic_intent_plan(
                case["input"], case.get("memory_context")
            )
            plan = deterministic_plan(case["input"], intent_plan)
            plan.model_validate(plan.model_dump(mode="json"))
            schema_valid += 1
        except Exception as error:
            failures.append(
                {
                    "dataset": "agent_v2_plan_schema",
                    "id": case["id"],
                    "error": type(error).__name__,
                }
            )
            continue

        actual_tools = [step.tool for step in plan.steps]
        expected_tools = case["expected_tools"]
        clarification_correct = plan.needs_clarification == case.get(
            "expected_clarification", False
        )
        if actual_tools == expected_tools and clarification_correct:
            tool_selection_correct += 1
        else:
            failures.append(
                {
                    "dataset": "agent_v2_tool_selection",
                    "id": case["id"],
                    "expected": expected_tools,
                    "actual": actual_tools,
                    "expected_clarification": case.get("expected_clarification", False),
                    "actual_clarification": plan.needs_clarification,
                }
            )

        expected_segments = case.get("expected_segments", {})
        actual_segments = {
            step.tool: step.segment
            for step in plan.steps
            if step.tool in expected_segments
        }
        if actual_segments == expected_segments:
            parameter_correct += 1
        else:
            failures.append(
                {
                    "dataset": "agent_v2_tool_parameters",
                    "id": case["id"],
                    "expected": expected_segments,
                    "actual": actual_segments,
                }
            )

        decision = validate_plan(plan)
        confirmation_valid = all(
            step.requires_confirmation == TOOL_REGISTRY[step.tool].requires_confirmation
            for step in plan.steps
        )
        no_direct_write = all(TOOL_REGISTRY[step.tool].read_only for step in plan.steps)
        if decision.allowed and confirmation_valid and no_direct_write:
            policy_correct += 1
        else:
            failures.append(
                {
                    "dataset": "agent_v2_policy",
                    "id": case["id"],
                    "violations": list(decision.violations),
                }
            )

        if len(plan.steps) <= MAX_AGENT_STEPS:
            bounded_correct += 1
        else:
            failures.append(
                {
                    "dataset": "agent_v2_step_bound",
                    "id": case["id"],
                    "step_count": len(plan.steps),
                }
            )

    total = len(cases)
    return (
        ratio(schema_valid, total),
        ratio(tool_selection_correct, total),
        ratio(parameter_correct, total),
        ratio(policy_correct, total),
        ratio(bounded_correct, total),
    )


def agent_v3_control_metrics(
    cases: list[dict[str, Any]], failures: list[dict[str, Any]]
) -> tuple[float, float, float, float]:
    checkpoint_cases = [case for case in cases if case["kind"] == "checkpoint"]
    recovery_cases = [case for case in cases if case["kind"] == "recovery"]
    privacy_cases = [case for case in cases if case["kind"] == "privacy"]
    checkpoint_hits = 0
    recovery_hits = 0
    observation_hits = 0
    privacy_hits = 0

    for case in checkpoint_cases:
        plan = deterministic_plan(
            case["input"], deterministic_intent_plan(case["input"])
        )
        confirmation_ids = {
            step.id for step in plan.steps if step.requires_confirmation
        }
        prefix_valid = not any(
            step.requires_confirmation
            for step in plan.steps[
                next(
                    (
                        index
                        for index, step in enumerate(plan.steps)
                        if not step.requires_confirmation
                    ),
                    len(plan.steps),
                ) :
            ]
        )
        context_steps = [step for step in plan.steps if step.tool == "context.load"]
        dependency_valid = bool(context_steps) and all(
            confirmation_ids <= set(step.depends_on) for step in context_steps
        )
        if (
            confirmation_ids
            and prefix_valid
            and dependency_valid
            and validate_plan(plan).allowed
        ):
            checkpoint_hits += 1
        else:
            failures.append({"dataset": "agent_v3_checkpoint", "id": case["id"]})

    for case in privacy_cases:
        plan = deterministic_plan(
            case["input"], deterministic_intent_plan(case["input"])
        )
        serialized = redacted_plan(plan).model_dump_json()
        if case["input"] not in serialized and all(
            step.segment is None for step in redacted_plan(plan).steps
        ):
            privacy_hits += 1
        else:
            failures.append({"dataset": "agent_v3_privacy", "id": case["id"]})

    for case in recovery_cases:
        tool = case["tool"]
        plan = AgentPlan(
            goal="synthetic recovery evaluation",
            steps=[AgentPlanStep(id="step-1", tool=tool, reason="synthetic")],
        )

        def execute(step: AgentPlanStep) -> ToolExecution:
            if step.id.startswith("recovery-") and case["recovery_succeeds"]:
                return ToolExecution(step.id, step.tool, "completed", "recovered", 1)
            return ToolExecution(
                step.id,
                step.tool,
                "failed",
                "synthetic failure",
                1,
                error_code="model_timeout",
            )

        def replan(observation):
            alternative = observation.allowed_alternatives[0]
            decision = AgentRecoveryDecision(
                action="use_alternative",
                tool=alternative,
                reason="allowlisted deterministic fallback",
            )
            invocation = ModelInvocation(
                output=decision,
                provider="mock",
                model="journey-deterministic-v1",
                input_tokens=1,
                output_tokens=1,
                retries=0,
                latency_ms=1,
                estimated_cost_usd=0,
                fallback_used=True,
            )
            return decision, invocation

        outcome = run_execution_graph_v3(plan, execute, replan)
        if (
            outcome.verification.decision == case["expected_decision"]
            and outcome.verification.replan_count <= 2
        ):
            recovery_hits += 1
        else:
            failures.append(
                {
                    "dataset": "agent_v3_recovery",
                    "id": case["id"],
                    "actual": outcome.verification.decision,
                }
            )
        first = outcome.observations[0]
        expected_alternatives = list(TOOL_REGISTRY[tool].recovery_tools)
        if (
            first.error_type == "model_timeout"
            and first.recoverable == bool(expected_alternatives)
            and first.allowed_alternatives == expected_alternatives
        ):
            observation_hits += 1
        else:
            failures.append({"dataset": "agent_v3_observation", "id": case["id"]})

    return (
        ratio(checkpoint_hits, len(checkpoint_cases)),
        ratio(recovery_hits, len(recovery_cases)),
        ratio(observation_hits, len(recovery_cases)),
        ratio(privacy_hits, len(privacy_cases)),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "latest.json")
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()
    failures: list[dict[str, Any]] = []
    started = time.perf_counter()

    intent = exact_intents(load("intent_router.json"), failures)
    mixed = exact_intents(load("mixed_intents.json"), failures)
    safety = exact_intents(load("safety.json"), failures)
    food_schema, food_exact = parsing_metrics(
        load("food_parsing.json"), _food_fallback, FoodParsed, "food", failures
    )
    activity_schema, activity_exact = parsing_metrics(
        load("activity_parsing.json"),
        _activity_fallback,
        ActivityParsed,
        "activity",
        failures,
    )
    fallback = fallback_metric(load("failure_fallback.json"), failures)
    recall, citation_support, no_answer, latencies = rag_metrics(
        load("rag_gold.json"), failures
    )
    food_image_cases = load("food_image_contract.json")
    image_contract, image_correction, image_range, image_abstention = (
        food_image_contract_metrics(food_image_cases, failures)
    )
    agent_v2_cases = load("agent_v2_plans.json")
    (
        agent_v2_schema,
        agent_v2_tools,
        agent_v2_parameters,
        agent_v2_policy,
        agent_v2_bounded,
    ) = agent_v2_plan_metrics(agent_v2_cases, failures)
    agent_v3_cases = load("agent_v3_control_loop.json")
    (
        agent_v3_checkpoint,
        agent_v3_recovery,
        agent_v3_observation,
        agent_v3_privacy,
    ) = agent_v3_control_metrics(agent_v3_cases, failures)

    metrics = [
        Metric("intent_exact_accuracy", intent, 0.90),
        Metric("mixed_intent_exact_accuracy", mixed, 0.90),
        Metric(
            "write_tool_selection_accuracy", min(food_schema, activity_schema), 0.95
        ),
        Metric("food_schema_validity", food_schema, 1.0),
        Metric("activity_schema_validity", activity_schema, 1.0),
        Metric("food_parameter_exact_accuracy", food_exact, 0.95),
        Metric("activity_parameter_exact_accuracy", activity_exact, 0.95),
        Metric("high_risk_rule_pass_rate", safety, 1.0),
        Metric("failure_fallback_pass_rate", fallback, 1.0),
        Metric("rag_recall_at_3", recall, 0.90),
        Metric("citation_support_rate", citation_support, 0.95),
        Metric("no_answer_accuracy", no_answer, 0.90),
        Metric("rag_retrieval_p95_ms", percentile(latencies, 0.95), 250, "<="),
        Metric("food_image_schema_contract_accuracy", image_contract, 1.0),
        Metric("food_image_user_correction_required_rate", image_correction, 1.0),
        Metric("food_image_portion_and_energy_range_validity", image_range, 1.0),
        Metric("food_image_nonfood_abstention_contract", image_abstention, 1.0),
        Metric("agent_v2_plan_schema_validity", agent_v2_schema, 1.0),
        Metric("agent_v2_tool_selection_accuracy", agent_v2_tools, 0.95),
        Metric("agent_v2_tool_parameter_accuracy", agent_v2_parameters, 0.95),
        Metric("agent_v2_confirmation_and_write_policy_rate", agent_v2_policy, 1.0),
        Metric("agent_v2_bounded_plan_rate", agent_v2_bounded, 1.0),
        Metric("agent_v3_checkpoint_policy_rate", agent_v3_checkpoint, 1.0),
        Metric("agent_v3_recovery_decision_rate", agent_v3_recovery, 1.0),
        Metric("agent_v3_observation_contract_rate", agent_v3_observation, 1.0),
        Metric("agent_v3_checkpoint_privacy_rate", agent_v3_privacy, 1.0),
    ]
    settings = get_settings()
    report = {
        "schema_version": "journey-eval-report-1",
        "prompt_version": PROMPT_VERSION,
        "agent_schema_version": SCHEMA_VERSION,
        "knowledge_version": KNOWLEDGE_VERSION,
        "provider": settings.agent_provider,
        "api_key_configured": bool(settings.agent_api_key),
        "external_budget_usd": settings.agent_daily_budget_usd,
        "estimated_external_cost_usd": 0,
        "datasets": {
            "intent_router": 100,
            "food_parsing": 50,
            "activity_parsing": 50,
            "mixed_intents": 20,
            "safety": 20,
            "failure_fallback": 20,
            "rag_gold": 36,
            "food_image_contract": len(food_image_cases),
            "agent_v2_plans": len(agent_v2_cases),
            "agent_v3_control_loop": len(agent_v3_cases),
        },
        "metrics": [{**asdict(metric), "passed": metric.passed} for metric in metrics],
        "failure_count": len(failures),
        "failures": failures,
        "duration_ms": int((time.perf_counter() - started) * 1000),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for metric in metrics:
        print(
            f"{'PASS' if metric.passed else 'FAIL'} {metric.name}: {metric.value:.4f} {metric.comparison} {metric.threshold}"
        )
    print(
        f"report={args.output} failures={len(failures)} provider={settings.agent_provider} cost=$0"
    )
    return 1 if args.enforce and not all(metric.passed for metric in metrics) else 0


if __name__ == "__main__":
    raise SystemExit(main())
