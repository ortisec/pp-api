from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ProcessType, TimestampMixin
from app.db.session import Base

if TYPE_CHECKING:
    from app.models.users import Assignment
    from app.models.votes import TableParty, VoteRecord


class ElectoralProcess(Base, TimestampMixin):
    __tablename__ = "electoral_process"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    process_type: Mapped[ProcessType] = mapped_column(
        Enum(ProcessType, name="process_type"), nullable=False
    )
    election_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    provinces: Mapped[list["Province"]] = relationship(back_populates="process")
    parties: Mapped[list["PoliticalParty"]] = relationship(back_populates="process")


class Province(Base, TimestampMixin):
    __tablename__ = "province"
    __table_args__ = (UniqueConstraint("process_id", "ubigeo", name="uq_province_proc_ubigeo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int] = mapped_column(
        ForeignKey("electoral_process.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    ubigeo: Mapped[str] = mapped_column(String(6), nullable=False)

    process: Mapped[ElectoralProcess] = relationship(back_populates="provinces")
    districts: Mapped[list["District"]] = relationship(back_populates="province")


class District(Base, TimestampMixin):
    __tablename__ = "district"
    __table_args__ = (UniqueConstraint("process_id", "ubigeo", name="uq_district_proc_ubigeo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int] = mapped_column(
        ForeignKey("electoral_process.id", ondelete="CASCADE"), nullable=False
    )
    province_id: Mapped[int] = mapped_column(
        ForeignKey("province.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    ubigeo: Mapped[str] = mapped_column(String(6), nullable=False)

    province: Mapped[Province] = relationship(back_populates="districts")
    schools: Mapped[list["School"]] = relationship(back_populates="district")


class School(Base, TimestampMixin):
    __tablename__ = "school"
    __table_args__ = (UniqueConstraint("process_id", "local_id", name="uq_school_proc_local"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int] = mapped_column(
        ForeignKey("electoral_process.id", ondelete="CASCADE"), nullable=False
    )
    district_id: Mapped[int] = mapped_column(
        ForeignKey("district.id", ondelete="CASCADE"), nullable=False
    )
    local_id: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)

    district: Mapped[District] = relationship(back_populates="schools")
    tables: Mapped[list["PollingTable"]] = relationship(back_populates="school")


class PollingTable(Base, TimestampMixin):
    __tablename__ = "polling_table"
    __table_args__ = (
        UniqueConstraint("process_id", "school_id", "number", name="uq_table_proc_school_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int] = mapped_column(
        ForeignKey("electoral_process.id", ondelete="CASCADE"), nullable=False
    )
    school_id: Mapped[int] = mapped_column(
        ForeignKey("school.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column(nullable=False)
    code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    electores_habilitados: Mapped[int] = mapped_column(default=0, nullable=False)

    school: Mapped[School] = relationship(back_populates="tables")
    vote_records: Mapped[list["VoteRecord"]] = relationship(back_populates="table")
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="table")
    table_parties: Mapped[list["TableParty"]] = relationship(back_populates="table")


class PoliticalParty(Base, TimestampMixin):
    __tablename__ = "political_party"
    __table_args__ = (UniqueConstraint("process_id", "name", name="uq_party_proc_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int] = mapped_column(
        ForeignKey("electoral_process.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)

    process: Mapped[ElectoralProcess] = relationship(back_populates="parties")
    candidates: Mapped[list["Candidate"]] = relationship(back_populates="party")


class Candidate(Base, TimestampMixin):
    __tablename__ = "candidate"

    id: Mapped[int] = mapped_column(primary_key=True)
    party_id: Mapped[int] = mapped_column(
        ForeignKey("political_party.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(
        Enum("GOBERNADOR", "CONSEJERO", "PROVINCIA", "DISTRITO", name="candidate_category"),
        nullable=False,
    )
    province_id: Mapped[int | None] = mapped_column(
        ForeignKey("province.id", ondelete="CASCADE"), nullable=True
    )
    district_id: Mapped[int | None] = mapped_column(
        ForeignKey("district.id", ondelete="CASCADE"), nullable=True
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)

    party: Mapped[PoliticalParty] = relationship(back_populates="candidates")
