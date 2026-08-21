import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import install_error_handlers
from app.api.middleware import RequestContextMiddleware
from app.api.routes.health import router as health_router
from app.api.v1.router import router as api_v1_router
from app.core.logging import configure_app_logging
from app.core.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    configure_app_logging()
    logging.getLogger("journey").info(
        "Agent Provider: %s | provider=%s | model=%s",
        "MOCK" if settings.agent_provider == "mock" else "REAL",
        settings.agent_provider,
        settings.agent_default_model,
    )

    application = FastAPI(title="Journey API", version="1.0.0")
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Idempotency-Key",
            "If-Match-Version",
            "X-Request-ID",
        ],
        expose_headers=["X-Request-ID", "X-Response-Time-Ms"],
    )
    application.include_router(health_router)
    application.include_router(api_v1_router)
    install_error_handlers(application)

    return application


app = create_app()
