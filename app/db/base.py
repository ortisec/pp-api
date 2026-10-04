import enum
from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Role(enum.StrEnum):
    ADMIN = "ADMIN"
    PERSONERO_MESA = "PERSONERO_MESA"
    PERSONERO_LOCAL = "PERSONERO_LOCAL"


class ProcessType(enum.StrEnum):
    REGIONAL = "REGIONAL"
    MUNICIPAL = "MUNICIPAL"


class Category(enum.StrEnum):
    GOBERNADOR = "GOBERNADOR"
    CONSEJERO = "CONSEJERO"
    PROVINCIA = "PROVINCIA"
    DISTRITO = "DISTRITO"


# Categorias activas de votacion (unicamente distrital y provincial)
ACTIVE_CATEGORIES: tuple[Category, ...] = (Category.PROVINCIA, Category.DISTRITO)


class VoteType(enum.StrEnum):
    VALIDO = "VALIDO"
    NULO = "NULO"
    BLANCO = "BLANCO"


class RecordStatus(enum.StrEnum):
    BORRADOR = "BORRADOR"
    CONFIRMADO = "CONFIRMADO"

