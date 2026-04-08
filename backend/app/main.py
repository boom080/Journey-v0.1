from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.activity_records_mini import router as activity_records_router
from app.api.routes.ai_mini import router as ai_router
from app.api.routes.auth_mini import router as auth_router
from app.api.routes.food_records_mini import router as food_records_router
from app.api.routes.home_mini import router as home_router
from app.api.routes.journey_mini import router as journey_router
from app.api.routes.profile_mini import router as profile_router
from app.core.bootstrap import bootstrap_database
from app.core.database import Base, engine
from app.core.logging import configure_app_logging
from app.models.activity_record import ActivityRecord
from app.models.food_record import FoodRecord
from app.models.invite_code import InviteCode
from app.models.profile import Profile
from app.models.user import User

configure_app_logging()
Base.metadata.create_all(bind=engine)
bootstrap_database(engine)

app = FastAPI(title="Journey Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(profile_router)
app.include_router(home_router)
app.include_router(food_records_router)
app.include_router(activity_records_router)
app.include_router(journey_router)


@app.get("/")
def root():
    return {
        "message": "Journey mini backend is running",
        "phase": "wechat-login-invite-main-flow"
    }
