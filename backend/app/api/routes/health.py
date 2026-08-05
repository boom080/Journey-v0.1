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
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unavailable",
            "service": "journey-api",
            "environment": get_settings().environment,
            "database": "unavailable",
        }

    return {
        "status": "ok",
        "service": "journey-api",
        "environment": get_settings().environment,
        "database": "ok",
    }
