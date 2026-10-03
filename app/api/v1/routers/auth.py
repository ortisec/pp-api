from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.db.base import Role
from app.db.session import get_db
from app.models import Assignment, User
from app.schemas import (
    AdminLoginRequest,
    DNILoginRequest,
    MeResponse,
    ScopeInfo,
    TokenResponse,
)
from app.services.security import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _scopes_for(db: Session, user: User) -> list[ScopeInfo]:
    rows = db.execute(select(Assignment).where(Assignment.user_id == user.id)).scalars().all()
    return [ScopeInfo(table_id=r.table_id, school_id=r.school_id) for r in rows]


def _token_for(db: Session, user: User) -> TokenResponse:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return TokenResponse(
        access_token=token,
        role=user.role,
        full_name=user.full_name,
        scopes=_scopes_for(db, user),
    )


@router.post("/login/dni", response_model=TokenResponse)
def login_dni(payload: DNILoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.execute(select(User).where(User.dni == payload.dni)).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "DNI no registrado")
    if user.role == Role.ADMIN:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Use el acceso de administrador")
    return _token_for(db, user)


@router.post("/login/admin", response_model=TokenResponse)
def login_admin(payload: AdminLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(
        payload.password, user.password_hash
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales invalidas")
    if user.role != Role.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No es administrador")
    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario inactivo")
    return _token_for(db, user)


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MeResponse:
    return MeResponse(
        id=user.id,
        dni=user.dni,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        scopes=_scopes_for(db, user),
    )
