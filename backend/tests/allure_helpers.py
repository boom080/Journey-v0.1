"""Safe Allure attachments for interview-friendly test evidence."""

from __future__ import annotations

import json
from typing import Any

import allure

_REDACTED = "[REDACTED]"
_SENSITIVE_KEY_PARTS = (
    "authorization",
    "token",
    "api_key",
    "apikey",
    "password",
    "secret",
    "message",
    "segment",
)


def sanitize_for_report(value: Any) -> Any:
    """Recursively redact credentials and raw user/model input from report data."""
    if isinstance(value, dict):
        return {
            key: (
                _REDACTED
                if any(part in key.lower() for part in _SENSITIVE_KEY_PARTS)
                else sanitize_for_report(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_for_report(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_for_report(item) for item in value]
    return value


def attach_json(name: str, payload: Any) -> None:
    """Attach sanitized JSON to Allure when the plugin is active."""
    allure.attach(
        json.dumps(sanitize_for_report(payload), ensure_ascii=False, indent=2),
        name=name,
        attachment_type=allure.attachment_type.JSON,
    )
