from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.base import Category, ProcessType, RecordStatus, Role, VoteType


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------
class DNILoginRequest(BaseModel):
    dni: str = Field(min_length=8, max_length=8)


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    full_name: str
    scopes: list["ScopeInfo"] = []


class ScopeInfo(BaseModel):
    table_id: int | None = None
    school_id: int | None = None


class MeResponse(BaseModel):
    id: int
    dni: str | None
    username: str | None
    full_name: str
    role: Role
    scopes: list[ScopeInfo]


# ---------- Catalogos ----------
class ProcessCreate(BaseModel):
    name: str
    year: int
    process_type: ProcessType
    election_date: date | None = None
    is_active: bool = True


class ProcessRead(ORMModel):
    id: int
    name: str
    year: int
    process_type: ProcessType
    election_date: date | None
    is_active: bool


class ProvinceCreate(BaseModel):
    process_id: int
    name: str
    ubigeo: str = Field(min_length=6, max_length=6)


class ProvinceRead(ORMModel):
    id: int
    process_id: int
    name: str
    ubigeo: str


class DistrictCreate(BaseModel):
    process_id: int
    province_id: int
    name: str
    ubigeo: str = Field(min_length=6, max_length=6)


class DistrictRead(ORMModel):
    id: int
    process_id: int
    province_id: int
    name: str
    ubigeo: str


class SchoolCreate(BaseModel):
    process_id: int
    district_id: int
    local_id: str
    name: str
    address: str | None = None


class SchoolRead(ORMModel):
    id: int
    process_id: int
    district_id: int
    local_id: str
    name: str
    address: str | None


class PollingTableCreate(BaseModel):
    process_id: int
    school_id: int
    number: int
    code: str | None = None
    electores_habilitados: int = 0


class PollingTableUpdate(BaseModel):
    number: int | None = Field(default=None, ge=0)
    code: str | None = None
    school_id: int | None = None
    electores_habilitados: int | None = Field(default=None, ge=0)


class PollingTableRead(ORMModel):
    id: int
    process_id: int
    school_id: int
    number: int
    code: str | None
    electores_habilitados: int


class SchoolUpdate(BaseModel):
    local_id: str | None = None
    name: str | None = None
    address: str | None = None
    district_id: int | None = None


class DistrictUpdate(BaseModel):
    name: str | None = None
    ubigeo: str | None = Field(default=None, min_length=6, max_length=6)
    province_id: int | None = None


class ProvinceUpdate(BaseModel):
    name: str | None = None
    ubigeo: str | None = Field(default=None, min_length=6, max_length=6)


class PoliticalPartyUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    color: str | None = None


class PoliticalPartyCreate(BaseModel):
    process_id: int
    name: str
    code: str | None = None
    color: str | None = None


class PoliticalPartyRead(ORMModel):
    id: int
    process_id: int
    name: str
    code: str | None
    color: str | None


class CandidateCreate(BaseModel):
    party_id: int
    category: Category
    province_id: int | None = None
    district_id: int | None = None
    full_name: str


class CandidateRead(ORMModel):
    id: int
    party_id: int
    category: Category
    province_id: int | None
    district_id: int | None
    full_name: str


class UserCreate(BaseModel):
    dni: str | None = Field(default=None, min_length=8, max_length=8)
    username: str | None = None
    password: str | None = None
    full_name: str
    phone: str | None = None
    role: Role
    table_id: int | None = None
    school_id: int | None = None


class UserUpdate(BaseModel):
    dni: str | None = Field(default=None, min_length=8, max_length=8)
    full_name: str | None = None
    phone: str | None = None
    username: str | None = None
    password: str | None = None
    is_active: bool | None = None
    table_id: int | None = None
    school_id: int | None = None
    clear_assignment: bool = False


class UserAssignmentInfo(BaseModel):
    id: int
    table_id: int | None = None
    school_id: int | None = None
    table_number: int | None = None
    table_code: str | None = None
    school_name: str | None = None


class UserRead(ORMModel):
    id: int
    dni: str | None
    username: str | None
    full_name: str
    phone: str | None
    role: Role
    is_active: bool
    assignments: list[UserAssignmentInfo] = []


class AssignmentCreate(BaseModel):
    user_id: int
    table_id: int | None = None
    school_id: int | None = None


class AssignmentRead(ORMModel):
    id: int
    user_id: int
    table_id: int | None
    school_id: int | None


class TablePartyCreate(BaseModel):
    table_id: int
    category: Category
    party_id: int


class TablePartyRead(ORMModel):
    id: int
    table_id: int
    category: Category
    party_id: int


# ---------- Votos ----------
class VoteEntryInput(BaseModel):
    category: Category
    vote_type: VoteType
    party_id: int | None = None
    quantity: int = Field(ge=0)


class VoteRecordInput(BaseModel):
    electores_habilitados: int | None = Field(default=None, ge=0)
    total_asistentes: int | None = Field(default=None, ge=0)
    comment: str | None = None
    entries: list[VoteEntryInput]


class VoteEntryRead(ORMModel):
    id: int
    category: Category
    vote_type: VoteType
    party_id: int | None
    quantity: int


class VoteRecordRead(ORMModel):
    id: int
    table_id: int
    process_id: int
    electores_habilitados: int
    total_asistentes: int
    status: RecordStatus
    comment: str | None
    created_by_id: int | None
    updated_by_id: int | None
    created_at: datetime
    updated_at: datetime
    entries: list[VoteEntryRead] = []


class ValidationResult(BaseModel):
    category: Category
    validos: int
    nulos: int
    blancos: int
    total_categoria: int
    total_asistentes: int
    ok: bool


class VoteRecordResponse(BaseModel):
    record: VoteRecordRead
    validation: list[ValidationResult]


class HistoryRead(ORMModel):
    id: int
    record_id: int
    changed_by_id: int | None
    reason: str | None
    created_at: datetime


# ---------- Resultados ----------
class PartyResult(BaseModel):
    party_id: int
    party_name: str
    color: str | None
    votes: int
    percentage: float


class CategoryResult(BaseModel):
    category: Category
    validos: int
    nulos: int
    blancos: int
    total: int
    parties: list[PartyResult]


class TableResult(BaseModel):
    table_id: int
    table_number: int
    school_name: str
    electores_habilitados: int
    total_asistentes: int
    ausentismo: int
    participation: float
    status: RecordStatus | None
    comment: str | None
    categories: list[CategoryResult]


class SummaryResponse(BaseModel):
    total_tables: int
    tables_reportadas: int
    tables_pendientes: int
    total_electores: int
    total_asistentes: int
    ausentismo: int
    participation: float
    comment_count: int


class RankingEntry(BaseModel):
    party_id: int
    party_name: str
    color: str | None
    votes: int
    percentage: float
    position: int


class CategoryRanking(BaseModel):
    category: Category
    total_validos: int
    ranking: list[RankingEntry]


class SchoolRankingEntry(BaseModel):
    school_id: int
    school_name: str
    district_name: str
    total_asistentes: int
    validos: int
    nulos: int
    blancos: int
    participation: float


class DistrictParticipation(BaseModel):
    district_id: int
    district_name: str
    province_name: str
    electores: int
    asistentes: int
    participation: float


class AnalyticsResponse(BaseModel):
    process_id: int
    rankings: list[CategoryRanking]
    school_ranking: list[SchoolRankingEntry]
    district_participation: list[DistrictParticipation]


TokenResponse.model_rebuild()
