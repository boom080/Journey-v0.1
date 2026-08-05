from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.media.food_image import analyze_food_image
from app.models.user import User
from app.schemas.media import FoodImageAnalysisResponse, FoodImageAnalyzeRequest

router = APIRouter(prefix="/food-images", tags=["Food images"])


@router.post("/analyses", response_model=FoodImageAnalysisResponse)
def create_food_image_analysis(
    payload: FoodImageAnalyzeRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return analyze_food_image(
        db,
        user,
        payload=payload,
        request_id=request.state.request_id,
    )
