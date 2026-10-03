from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Role
from app.models import User


def seed(db: Session) -> None:
    """Crea unicamente el usuario administrador inicial.

    La base de datos arranca sin datos de negocio (procesos, geografia, partidos,
    mesas, usuarios personeros).
    """
    existing_admin = db.execute(
        select(User).where(User.role == Role.ADMIN)
    ).scalar_one_or_none()
    if existing_admin:
        return

    admin = User(
        username=settings.admin_username,
        password_hash=hash_password(settings.admin_password),
        full_name="Administrador General",
        role=Role.ADMIN,
    )
    db.add(admin)
    db.commit()
