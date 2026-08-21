from fastapi import APIRouter, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import engine
from app.core.settings import get_settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live")
def live() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "journey-api",
        "environment": get_settings().environment,
    }


@router.get("/ready")
def ready(response: Response) -> dict[str, str]:
    settings = get_settings()
    agent_mode = "MOCK" if settings.agent_provider == "mock" else "REAL"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            knowledge_chunks = connection.execute(
                text("SELECT COUNT(*) FROM knowledge_chunks")
            ).scalar_one()
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unavailable",
            "service": "journey-api",
            "environment": settings.environment,
            "database": "unavailable",
            "rag": "unavailable",
            "agent_mode": agent_mode,
            "agent_provider": settings.agent_provider,
        }

    return {
        "status": "ok",
        "service": "journey-api",
        "environment": settings.environment,
        "database": "ok",
        "rag": "ok" if knowledge_chunks else "empty",
        "agent_mode": agent_mode,
        "agent_provider": settings.agent_provider,
        "agent_model": settings.agent_default_model,
    }
