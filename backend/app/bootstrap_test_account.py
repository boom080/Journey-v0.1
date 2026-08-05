import logging

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.settings import get_settings
from app.repositories.users import get_user_by_identifier
from app.schemas.auth import RegisterRequest
from app.services.auth import create_user

logger = logging.getLogger("journey.bootstrap")


def seed_test_account(db: Session | None = None) -> bool:
    settings = get_settings()
    if not settings.seed_test_account:
        return False
    owns_session = db is None
    session = db or SessionLocal()
    try:
        if get_user_by_identifier(session, settings.test_account_email) is not None:
            return False
        create_user(
            session,
            RegisterRequest(
                email=settings.test_account_email,
                username=settings.test_account_username,
                password=settings.test_account_password,
                display_name="Journey 测试用户",
            ),
        )
        session.commit()
        logger.info(
            "test_account_seeded email=%s username=%s",
            settings.test_account_email,
            settings.test_account_username,
        )
        return True
    finally:
        if owns_session:
            session.close()


if __name__ == "__main__":
    seed_test_account()
