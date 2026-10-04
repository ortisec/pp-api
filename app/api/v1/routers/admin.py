from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.base import Category, Role
from app.db.session import get_db
from app.models import (
    Assignment,
    Candidate,
    District,
    ElectoralProcess,
    PoliticalParty,
    PollingTable,
    Province,
    School,
    TableParty,
    User,
)
from app.schemas import (
    AssignmentCreate,
    AssignmentRead,
    CandidateCreate,
    CandidateRead,
    DistrictCreate,
    DistrictRead,
    DistrictUpdate,
    PoliticalPartyCreate,
    PoliticalPartyRead,
    PoliticalPartyUpdate,
    PollingTableCreate,
    PollingTableRead,
    PollingTableUpdate,
    ProcessCreate,
    ProcessRead,
    ProvinceCreate,
    ProvinceRead,
    ProvinceUpdate,
    SchoolCreate,
    SchoolRead,
    SchoolUpdate,
    TablePartyCreate,
    TablePartyRead,
    UserAssignmentInfo,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.services.identity import DniLookupError, DniNotFoundError, lookup_dni
from app.services.security import require_admin

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _get_or_404(db: Session, model, pk: int, name: str):
    obj = db.get(model, pk)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{name} no encontrado")
    return obj


# ---------- Procesos ----------
@router.post("/processes", response_model=ProcessRead, status_code=201)
def create_process(payload: ProcessCreate, db: Session = Depends(get_db)):
    obj = ElectoralProcess(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/processes", response_model=list[ProcessRead])
def list_processes(db: Session = Depends(get_db)):
    return db.execute(select(ElectoralProcess).order_by(ElectoralProcess.year.desc())).scalars().all()


@router.patch("/processes/{process_id}", response_model=ProcessRead)
def update_process(process_id: int, payload: ProcessCreate, db: Session = Depends(get_db)):
    obj = _get_or_404(db, ElectoralProcess, process_id, "Proceso")
    for field, value in payload.model_dump().items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/processes/{process_id}", status_code=204)
def delete_process(process_id: int, db: Session = Depends(get_db)):
    obj = _get_or_404(db, ElectoralProcess, process_id, "Proceso")
    db.delete(obj)
    db.commit()


# ---------- Provincias ----------
@router.post("/provinces", response_model=ProvinceRead, status_code=201)
def create_province(payload: ProvinceCreate, db: Session = Depends(get_db)):
    _get_or_404(db, ElectoralProcess, payload.process_id, "Proceso")
    obj = Province(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/provinces", response_model=list[ProvinceRead])
def list_provinces(process_id: int, db: Session = Depends(get_db)):
    return db.execute(
        select(Province).where(Province.process_id == process_id).order_by(Province.name)
    ).scalars().all()


@router.patch("/provinces/{province_id}", response_model=ProvinceRead)
def update_province(province_id: int, payload: ProvinceUpdate, db: Session = Depends(get_db)):
    obj = _get_or_404(db, Province, province_id, "Provincia")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/provinces/{province_id}", status_code=204)
def delete_province(province_id: int, db: Session = Depends(get_db)):
    obj = _get_or_404(db, Province, province_id, "Provincia")
    db.delete(obj)
    db.commit()


# ---------- Distritos ----------
@router.post("/districts", response_model=DistrictRead, status_code=201)
def create_district(payload: DistrictCreate, db: Session = Depends(get_db)):
    _get_or_404(db, Province, payload.province_id, "Provincia")
    obj = District(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/districts", response_model=list[DistrictRead])
def list_districts(process_id: int, province_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(District).where(District.process_id == process_id)
    if province_id:
        stmt = stmt.where(District.province_id == province_id)
    return db.execute(stmt.order_by(District.name)).scalars().all()


@router.patch("/districts/{district_id}", response_model=DistrictRead)
def update_district(district_id: int, payload: DistrictUpdate, db: Session = Depends(get_db)):
    obj = _get_or_404(db, District, district_id, "Distrito")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/districts/{district_id}", status_code=204)
def delete_district(district_id: int, db: Session = Depends(get_db)):
    obj = _get_or_404(db, District, district_id, "Distrito")
    db.delete(obj)
    db.commit()


# ---------- Centros educativos ----------
@router.post("/schools", response_model=SchoolRead, status_code=201)
def create_school(payload: SchoolCreate, db: Session = Depends(get_db)):
    _get_or_404(db, District, payload.district_id, "Distrito")
    obj = School(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/schools", response_model=list[SchoolRead])
def list_schools(process_id: int, district_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(School).where(School.process_id == process_id)
    if district_id:
        stmt = stmt.where(School.district_id == district_id)
    return db.execute(stmt.order_by(School.name)).scalars().all()


@router.patch("/schools/{school_id}", response_model=SchoolRead)
def update_school(school_id: int, payload: SchoolUpdate, db: Session = Depends(get_db)):
    obj = _get_or_404(db, School, school_id, "Centro")
    data = payload.model_dump(exclude_unset=True)
    if data.get("district_id"):
        _get_or_404(db, District, data["district_id"], "Distrito")
    for field, value in data.items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/schools/{school_id}", status_code=204)
def delete_school(school_id: int, db: Session = Depends(get_db)):
    obj = _get_or_404(db, School, school_id, "Centro")
    db.delete(obj)
    db.commit()


# ---------- Mesas ----------
@router.post("/tables", response_model=PollingTableRead, status_code=201)
def create_table(payload: PollingTableCreate, db: Session = Depends(get_db)):
    _get_or_404(db, School, payload.school_id, "Centro")
    obj = PollingTable(**payload.model_dump())
    db.add(obj)
    db.flush()

    # Auto-vincular la nueva mesa con TODOS los partidos del proceso, en todas las categorias
    parties = db.execute(
        select(PoliticalParty).where(PoliticalParty.process_id == payload.process_id)
    ).scalars().all()
    for party in parties:
        for cat in Category:
            db.add(TableParty(table_id=obj.id, category=cat, party_id=party.id))

    db.commit()
    db.refresh(obj)
    return obj


@router.get("/tables", response_model=list[PollingTableRead])
def list_tables(process_id: int, school_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(PollingTable).where(PollingTable.process_id == process_id)
    if school_id:
        stmt = stmt.where(PollingTable.school_id == school_id)
    return db.execute(stmt.order_by(PollingTable.number)).scalars().all()


@router.patch("/tables/{table_id}", response_model=PollingTableRead)
def update_table(table_id: int, payload: PollingTableUpdate, db: Session = Depends(get_db)):
    obj = _get_or_404(db, PollingTable, table_id, "Mesa")
    data = payload.model_dump(exclude_unset=True)
    if data.get("school_id"):
        _get_or_404(db, School, data["school_id"], "Centro")
    for field, value in data.items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/tables/{table_id}", status_code=204)
def delete_table(table_id: int, db: Session = Depends(get_db)):
    obj = _get_or_404(db, PollingTable, table_id, "Mesa")
    db.delete(obj)
    db.commit()


# ---------- Partidos ----------
@router.post("/parties", response_model=PoliticalPartyRead, status_code=201)
def create_party(payload: PoliticalPartyCreate, db: Session = Depends(get_db)):
    _get_or_404(db, ElectoralProcess, payload.process_id, "Proceso")
    obj = PoliticalParty(**payload.model_dump())
    db.add(obj)
    db.flush()

    # Auto-vincular el nuevo partido a TODAS las mesas del proceso, en todas las categorias
    tables = db.execute(
        select(PollingTable).where(PollingTable.process_id == payload.process_id)
    ).scalars().all()
    for table in tables:
        for cat in Category:
            db.add(TableParty(table_id=table.id, category=cat, party_id=obj.id))

    db.commit()
    db.refresh(obj)
    return obj


@router.get("/parties", response_model=list[PoliticalPartyRead])
def list_parties(process_id: int, db: Session = Depends(get_db)):
    return db.execute(
        select(PoliticalParty).where(PoliticalParty.process_id == process_id).order_by(
            PoliticalParty.name
        )
    ).scalars().all()


@router.patch("/parties/{party_id}", response_model=PoliticalPartyRead)
def update_party(party_id: int, payload: PoliticalPartyUpdate, db: Session = Depends(get_db)):
    obj = _get_or_404(db, PoliticalParty, party_id, "Partido")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/parties/{party_id}", status_code=204)
def delete_party(party_id: int, db: Session = Depends(get_db)):
    obj = _get_or_404(db, PoliticalParty, party_id, "Partido")
    db.delete(obj)
    db.commit()


# ---------- Candidatos ----------
@router.post("/candidates", response_model=CandidateRead, status_code=201)
def create_candidate(payload: CandidateCreate, db: Session = Depends(get_db)):
    _get_or_404(db, PoliticalParty, payload.party_id, "Partido")
    obj = Candidate(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/candidates", response_model=list[CandidateRead])
def list_candidates(process_id: int, category: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Candidate).join(PoliticalParty).where(PoliticalParty.process_id == process_id)
    if category:
        stmt = stmt.where(Candidate.category == category)
    return db.execute(stmt).scalars().all()


# ---------- Usuarios ----------
@router.get("/dni/{dni}")
def lookup_dni_endpoint(dni: str):
    """Consulta el nombre completo a partir del DNI (via apisperu)."""
    if not dni.isdigit() or len(dni) != 8:
        raise HTTPException(400, "El DNI debe tener 8 digitos")
    try:
        return lookup_dni(dni)
    except DniNotFoundError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    except DniLookupError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc


def _user_read(db: Session, user: User) -> UserRead:
    assignments: list[UserAssignmentInfo] = []
    rows = db.execute(select(Assignment).where(Assignment.user_id == user.id)).scalars().all()
    for row in rows:
        table = db.get(PollingTable, row.table_id) if row.table_id else None
        school = db.get(School, row.school_id) if row.school_id else None
        assignments.append(
            UserAssignmentInfo(
                id=row.id,
                table_id=row.table_id,
                school_id=row.school_id,
                table_number=table.number if table else None,
                table_code=table.code if table else None,
                school_name=school.name if school else None,
            )
        )
    return UserRead(
        id=user.id,
        dni=user.dni,
        username=user.username,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        is_active=user.is_active,
        assignments=assignments,
    )


def _set_assignment(db: Session, user: User, table_id: int | None, school_id: int | None) -> None:
    """Reemplaza la asignacion del usuario (una mesa o un local)."""
    db.execute(
        Assignment.__table__.delete().where(Assignment.user_id == user.id)
    )
    if table_id:
        _get_or_404(db, PollingTable, table_id, "Mesa")
        db.add(Assignment(user_id=user.id, table_id=table_id))
    elif school_id:
        _get_or_404(db, School, school_id, "Centro")
        db.add(Assignment(user_id=user.id, school_id=school_id))


@router.post("/users", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    if payload.role == Role.ADMIN:
        if not payload.username or not payload.password:
            raise HTTPException(400, "Admin requiere usuario y contrasena")
    else:
        if not payload.dni:
            raise HTTPException(400, "Personero requiere DNI")
        if payload.role == Role.PERSONERO_MESA and not payload.table_id:
            raise HTTPException(400, "Personero de mesa requiere una mesa asignada")
        if payload.role == Role.PERSONERO_LOCAL and not payload.school_id:
            raise HTTPException(400, "Personero de local requiere un centro asignado")

    if payload.dni:
        exists = db.execute(select(User).where(User.dni == payload.dni)).scalar_one_or_none()
        if exists:
            raise HTTPException(409, "Ya existe un usuario con ese DNI")

    obj = User(
        dni=payload.dni,
        username=payload.username,
        password_hash=hash_password(payload.password) if payload.password else None,
        full_name=payload.full_name,
        phone=payload.phone,
        role=payload.role,
    )
    db.add(obj)
    db.flush()
    if payload.role != Role.ADMIN:
        _set_assignment(db, obj, payload.table_id, payload.school_id)
    db.commit()
    db.refresh(obj)
    return _user_read(db, obj)


@router.get("/users", response_model=list[UserRead])
def list_users(role: Role | None = None, db: Session = Depends(get_db)):
    stmt = select(User).order_by(User.full_name)
    if role:
        stmt = stmt.where(User.role == role)
    users = db.execute(stmt).scalars().all()
    return [_user_read(db, u) for u in users]


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    obj = _get_or_404(db, User, user_id, "Usuario")
    data = payload.model_dump(exclude_unset=True)

    if "dni" in data and data["dni"] and data["dni"] != obj.dni:
        exists = db.execute(select(User).where(User.dni == data["dni"])).scalar_one_or_none()
        if exists:
            raise HTTPException(409, "Ya existe un usuario con ese DNI")

    if data.get("password"):
        obj.password_hash = hash_password(data.pop("password"))
    data.pop("password", None)

    if "full_name" in data and data["full_name"]:
        obj.full_name = data["full_name"]
    if "phone" in data:
        obj.phone = data["phone"]
    if "dni" in data:
        obj.dni = data["dni"]
    if "username" in data:
        obj.username = data["username"]
    if "is_active" in data and data["is_active"] is not None:
        obj.is_active = data["is_active"]

    if obj.role != Role.ADMIN:
        if data.get("clear_assignment"):
            _set_assignment(db, obj, None, None)
        elif data.get("table_id") or data.get("school_id"):
            _set_assignment(db, obj, data.get("table_id"), data.get("school_id"))

    db.commit()
    db.refresh(obj)
    return _user_read(db, obj)


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, current: User = Depends(require_admin), db: Session = Depends(get_db)):
    obj = _get_or_404(db, User, user_id, "Usuario")
    if obj.id == current.id:
        raise HTTPException(400, "No puede eliminar su propio usuario")
    db.delete(obj)
    db.commit()


# ---------- Asignaciones ----------
@router.post("/assignments", response_model=AssignmentRead, status_code=201)
def create_assignment(payload: AssignmentCreate, db: Session = Depends(get_db)):
    _get_or_404(db, User, payload.user_id, "Usuario")
    if payload.table_id is None and payload.school_id is None:
        raise HTTPException(400, "Debe asignar una mesa o un centro")
    obj = Assignment(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/assignments", response_model=list[AssignmentRead])
def list_assignments(user_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(Assignment)
    if user_id:
        stmt = stmt.where(Assignment.user_id == user_id)
    return db.execute(stmt).scalars().all()


@router.delete("/assignments/{assignment_id}", status_code=204)
def delete_assignment(assignment_id: int, db: Session = Depends(get_db)):
    obj = _get_or_404(db, Assignment, assignment_id, "Asignacion")
    db.delete(obj)
    db.commit()


# ---------- Partidos por mesa ----------
@router.post("/table-parties", response_model=TablePartyRead, status_code=201)
def create_table_party(payload: TablePartyCreate, db: Session = Depends(get_db)):
    _get_or_404(db, PollingTable, payload.table_id, "Mesa")
    _get_or_404(db, PoliticalParty, payload.party_id, "Partido")
    obj = TableParty(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/table-parties", response_model=list[TablePartyRead])
def list_table_parties(table_id: int, db: Session = Depends(get_db)):
    return db.execute(
        select(TableParty).where(TableParty.table_id == table_id)
    ).scalars().all()


@router.post("/table-parties/sync")
def sync_table_parties(process_id: int, db: Session = Depends(get_db)):
    """Sincroniza los partidos con todas las mesas del proceso.

    Crea los registros TableParty faltantes para que cada mesa tenga
    todos los partidos del proceso vinculados en todas las categorias.
    No borra ni duplica registros existentes.
    """
    _get_or_404(db, ElectoralProcess, process_id, "Proceso")
    tables = db.execute(
        select(PollingTable).where(PollingTable.process_id == process_id)
    ).scalars().all()
    parties = db.execute(
        select(PoliticalParty).where(PoliticalParty.process_id == process_id)
    ).scalars().all()

    # Obtener los vinculos existentes para no duplicar
    existing = set()
    all_tp = db.execute(
        select(TableParty).where(
            TableParty.table_id.in_([t.id for t in tables])
        )
    ).scalars().all() if tables else []
    for tp in all_tp:
        existing.add((tp.table_id, tp.category, tp.party_id))

    created = 0
    for table in tables:
        for party in parties:
            for cat in Category:
                key = (table.id, cat, party.id)
                if key not in existing:
                    db.add(TableParty(table_id=table.id, category=cat, party_id=party.id))
                    created += 1

    db.commit()
    return {
        "message": f"Sincronizacion completada: {created} vinculos creados.",
        "tables": len(tables),
        "parties": len(parties),
        "created": created,
    }
