from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.base import Role
from app.db.session import get_db
from app.models import Assignment, PollingTable, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login/admin", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado")
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    user_id = payload.get("sub")
    user = db.get(User, int(user_id)) if user_id else None
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario invalido o inactivo")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Requiere rol administrador")
    return user


def assigned_table_ids(db: Session, user: User) -> tuple[set[int], set[int]]:
    """Devuelve (table_ids_directos, school_ids) asignados al usuario."""
    rows = db.execute(select(Assignment).where(Assignment.user_id == user.id)).scalars().all()
    table_ids = {row.table_id for row in rows if row.table_id is not None}
    school_ids = {row.school_id for row in rows if row.school_id is not None}
    return table_ids, school_ids


def can_access_table(db: Session, user: User, table: PollingTable) -> bool:
    if user.role == Role.ADMIN:
        return True
    table_ids, school_ids = assigned_table_ids(db, user)
    if table.id in table_ids:
        return True
    return table.school_id in school_ids


def ensure_table_access(db: Session, user: User, table_id: int) -> PollingTable:
    table = db.get(PollingTable, table_id)
    if not table:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa no encontrada")
    if not can_access_table(db, user, table):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene acceso a esta mesa")
    return table
