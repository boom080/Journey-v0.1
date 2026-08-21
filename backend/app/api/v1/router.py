from fastapi import APIRouter

from app.api.v1.activity_records import router as activity_router
from app.api.v1.agent import router as agent_router
from app.api.v1.aggregates import router as aggregate_router
from app.api.v1.auth import router as auth_router
from app.api.v1.food_images import router as food_image_router
from app.api.v1.food_records import router as food_router
from app.api.v1.inspirations import router as inspiration_router
from app.api.v1.profile import router as profile_router
from app.api.v1.weight_records import router as weight_router
from app.schemas.common import ErrorResponse

router = APIRouter(
    prefix="/api/v1",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Authentication failed"},
        404: {"model": ErrorResponse, "description": "Resource not found"},
        409: {"model": ErrorResponse, "description": "Resource conflict"},
        422: {"model": ErrorResponse, "description": "Validation failed"},
        500: {"model": ErrorResponse, "description": "Unexpected server error"},
    },
)
for child in (
    auth_router,
    profile_router,
    food_router,
    food_image_router,
    activity_router,
    weight_router,
    aggregate_router,
    inspiration_router,
    agent_router,
):
    router.include_router(child)
