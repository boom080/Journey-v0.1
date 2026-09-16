"""Isolated synthetic evaluation runtime; never uses the application's database."""
import os
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, UTC
import uuid

ROOT = Path(__file__).resolve().parents[2]
DB_URL = 'postgresql+psycopg://p668@127.0.0.1:55439/journey_resume_eval'

def configure(real=True):
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    from dotenv import dotenv_values
    if real:
        for key, value in dotenv_values(ROOT / '.env').items():
            if value is not None and (key.startswith(('AGENT_', 'DEEPSEEK_', 'QWEN_', 'OPENAI_', 'GLM_', 'KIMI_'))):
                os.environ[key] = value
    os.environ.update(DATABASE_URL=DB_URL if real else DB_URL.replace("journey_resume_eval", "journey_test"), APP_ENV='local' if real else 'test',
        APP_SECRET_KEY='local-evaluation-synthetic-secret-2026', SEED_TEST_ACCOUNT='false',
        SEED_BUILTIN_KNOWLEDGE='true', AGENT_V2_ENABLED='true', AGENT_V3_ENABLED='true')
    if not real:
        for key in list(os.environ):
            if key.startswith(('AGENT_', 'DEEPSEEK_', 'QWEN_', 'OPENAI_', 'GLM_', 'KIMI_', 'FOOD_IMAGE_')):
                os.environ.pop(key)
        os.environ.update(AGENT_PROVIDER_REVIEW_REQUIRED='true', AGENT_V2_ENABLED='true', AGENT_V3_ENABLED='true', FOOD_IMAGE_PROVIDER='mock', FOOD_IMAGE_ANALYSIS_ENABLED='true')
        os.environ.update(AGENT_PROVIDER='mock', AGENT_DEFAULT_MODEL='journey-deterministic-v1')
    from app.core.settings import get_settings
    get_settings.cache_clear()
    return get_settings()

@contextmanager
def real_router(user_key="00000000-0000-4000-8000-000000000091"):
    settings = configure(True)
    from app.core.database import SessionLocal
    from app.models.user import User
    from app.models.agent_privacy import AgentConsent
    from app.services.agent_privacy import policy_version
    from app.agent.model_router import ModelRouter
    with SessionLocal() as db:
        user_id = uuid.UUID(user_key)
        if db.get(User, user_id) is None:
            db.add(User(id=user_id)); db.flush()
        # Explicit user request authorizes these synthetic evaluation inputs.
        consent = db.get(AgentConsent, user_id)
        if consent is None:
            consent = AgentConsent(user_id=user_id); db.add(consent)
        consent.policy_version = policy_version(settings)
        consent.granted_at = datetime.now(UTC)
        db.commit()
        yield ModelRouter(db, settings=settings, user_id=user_id)
        db.rollback()
