import logging
import sys
from typing import Any, Dict


def normalize_log_value(value: Any, fallback: str = "-") -> str:
    if value is None:
        return fallback

    text = str(value).strip()
    return text or fallback


def build_error_log_fields(error: Any = None) -> Dict[str, str]:
    if error is None or error == "":
        return {
            "error": "none",
            "error_type": "-",
            "error_message": "-",
        }

    if isinstance(error, BaseException):
        error_type = error.__class__.__name__
        error_message = str(error).strip() or repr(error).strip() or error_type
    else:
        error_type = "-"
        error_message = str(error).strip() or "-"

    return {
        "error": error_message,
        "error_type": error_type or "-",
        "error_message": error_message or "-",
    }


def configure_app_logging():
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    app_logger = logging.getLogger("journey")
    app_logger.handlers.clear()
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False
    app_logger.addHandler(handler)

    for logger_name in [
        "journey.mini.auth",
        "journey.mini.ai.route",
        "journey.mini.ai.service",
        "journey.mini.ai.client",
        "journey.mini.wechat",
    ]:
        child_logger = logging.getLogger(logger_name)
        child_logger.setLevel(logging.INFO)
        child_logger.propagate = True
