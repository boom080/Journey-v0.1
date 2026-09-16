"""Real-provider parsing evaluation for the fixed Chinese health-record set.

The evaluator deliberately calls the current ``route_intents`` implementation and
the same structured parsing capabilities used by the food/activity candidate tools.
It does not write health records.  ``--execute`` is required before any provider
call; every completed case is appended to ``evaluation/raw/parsing.jsonl`` so an
interrupted run can continue later.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import statistics
import sys
import time
from collections import Counter
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    # This also makes ``python scripts/evaluation/parsing.py`` work from the
    # repository root; the runtime still controls all application imports.
    sys.path.insert(0, str(ROOT))

DEFAULT_DATASET = ROOT / "evaluation" / "datasets" / "health_v1.json"
DEFAULT_RAW = ROOT / "evaluation" / "raw" / "parsing.jsonl"
DEFAULT_SUMMARY = ROOT / "evaluation" / "raw" / "parsing-summary.json"

EVALUATION_VERSION = "journey-health-parsing-eval-1.0.0"
SUMMARY_SCHEMA_VERSION = "journey-health-parsing-summary-1"
RAW_SCHEMA_VERSION = "journey-health-parsing-case-1"
GOLD_STATUS = "agent_authored_pending_human_review"

ROUTER_CAPABILITY = "intent_classification"
FOOD_CAPABILITY = "food_text_parse"
ACTIVITY_CAPABILITY = "activity_text_parse"
FOOD_SYSTEM_PROMPT = (
    "解析饮食为结构化候选，不执行写入。用户未说明餐别时可返回 other；"
    "用户未说明份量时给出合理的常见单份估算。"
)
ACTIVITY_SYSTEM_PROMPT = "解析运动为结构化候选，不执行写入。"

# These are stable implementation parameters of ModelRouter/LangChainLiteLLM.
# The effective model alias is filled from router.model_for() at execution time.
FIXED_MODEL_PARAMETERS = {
    "temperature": 0,
    "adapter_max_retries": 0,
    "structured_output": True,
}

TEXT_PUNCTUATION = re.compile(r"[\s\u3000，。、“”‘’（）()【】\[\]：:；;、,.，!！?？\-_/]+")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _norm_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return TEXT_PUNCTUATION.sub("", value.casefold())


def _number_equal(actual: Any, expected: Any) -> bool:
    if isinstance(actual, bool) or isinstance(expected, bool):
        return False
    try:
        return float(actual) == float(expected)
    except (TypeError, ValueError):
        return False


def _exact(actual: Any, expected: Any) -> bool:
    if isinstance(expected, str):
        return _norm_text(actual) == _norm_text(expected)
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return _number_equal(actual, expected)
    return actual == expected


def _percent(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def _percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * fraction) - 1)
    return ordered[index]


def _load_dataset(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("parsing_dataset_must_be_object")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not 60 <= len(cases) <= 80:
        raise ValueError("parsing_dataset_must_contain_60_to_80_cases")
    if payload.get("gold_status") != GOLD_STATUS:
        raise ValueError("parsing_dataset_gold_status_must_be_pending_human_review")
    ids: set[str] = set()
    counts = Counter()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("parsing_case_must_be_object")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            raise ValueError("parsing_case_ids_must_be_unique")
        ids.add(case_id)
        kind = case.get("kind")
        if kind not in {"food", "activity"}:
            raise ValueError(f"unsupported_parsing_case_kind:{case_id}")
        counts[kind] += 1
        if not isinstance(case.get("input"), str) or not case["input"].strip():
            raise ValueError(f"parsing_case_input_missing:{case_id}")
        if not isinstance(case.get("expected_intents"), list):
            raise ValueError(f"parsing_case_expected_intents_missing:{case_id}")
        if case.get("gold_status", GOLD_STATUS) != GOLD_STATUS:
            raise ValueError(f"parsing_case_gold_status_mismatch:{case_id}")
        if not isinstance(case.get("gold"), dict):
            raise ValueError(f"parsing_case_gold_missing:{case_id}")
    if counts["food"] < 20 or counts["activity"] < 20:
        raise ValueError("parsing_dataset_needs_at_least_20_food_and_20_activity_cases")
    return payload


def _invocation_dict(invocation: Any) -> dict[str, Any]:
    """Keep only non-sensitive, stable accounting fields from ModelInvocation."""

    return {
        "provider": invocation.provider,
        "model": invocation.model,
        "input_tokens": int(invocation.input_tokens),
        "output_tokens": int(invocation.output_tokens),
        "retries": int(invocation.retries),
        "latency_ms": int(invocation.latency_ms),
        "estimated_cost_usd": float(invocation.estimated_cost_usd),
        "fallback_used": bool(invocation.fallback_used),
        "error_code": invocation.error_code,
    }


def _field_result(
    *,
    field: str,
    actual: Any,
    expected: Any,
    ai_success: bool,
    reason: str | None = None,
) -> dict[str, Any]:
    if expected is None:
        return {
            "field": field,
            "scored": False,
            "passed": None,
            "actual": actual,
            "gold": None,
            "reason": reason or "gold_not_determined_from_input",
        }
    raw_match = _exact(actual, expected)
    return {
        "field": field,
        "scored": True,
        # A fallback can be structurally right, but is never an AI success.
        "passed": bool(ai_success and raw_match),
        "raw_match": raw_match,
        "actual": actual,
        "gold": expected,
        "reason": None if ai_success and raw_match else (
            "fallback_excluded" if raw_match and not ai_success else "exact_mismatch"
        ),
    }


def _quantity_result(
    *, actual: dict[str, Any], gold: dict[str, Any] | None, ai_success: bool
) -> dict[str, Any]:
    status = gold.get("status") if isinstance(gold, dict) else "missing"
    actual_value = {
        "amount": actual.get("portion_amount"),
        "unit": actual.get("portion_unit"),
    }
    if status != "explicit":
        return {
            "field": "quantity",
            "scored": False,
            "passed": None,
            "actual": actual_value,
            "gold": {"status": status},
            "reason": (
                "quantity_ambiguous_in_input"
                if status == "ambiguous"
                else "quantity_missing_in_input"
            ),
        }
    expected_value = {"amount": gold.get("amount"), "unit": gold.get("unit")}
    raw_match = _exact(actual_value, expected_value)
    return {
        "field": "quantity",
        "scored": True,
        "passed": bool(ai_success and raw_match),
        "raw_match": raw_match,
        "actual": actual_value,
        "gold": expected_value,
        "reason": None if ai_success and raw_match else (
            "fallback_excluded" if raw_match and not ai_success else "exact_mismatch"
        ),
    }


def _item_recognition_result(
    *, actual_name: Any, gold: dict[str, Any], ai_success: bool
) -> dict[str, Any]:
    expected_names = gold.get("names")
    expected_count = gold.get("item_count")
    if not isinstance(expected_names, list) or not isinstance(expected_count, int):
        return {
            "field": "item_recognition",
            "scored": False,
            "passed": None,
            "actual": {"name": actual_name, "item_count": 1 if actual_name else 0},
            "gold": None,
            "reason": "item_count_or_names_not_determined_from_input",
        }
    actual_count = 1 if isinstance(actual_name, str) and actual_name.strip() else 0
    actual_norm = _norm_text(actual_name)
    expected_norm = [_norm_text(name) for name in expected_names]
    raw_match = actual_count == expected_count and expected_norm == [actual_norm]
    return {
        "field": "item_recognition",
        "scored": True,
        "passed": bool(ai_success and raw_match),
        "raw_match": raw_match,
        "actual": {"name": actual_name, "item_count": actual_count},
        "gold": {"names": expected_names, "item_count": expected_count},
        "reason": None if ai_success and raw_match else (
            "fallback_excluded" if raw_match and not ai_success else (
                "single_item_schema_cannot_represent_multiple_items"
                if expected_count > 1
                else "exact_mismatch"
            )
        ),
    }


def _parse_output(
    router: Any,
    case: dict[str, Any],
    *,
    food_schema: Any,
    activity_schema: Any,
    food_fallback: Any,
    activity_fallback: Any,
) -> tuple[dict[str, Any], Any, str, str]:
    kind = case["kind"]
    if kind == "food":
        schema = food_schema
        capability = FOOD_CAPABILITY
        system_prompt = FOOD_SYSTEM_PROMPT
        fallback_factory = lambda: food_fallback(case["input"])
    else:
        schema = activity_schema
        capability = ACTIVITY_CAPABILITY
        system_prompt = ACTIVITY_SYSTEM_PROMPT
        fallback_factory = lambda: activity_fallback(case["input"])
    invocation = router.generate(
        capability,
        schema,
        system_prompt=system_prompt,
        user_prompt=case["input"],
        fallback_factory=fallback_factory,
    )
    parsed = schema.model_validate(invocation.output)
    return parsed.model_dump(mode="json"), invocation, capability, system_prompt


def _configuration(router: Any, modules: dict[str, Any]) -> dict[str, Any]:
    settings = router.settings
    schemas = {
        "intent_classification": modules["IntentPlan"],
        "food_text_parse": modules["FoodParsed"],
        "activity_text_parse": modules["ActivityParsed"],
    }
    prompts = {
        "intent_classification": {
            "version": modules["ROUTER_PROMPT_VERSION"],
            "sha256": _json_hash(modules["ROUTER_SYSTEM_PROMPT"]),
        },
        "food_text_parse": {
            "version": "food-text-parse-1.0.0",
            "sha256": _json_hash(FOOD_SYSTEM_PROMPT),
        },
        "activity_text_parse": {
            "version": "activity-text-parse-1.0.0",
            "sha256": _json_hash(ACTIVITY_SYSTEM_PROMPT),
        },
    }
    models = {
        capability: {
            "requested_model": router.model_for(capability),
            "temperature": FIXED_MODEL_PARAMETERS["temperature"],
            "adapter_max_retries": FIXED_MODEL_PARAMETERS["adapter_max_retries"],
            "router_max_retries": int(settings.agent_max_retries),
            "timeout_seconds": int(settings.agent_timeout_seconds),
            "max_output_tokens": int(settings.agent_max_output_tokens),
            "structured_output": FIXED_MODEL_PARAMETERS["structured_output"],
        }
        for capability in schemas
    }
    schema_info = {
        capability: {
            "name": schema.__name__,
            "module": schema.__module__,
            "json_schema_sha256": _json_hash(schema.model_json_schema()),
        }
        for capability, schema in schemas.items()
    }
    return {
        "provider": settings.agent_provider,
        "prompts": prompts,
        "schemas": schema_info,
        "models": models,
        "configuration_sha256": _json_hash(
            {"provider": settings.agent_provider, "prompts": prompts, "schemas": schema_info, "models": models}
        ),
    }


def _modules() -> dict[str, Any]:
    """Import app modules only after runtime.configure() has set DATABASE_URL."""

    from app.agent.intent_router import ROUTER_PROMPT_VERSION, ROUTER_SYSTEM_PROMPT, route_intents
    from app.agent.model_router import SCHEMA_VERSION
    from app.agent.tools import _activity_fallback, _food_fallback
    from app.schemas.agent import ActivityParsed, FoodParsed, IntentPlan

    return {
        "route_intents": route_intents,
        "ROUTER_PROMPT_VERSION": ROUTER_PROMPT_VERSION,
        "ROUTER_SYSTEM_PROMPT": ROUTER_SYSTEM_PROMPT,
        "SCHEMA_VERSION": SCHEMA_VERSION,
        "_activity_fallback": _activity_fallback,
        "_food_fallback": _food_fallback,
        "ActivityParsed": ActivityParsed,
        "FoodParsed": FoodParsed,
        "IntentPlan": IntentPlan,
    }


def _evaluate_case(router: Any, case: dict[str, Any], modules: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    route_invocation: Any | None = None
    parse_invocation: Any | None = None
    actual: dict[str, Any] | None = None
    route_actual: list[str] = []
    field_results: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        route_plan, route_invocation = modules["route_intents"](router, case["input"])
        route_actual = [item.intent for item in route_plan.intents]
        route_ai_success = not route_invocation.fallback_used and route_invocation.error_code is None
        expected_intents = case["expected_intents"]
        route_raw_match = route_actual == expected_intents
        route_result = {
            "field": "route_exact",
            "scored": True,
            "passed": bool(route_ai_success and route_raw_match),
            "raw_match": route_raw_match,
            "actual": route_actual,
            "gold": expected_intents,
            "reason": None if route_ai_success and route_raw_match else (
                "fallback_excluded" if route_raw_match and not route_ai_success else "exact_mismatch"
            ),
        }
        field_results.append(route_result)
    except Exception as error:  # preserve the case and continue the batch
        errors.append(f"route:{type(error).__name__}")
        route_ai_success = False
        field_results.append(
            {
                "field": "route_exact",
                "scored": True,
                "passed": False,
                "actual": route_actual,
                "gold": case["expected_intents"],
                "reason": "execution_error",
            }
        )

    try:
        actual, parse_invocation, capability, parse_prompt = _parse_output(
            router,
            case,
            food_schema=modules["FoodParsed"],
            activity_schema=modules["ActivityParsed"],
            food_fallback=modules["_food_fallback"],
            activity_fallback=modules["_activity_fallback"],
        )
        parse_ai_success = not parse_invocation.fallback_used and parse_invocation.error_code is None
        gold = case["gold"]
        if case["kind"] == "food":
            field_results.append(
                _field_result(
                    field="meal_type",
                    actual=actual.get("meal_type"),
                    expected=gold.get("meal_type"),
                    ai_success=parse_ai_success,
                )
            )
            field_results.append(
                _field_result(
                    field="name",
                    actual=actual.get("name"),
                    expected=gold.get("name"),
                    ai_success=parse_ai_success,
                )
            )
            field_results.append(
                _item_recognition_result(
                    actual_name=actual.get("name"), gold=gold, ai_success=parse_ai_success
                )
            )
            field_results.append(
                _quantity_result(
                    actual=actual, gold=gold.get("quantity"), ai_success=parse_ai_success
                )
            )
            field_results.append(
                _field_result(
                    field="explicit_energy_kcal",
                    actual=actual.get("energy_kcal"),
                    expected=gold.get("explicit_energy_kcal"),
                    ai_success=parse_ai_success,
                    reason="energy_not_explicit_in_input",
                )
            )
        else:
            field_results.append(
                _field_result(
                    field="name",
                    actual=actual.get("name"),
                    expected=gold.get("name"),
                    ai_success=parse_ai_success,
                )
            )
            field_results.append(
                _item_recognition_result(
                    actual_name=actual.get("name"), gold=gold, ai_success=parse_ai_success
                )
            )
            field_results.append(
                _field_result(
                    field="duration_minutes",
                    actual=actual.get("duration_minutes"),
                    expected=gold.get("duration_minutes"),
                    ai_success=parse_ai_success,
                    reason="duration_not_exactly_determined_from_input",
                )
            )
            field_results.append(
                _field_result(
                    field="intensity",
                    actual=actual.get("intensity"),
                    expected=gold.get("intensity"),
                    ai_success=parse_ai_success,
                    reason="intensity_not_explicit_in_input",
                )
            )
            field_results.append(
                _field_result(
                    field="explicit_energy_kcal",
                    actual=actual.get("energy_kcal"),
                    expected=gold.get("explicit_energy_kcal"),
                    ai_success=parse_ai_success,
                    reason="energy_not_explicit_in_input",
                )
            )
    except Exception as error:
        errors.append(f"parse:{type(error).__name__}")
        parse_ai_success = False
        capability = FOOD_CAPABILITY if case["kind"] == "food" else ACTIVITY_CAPABILITY
        parse_prompt = FOOD_SYSTEM_PROMPT if case["kind"] == "food" else ACTIVITY_SYSTEM_PROMPT
        actual = None

    invocations = []
    if route_invocation is not None:
        invocations.append(
            {"capability": ROUTER_CAPABILITY, **_invocation_dict(route_invocation)}
        )
    if parse_invocation is not None:
        invocations.append({"capability": capability, **_invocation_dict(parse_invocation)})
    gold = case["gold"]
    record_status = gold.get("record_status", "complete")
    schema_limitations = list(case.get("schema_limitations", []))
    if gold.get("item_count", 1) > 1:
        schema_limitations.append("current_structured_parser_schema_has_one_name_field")
    if case.get("operation") in {"modify", "delete", "repeat"}:
        schema_limitations.append("operation_is_metadata_and_not_represented_in_parse_schema")
    scored_fields = [item for item in field_results if item.get("scored")]
    raw_matches = [item for item in scored_fields if item.get("raw_match")]
    passed_fields = [item for item in scored_fields if item.get("passed")]
    fully_scored = not any(not item.get("scored") for item in field_results[1:])
    basic_pass = (
        not errors
        and route_ai_success
        and parse_ai_success
        and len(scored_fields) == len(passed_fields)
        and record_status == "complete"
    )
    if record_status in {"unjudgeable", "insufficient", "schema_limited", "mixed"}:
        evaluation_status = record_status
        case_passed = False
    elif basic_pass and fully_scored:
        evaluation_status = "pass"
        case_passed = True
    elif basic_pass:
        evaluation_status = "partial_pass_unscored_fields"
        case_passed = True
    else:
        evaluation_status = "fail"
        case_passed = False
    return {
        "schema_version": RAW_SCHEMA_VERSION,
        "evaluation_version": EVALUATION_VERSION,
        "dataset_case_id": case["id"],
        "kind": case["kind"],
        "scenario": case.get("scenario"),
        "operation": case.get("operation"),
        "input": case["input"],
        "gold_status": case.get("gold_status", GOLD_STATUS),
        "gold_record_status": record_status,
        "expected_intents": case["expected_intents"],
        "actual_intents": route_actual,
        "actual": actual,
        "field_results": field_results,
        "route_ai_success": route_ai_success,
        "parse_ai_success": parse_ai_success,
        "case_passed": case_passed,
        "fully_scored": fully_scored,
        "evaluation_status": evaluation_status,
        "schema_limitations": sorted(set(schema_limitations)),
        "errors": errors,
        "invocations": invocations,
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "parser_parameters": {
            "capability": capability if parse_invocation is not None else None,
            "system_prompt_sha256": _json_hash(parse_prompt),
            "structured_output": True,
        },
    }


def _read_raw(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid_parsing_jsonl_line:{line_number}") from error
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _append_raw(path: Path, row: dict[str, Any], *, dataset_sha256: str, config_sha256: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stored = {
        "dataset_sha256": dataset_sha256,
        "configuration_sha256": config_sha256,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        **row,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(stored, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _latest_rows(rows: list[dict[str, Any]], *, dataset_sha256: str, config_sha256: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("dataset_sha256") != dataset_sha256:
            raise ValueError("existing_parsing_jsonl_dataset_hash_mismatch")
        if row.get("configuration_sha256") != config_sha256:
            raise ValueError("existing_parsing_jsonl_configuration_hash_mismatch")
        case_id = row.get("dataset_case_id")
        if isinstance(case_id, str):
            latest[case_id] = row
    return latest


def _metric(rows: list[dict[str, Any]], field_name: str) -> dict[str, Any]:
    field_rows = [
        field
        for row in rows
        for field in row.get("field_results", [])
        if field.get("field") == field_name
    ]
    scored = [field for field in field_rows if field.get("scored")]
    raw_matches = sum(bool(field.get("raw_match")) for field in scored)
    passed = sum(bool(field.get("passed")) for field in scored)
    fallback_matches_ignored = sum(
        field.get("raw_match") is True and field.get("passed") is False
        and field.get("reason") == "fallback_excluded"
        for field in scored
    )
    return {
        "exact": _percent(passed, len(scored)),
        "matched_without_fallback_filter": raw_matches,
        "matched": passed,
        "scored": len(scored),
        "unscored": len(field_rows) - len(scored),
        "fallback_matches_ignored": fallback_matches_ignored,
    }


def _summary(
    *,
    dataset: dict[str, Any],
    dataset_path: Path,
    raw_path: Path,
    summary_path: Path,
    rows: dict[str, dict[str, Any]],
    configuration: dict[str, Any] | None,
    execution_mode: str,
    started_at: str,
) -> dict[str, Any]:
    case_rows = list(rows.values())
    food_rows = [row for row in case_rows if row.get("kind") == "food"]
    activity_rows = [row for row in case_rows if row.get("kind") == "activity"]
    all_invocations = [item for row in case_rows for item in row.get("invocations", [])]
    fallback_count = sum(bool(item.get("fallback_used")) for item in all_invocations)
    ai_success_count = sum(
        not item.get("fallback_used") and item.get("error_code") is None
        for item in all_invocations
    )
    route_metric = _metric(case_rows, "route_exact")
    food_metrics = {
        field: _metric(food_rows, field)
        for field in ("meal_type", "name", "item_recognition", "quantity", "explicit_energy_kcal")
    }
    activity_metrics = {
        field: _metric(activity_rows, field)
        for field in ("name", "item_recognition", "duration_minutes", "intensity", "explicit_energy_kcal")
    }
    statuses = Counter(row.get("evaluation_status", "unknown") for row in case_rows)
    scenario_counts: dict[str, dict[str, int]] = {}
    for row in case_rows:
        scenario = row.get("scenario") or "unspecified"
        bucket = scenario_counts.setdefault(scenario, {"cases": 0, "passed": 0, "failed": 0})
        bucket["cases"] += 1
        bucket["passed"] += int(bool(row.get("case_passed")))
        bucket["failed"] += int(not row.get("case_passed"))
    latency = [int(row.get("latency_ms", 0)) for row in case_rows]
    total_cases = len(dataset["cases"])
    completed = len(case_rows)
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "evaluation_version": EVALUATION_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "started_at": started_at,
        "execution_mode": execution_mode,
        "status": "complete" if completed == total_cases else "partial",
        "dataset_version": dataset.get("dataset_version"),
        "dataset_sha256": _sha256(dataset_path),
        "gold_status": dataset.get("gold_status"),
        "dataset": {
            "path": str(dataset_path),
            "cases": total_cases,
            "food_cases": sum(case.get("kind") == "food" for case in dataset["cases"]),
            "activity_cases": sum(case.get("kind") == "activity" for case in dataset["cases"]),
            "completed_rows": completed,
            "remaining_rows": total_cases - completed,
        },
        "configuration": configuration,
        "metrics": {
            "route_intents_exact": route_metric,
            "food": food_metrics,
            "activity": activity_metrics,
            "case_pass_rate": {
                "passed": sum(bool(row.get("case_passed")) for row in case_rows),
                "completed": completed,
                "rate": _percent(sum(bool(row.get("case_passed")) for row in case_rows), completed),
            },
            "fully_scored_case_pass_rate": {
                "passed": sum(bool(row.get("case_passed")) and row.get("fully_scored") for row in case_rows),
                "fully_scored": sum(bool(row.get("fully_scored")) for row in case_rows),
                "rate": _percent(
                    sum(bool(row.get("case_passed")) and row.get("fully_scored") for row in case_rows),
                    sum(bool(row.get("fully_scored")) for row in case_rows),
                ),
            },
        },
        "counts": {
            "fallback_invocations": fallback_count,
            "ai_success_invocations": ai_success_count,
            "invocations": len(all_invocations),
            "case_statuses": dict(sorted(statuses.items())),
            "schema_limited_or_unjudgeable_cases": sum(
                row.get("evaluation_status") in {"unjudgeable", "insufficient", "schema_limited", "mixed"}
                for row in case_rows
            ),
        },
        "usage": {
            "input_tokens": sum(int(item.get("input_tokens", 0)) for item in all_invocations),
            "output_tokens": sum(int(item.get("output_tokens", 0)) for item in all_invocations),
            "retries": sum(int(item.get("retries", 0)) for item in all_invocations),
            "estimated_cost_usd": round(sum(float(item.get("estimated_cost_usd", 0)) for item in all_invocations), 8),
            "latency_p50_ms": _percentile(latency, 0.50),
            "latency_p95_ms": _percentile(latency, 0.95),
        },
        "scenario_counts": dict(sorted(scenario_counts.items())),
        "raw_jsonl": str(raw_path),
        "summary_path": str(summary_path),
        "limitations": [
            "gold is agent-authored and pending human review; no human-review claim is made",
            "energy is scored only when an explicit kcal value appears in the input",
            "quantity is scored only for an input-determinable explicit amount and unit; ambiguous or missing quantity is retained as unscored",
            "FoodParsed and ActivityParsed each expose one name, so multi-item inputs remain explicit schema failures",
            "operation metadata for modification/repeat/delete is recorded but is not represented in the current parsing schemas",
            "fallback outputs are retained for diagnosis and excluded from every AI-success metric",
        ],
    }


def _write_summary(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the fixed Chinese health parsing evaluation against the configured real provider."
    )
    parser.add_argument("--execute", action="store_true", help="opt in to provider calls")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--raw-output", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    dataset = _load_dataset(args.dataset)
    dataset_hash = _sha256(args.dataset)
    existing_rows = _read_raw(args.raw_output)
    if not args.execute:
        completed_ids = {
            row.get("dataset_case_id")
            for row in existing_rows
            if row.get("dataset_sha256") == dataset_hash
            and row.get("execution_status", "completed") == "completed"
        }
        print(
            json.dumps(
                {
                    "status": "dry_run",
                    "dataset": str(args.dataset),
                    "dataset_version": dataset.get("dataset_version"),
                    "cases": len(dataset["cases"]),
                    "food_cases": sum(case.get("kind") == "food" for case in dataset["cases"]),
                    "activity_cases": sum(case.get("kind") == "activity" for case in dataset["cases"]),
                    "provider_calls": 0,
                    "resume_candidates": len(completed_ids),
                    "execute_command": "python scripts/evaluation/parsing.py --execute",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0

    # The runtime is the only owner of .env loading, database selection and
    # synthetic user consent.  This script never assigns DATABASE_URL.
    from scripts.evaluation.runtime import real_router

    started_at = datetime.now(timezone.utc).isoformat()
    with real_router() as router:
        modules = _modules()
        configuration = _configuration(router, modules)
        config_hash = configuration["configuration_sha256"]
        latest = _latest_rows(
            existing_rows, dataset_sha256=dataset_hash, config_sha256=config_hash
        )
        settings = router.settings
        if settings.agent_provider == "mock":
            raise RuntimeError("real_parsing_evaluation_refuses_mock_provider")
        _write_summary(
            args.summary_output,
            _summary(
                dataset=dataset,
                dataset_path=args.dataset,
                raw_path=args.raw_output,
                summary_path=args.summary_output,
                rows=latest,
                configuration=configuration,
                execution_mode="real",
                started_at=started_at,
            ),
        )
        for index, case in enumerate(dataset["cases"], start=1):
            case_id = case["id"]
            prior = latest.get(case_id)
            # Provider fallbacks are retryable on a resumed run.  This keeps a
            # transient outage from becoming a reported AI success.
            prior_is_final = bool(
                prior
                and prior.get("execution_status", "completed") == "completed"
                and all(
                    not invocation.get("fallback_used") and invocation.get("error_code") is None
                    for invocation in prior.get("invocations", [])
                )
            )
            if prior_is_final:
                continue
            try:
                row = _evaluate_case(router, case, modules)
                row["execution_status"] = "completed"
            except Exception as error:  # keep the batch resumable without logging secrets
                row = {
                    "schema_version": RAW_SCHEMA_VERSION,
                    "evaluation_version": EVALUATION_VERSION,
                    "dataset_case_id": case_id,
                    "kind": case["kind"],
                    "scenario": case.get("scenario"),
                    "input": case["input"],
                    "gold_status": case.get("gold_status", GOLD_STATUS),
                    "execution_status": "error",
                    "error_type": type(error).__name__,
                    "invocations": [],
                    "field_results": [],
                    "case_passed": False,
                    "fully_scored": False,
                }
            _append_raw(
                args.raw_output,
                row,
                dataset_sha256=dataset_hash,
                config_sha256=config_hash,
            )
            latest[case_id] = {
                "dataset_sha256": dataset_hash,
                "configuration_sha256": config_hash,
                **row,
            }
            _write_summary(
                args.summary_output,
                _summary(
                    dataset=dataset,
                    dataset_path=args.dataset,
                    raw_path=args.raw_output,
                    summary_path=args.summary_output,
                    rows=latest,
                    configuration=configuration,
                    execution_mode="real",
                    started_at=started_at,
                ),
            )
            print(f"parsing evaluation: {index}/{len(dataset['cases'])}", flush=True)
    final = _summary(
        dataset=dataset,
        dataset_path=args.dataset,
        raw_path=args.raw_output,
        summary_path=args.summary_output,
        rows=latest,
        configuration=configuration,
        execution_mode="real",
        started_at=started_at,
    )
    _write_summary(args.summary_output, final)
    print(
        json.dumps(
            {
                "status": final["status"],
                "cases": final["dataset"]["completed_rows"],
                "remaining": final["dataset"]["remaining_rows"],
                "provider": final["configuration"]["provider"],
                "fallback_invocations": final["counts"]["fallback_invocations"],
                "summary": str(args.summary_output),
                "raw": str(args.raw_output),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
