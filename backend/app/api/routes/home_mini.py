from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps_mini import get_activated_user, get_db
from app.models.user import User
from app.schemas.home_mini import HomeSummaryResponse
from app.services.home_mini import build_home_summary

router = APIRouter(prefix="/home", tags=["Home"])


@router.get("/summary", response_model=HomeSummaryResponse)
def get_home_summary(
    current_user: User = Depends(get_activated_user),
    db: Session = Depends(get_db),
):
    return build_home_summary(db, current_user)
