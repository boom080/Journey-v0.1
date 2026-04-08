import logging
import sys


def configure_app_logging():
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    app_logger = logging.getLogger("journey")
    app_logger.handlers.clear()
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False
    app_logger.addHandler(handler)

    # Let child loggers under "journey.*" inherit this handler.
    for logger_name in [
        "journey.auth",
        "journey.ai.route",
        "journey.ai.service",
        "journey.ai.client",
        "journey.wechat",
    ]:
        child_logger = logging.getLogger(logger_name)
        child_logger.setLevel(logging.INFO)
        child_logger.propagate = True
