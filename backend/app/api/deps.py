import uuid

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.modules.identity.constants import DEV_USER_ID
from app.modules.identity.models import User


def get_current_user(
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None),
) -> User:
    settings = get_settings()
    if x_user_id:
        try:
            user_id = uuid.UUID(x_user_id)
        except ValueError as exc:
            raise AppError("invalid_user", "El identificador de usuario no es válido.", 401) from exc
        user = db.get(User, user_id)
        if user is None or user.status != "active":
            raise AppError("unauthorized", "El usuario no está autorizado.", 401)
        return user
    if settings.is_development:
        user = db.get(User, DEV_USER_ID)
        if user is not None and user.status == "active":
            return user
    raise AppError(
        "unauthorized",
        "Se requiere un usuario autenticado. La autenticación de producción todavía no está habilitada.",
        401,
    )
