from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Category, RecordStatus, TimestampMixin, VoteType
from app.db.session import Base

if TYPE_CHECKING:
    from app.models.geography import PoliticalParty, PollingTable



class TableParty(Base, TimestampMixin):
    """Define que partidos/candidaturas aplican a cada mesa y categoria."""

    __tablename__ = "table_party"
    __table_args__ = (
        UniqueConstraint("table_id", "category", "party_id", name="uq_tableparty"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    table_id: Mapped[int] = mapped_column(
        ForeignKey("polling_table.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[Category] = mapped_column(
        Enum(Category, name="candidate_category"), nullable=False
    )
    party_id: Mapped[int] = mapped_column(
        ForeignKey("political_party.id", ondelete="CASCADE"), nullable=False
    )

    table: Mapped["PollingTable"] = relationship(back_populates="table_parties")
    party: Mapped["PoliticalParty"] = relationship()


class VoteRecord(Base, TimestampMixin):
    """Acta de una mesa para un proceso electoral."""

    __tablename__ = "vote_record"
    __table_args__ = (UniqueConstraint("table_id", name="uq_record_table"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    table_id: Mapped[int] = mapped_column(
        ForeignKey("polling_table.id", ondelete="CASCADE"), nullable=False
    )
    process_id: Mapped[int] = mapped_column(
        ForeignKey("electoral_process.id", ondelete="CASCADE"), nullable=False
    )
    electores_habilitados: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_asistentes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, name="record_status"), default=RecordStatus.BORRADOR, nullable=False
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
    )

    table: Mapped["PollingTable"] = relationship(back_populates="vote_records")
    entries: Mapped[list["VoteEntry"]] = relationship(
        back_populates="record", cascade="all, delete-orphan"
    )
    history: Mapped[list["VoteRecordHistory"]] = relationship(
        back_populates="record", cascade="all, delete-orphan"
    )


class VoteEntry(Base):
    __tablename__ = "vote_entry"

    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[int] = mapped_column(
        ForeignKey("vote_record.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[Category] = mapped_column(
        Enum(Category, name="candidate_category"), nullable=False
    )
    vote_type: Mapped[VoteType] = mapped_column(Enum(VoteType, name="vote_type"), nullable=False)
    party_id: Mapped[int | None] = mapped_column(
        ForeignKey("political_party.id", ondelete="CASCADE"), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    record: Mapped[VoteRecord] = relationship(back_populates="entries")
    party: Mapped["PoliticalParty"] = relationship()


class VoteRecordHistory(Base):
    __tablename__ = "vote_record_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[int] = mapped_column(
        ForeignKey("vote_record.id", ondelete="CASCADE"), nullable=False
    )
    changed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
    )
    snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    record: Mapped[VoteRecord] = relationship(back_populates="history")
