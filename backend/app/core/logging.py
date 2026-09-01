import logging
import sys

import litellm

from app.core.privacy import PrivacyLogFilter


def configure_app_logging() -> None:
    litellm.turn_off_message_logging = True
    litellm.suppress_debug_info = True
    # No third-party prompt/response telemetry callbacks are approved by this contract.
    for callbacks in ("callbacks", "success_callback", "failure_callback", "input_callback"):
        setattr(litellm, callbacks, [])
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(PrivacyLogFilter())

    # Starlette re-raises unexpected errors after sending its safe response;
    # Uvicorn would otherwise print the raw exception (including SDK payloads).
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        server_logger = logging.getLogger(name)
        if not any(isinstance(item, PrivacyLogFilter) for item in server_logger.filters):
            server_logger.addFilter(PrivacyLogFilter())
        for server_handler in server_logger.handlers:
            if not any(isinstance(item, PrivacyLogFilter) for item in server_handler.filters):
                server_handler.addFilter(PrivacyLogFilter())

    # Third-party transport/callback logs are not an approved health-data sink.
    for name in (
        "litellm",
        "LiteLLM",
        "LiteLLM Router",
        "LiteLLM Proxy",
        "langchain",
        "langsmith",
        "openai",
        "httpx",
        "httpcore",
    ):
        sdk_logger = logging.getLogger(name)
        sdk_logger.handlers = [logging.NullHandler()]
        sdk_logger.propagate = False
        sdk_logger.disabled = True

    app_logger = logging.getLogger("journey")
    app_logger.handlers.clear()
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False
    app_logger.addHandler(handler)
