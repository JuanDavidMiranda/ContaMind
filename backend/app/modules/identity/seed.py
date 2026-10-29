from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.identity.constants import DEV_USER_ID
from app.modules.identity.models import User


def seed_dev_user(session: Session) -> None:
    settings = get_settings()
    if not settings.is_development:
        return
    existing = session.get(User, DEV_USER_ID)
    if existing is not None:
        return
    by_email = session.scalar(select(User).where(User.email == settings.dev_user_email))
    if by_email is not None:
        return
    session.add(
        User(
            id=DEV_USER_ID,
            full_name=settings.dev_user_name,
            email=settings.dev_user_email,
            status="active",
        )
    )
    session.commit()
