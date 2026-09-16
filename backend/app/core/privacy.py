"""Bounded outbound context and credential/identifier redaction.

Not a claim of general-purpose PII detection: arbitrary health text is disclosed
in the consent notice. Operational traces never retain free-form text fields.
"""

import json
import logging
import re

REDACTED = "[REDACTED]"
PATTERNS = [
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{6,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)"),
    re.compile(r"(?<!\w)\d{17}[\dXx](?!\w)"),
    re.compile(
        r"(?i)(?:api[_-]?key|password|access_token|refresh_token|secret|密码|密钥)\s*[=:：]\s*[^\s,，;；\"}]+"
    ),
    re.compile(r"(?:姓名|住址|地址|身份证号|电话号码)\s*[=:：]\s*[^\s,，;；。\"}]+"),
]
PRIVATE_KEYS = {
    "user_id",
    "email",
    "phone",
    "username",
    "display_name",
    "birth_date",
    "address",
    "password",
    "api_key",
    "access_token",
    "refresh_token",
    "authorization",
    "confirmation_token",
}
TRACE_TEXT_KEYS = {
    "text",
    "message",
    "question",
    "query",
    "segment",
    "goal",
    "reason",
    "clarification_question",
    "detail",
    "note",
    "summary",
    "description",
}
SUMMARY_KEYS = {
    "media_type",
    "byte_length",
    "scale_reference_type",
    "scale_reference_size_cm",
    "candidate_created",
    "confidence",
    "scale_reference_used",
    "image_retained",
    "needs_user_correction",
    "image_bytes",
    "width",
    "height",
    "reference_provided",
    "input_length",
    "text_length",
    "intent_count",
    "intents",
    "selected_agents",
    "step_count",
    "allowed",
    "blocked_steps",
    "citation_count",
    "citation_fallback_used",
    "citation_verification",
    "profile_available",
    "days_returned",
    "kind",
    "energy_present",
    "duration_present",
    "value_present",
    "context_version",
    "estimated_tokens",
    "included_sources",
    "chunk_count",
    "retrieved_count",
    "insufficient_context",
    "deterministic",
    "range_days",
    "decision",
    "passed",
    "recoverable",
    "completed_steps",
    "skipped_steps",
    "failed_steps",
    "replan_count",
    "pending_confirmations",
    "period_days",
    "record_count_30d",
    "record_count_7d",
    "days_with_records_30d",
    "conditional",
    "query_present",
    "raw_records_sent",
    "knowledge_chunk_count",
    "llm_call_count",
    "finding_count",
    "suggestion_count",
}


def redact_text(value: str, private_values: tuple[str, ...] = ()) -> str:
    for private in sorted(private_values, key=len, reverse=True):
        if len(private) >= 2:
            value = value.replace(private, REDACTED)
    for pattern in PATTERNS:
        value = pattern.sub(REDACTED, value)
    return value


def redact_payload(value, private_values: tuple[str, ...] = (), *, trace: bool = False):
    if isinstance(value, dict):
        return {
            key: (REDACTED if item is not None else None)
            if key.lower() in PRIVATE_KEYS or (trace and key.lower() in TRACE_TEXT_KEYS)
            else redact_payload(item, private_values, trace=trace)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_payload(item, private_values, trace=trace) for item in value]
    return redact_text(value, private_values) if isinstance(value, str) else value


def trace_summary(value: dict) -> dict:
    return redact_payload(
        {key: item for key, item in value.items() if key in SUMMARY_KEYS}, trace=True
    )


def _pick(value, keys):
    return {key: value[key] for key in keys if key in value} if isinstance(value, dict) else {}


def minimal_context(context: dict) -> dict:
    """Use computed aggregates; never serialize profiles, record rows or DOB."""
    return {
        "range_days": context.get("range_days"),
        "goal": _pick(
            context.get("goal"), ("kind", "target_weight_kg", "daily_energy_target_kcal")
        ),
        "today": _pick(
            context.get("today"),
            ("intake_kcal", "activity_kcal", "net_kcal", "estimated_energy_balance_kcal", "counts"),
        ),
        "recent_totals": _pick(
            context.get("recent_totals"),
            (
                "range_days",
                "days_with_records",
                "intake_kcal",
                "activity_kcal",
                "recorded_balance_kcal",
                "estimated_resting_energy_kcal",
                "estimated_energy_balance_kcal",
                "food_count",
                "activity_count",
                "weight_count",
                "weight_change_kg",
                "average_daily_intake_kcal",
                "average_daily_activity_kcal",
            ),
        ),
    }


def _minimal_summary_period(value: dict) -> dict:
    return _pick(
        value,
        (
            "period_days",
            "start_date",
            "end_date",
            "record_count",
            "food_count",
            "activity_count",
            "weight_count",
            "total_intake_kcal",
            "total_activity_kcal",
            "days_with_records",
            "weight_change_kg",
        ),
    )


def minimal_summary_statistics(value: dict) -> dict:
    return {
        "last_30_days": _minimal_summary_period(value.get("last_30_days", {})),
        "last_7_days": _minimal_summary_period(value.get("last_7_days", {})),
        "goal": _pick(value.get("goal"), ("kind", "target_weight_kg", "daily_energy_target_kcal")),
    }


def _minimal_coach_window(value: dict) -> dict:
    return _pick(
        value,
        (
            "period_days",
            "record_days",
            "record_count",
            "food_days",
            "food_records",
            "days_with_at_least_two_meals",
            "average_intake_kcal_on_food_days",
            "meal_counts",
            "activity_days",
            "activity_sessions",
            "activity_minutes",
            "moderate_or_high_sessions",
            "weight_measurements",
            "weight_change_kg",
        ),
    )


def minimal_coach_signals(value: dict) -> dict:
    """Allow only derived behavior signals; never forward record rows or names."""
    return {
        "skill": _pick(value.get("skill"), ("name", "version")),
        "period": _minimal_coach_window(value.get("period", {})),
        "recent_7_days": _minimal_coach_window(value.get("recent_7_days", {})),
        "goal": _pick(value.get("goal"), ("kind", "target_weight_kg", "daily_energy_target_kcal")),
    }


def prepare_model_prompt(capability: str, prompt: str, private_values: tuple[str, ...] = ()) -> str:
    text_capabilities = {
        "intent_classification",
        "food_text_parse",
        "activity_text_parse",
        "weight_text_parse",
    }
    fields = {
        "intent_classification": ("message", "recent_thread_memory"),
        "task_planning": ("message", "intents", "recent_thread_memory", "tools", "specialists"),
        "knowledge_answer": ("question", "chunks"),
        "recommendation": ("context_version", "context", "chunks"),
        "weekly_summary": ("context_version", "context", "chunks"),
        "thirty_day_summary": ("period", "coach_signals", "knowledge"),
        "failure_replanning": (
            "step_id",
            "tool",
            "status",
            "error_type",
            "recoverable",
            "allowed_recovery_tools",
        ),
    }
    # Parse functions accept user text, even when the user entered valid JSON.
    if capability in text_capabilities - {"intent_classification"}:
        return redact_text(prompt[:6000], private_values)
    try:
        payload = json.loads(prompt)
    except (ValueError, TypeError):
        payload = None
    if not isinstance(payload, dict):
        if capability in text_capabilities:
            return redact_text(prompt[:6000], private_values)
        raise ValueError("invalid_structured_prompt")
    if capability == "intent_classification" and "message" not in payload:
        return redact_text(prompt[:6000], private_values)
    if capability not in fields:
        raise ValueError("unsupported_model_capability")
    payload = _pick(payload, fields[capability])
    if "message" in payload:
        payload["message"] = str(payload["message"])[:6000]
    if "context" in payload:
        payload["context"] = minimal_context(payload["context"])
    if "chunks" in payload:
        payload["chunks"] = [
            _pick(item, ("chunk_id", "title", "text")) for item in payload["chunks"][:5]
        ]
    if "statistics" in payload:
        payload["statistics"] = minimal_summary_statistics(payload["statistics"])
    if "coach_signals" in payload:
        payload["coach_signals"] = minimal_coach_signals(payload["coach_signals"])
    if "knowledge" in payload:
        payload["knowledge"] = [
            _pick(item, ("chunk_id", "title", "version", "text"))
            for item in payload["knowledge"][:3]
        ]
    if "recent_thread_memory" in payload:
        payload["recent_thread_memory"] = [
            _pick(
                item, ("intents", "status", "candidate_kinds", "confirmed_kinds", "answer_present")
            )
            for item in payload["recent_thread_memory"][-8:]
        ]
    result = json.dumps(redact_payload(payload, private_values), ensure_ascii=False)
    if len(result) > 24000:
        raise ValueError("model_context_budget_exceeded")
    return result


class PrivacyLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if (
            record.name == "uvicorn.access"
            and isinstance(record.args, tuple)
            and len(record.args) == 5
        ):
            # AccessFormatter needs this tuple intact. Do not log client IPs or
            # query strings, which may contain health text or credentials.
            _, method, path, http_version, status = record.args
            record.args = (
                "client",
                method,
                redact_text(str(path).split("?", 1)[0]),
                http_version,
                status,
            )
        else:
            record.msg = redact_text(record.getMessage())
            record.args = ()
        # SDK exceptions frequently embed complete request bodies or headers.
        if record.exc_info:
            record.msg += " [exception details withheld]"
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return True
