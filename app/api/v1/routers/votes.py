import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Category, RecordStatus, Role, VoteType
from app.db.session import get_db
from app.models import (
    PoliticalParty,
    PollingTable,
    TableParty,
    User,
    VoteEntry,
    VoteRecord,
    VoteRecordHistory,
)
from app.schemas import (
    HistoryRead,
    VoteRecordInput,
    VoteRecordRead,
    VoteRecordResponse,
)
from app.services.realtime import manager
from app.services.security import ensure_table_access, get_current_user
from app.services.vote_logic import build_table_result, validate_record

router = APIRouter(tags=["votos"])


def _allowed_parties(db: Session, table_id: int, process_id: int) -> dict[Category, set[int]]:
    """Devuelve los partidos permitidos por categoria para una mesa.

    Si existen registros TableParty explicitos para la mesa, se usan esos.
    Si no hay ninguno, se devuelven TODOS los partidos del proceso para
    todas las categorias (fallback automatico).
    """
    rows = db.execute(select(TableParty).where(TableParty.table_id == table_id)).scalars().all()
    result: dict[Category, set[int]] = {cat: set() for cat in Category}
    if rows:
        for row in rows:
            result[row.category].add(row.party_id)
    else:
        # Fallback: todos los partidos del proceso aplican a todas las categorias
        all_party_ids = set(
            db.execute(
                select(PoliticalParty.id).where(PoliticalParty.process_id == process_id)
            ).scalars().all()
        )
        for cat in Category:
            result[cat] = set(all_party_ids)
    return result


@router.get("/tables")
def list_my_tables(
    school_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mesas accesibles por el usuario (scope asignado)."""
    from app.services.security import assigned_table_ids

    table_ids, school_ids = assigned_table_ids(db, user)
    stmt = select(PollingTable)

    if user.role == Role.ADMIN:
        if school_id:
            stmt = stmt.where(PollingTable.school_id == school_id)
    else:
        conditions = []
        if table_ids:
            conditions.append(PollingTable.id.in_(table_ids))
        if school_ids:
            conditions.append(PollingTable.school_id.in_(school_ids))
        if not conditions:
            return []
        from sqlalchemy import or_

        stmt = stmt.where(or_(*conditions))
        if school_id:
            if school_id not in school_ids:
                return []
            stmt = stmt.where(PollingTable.school_id == school_id)
    return [
        {
            "id": t.id,
            "number": t.number,
            "school_id": t.school_id,
            "electores_habilitados": t.electores_habilitados,
        }
        for t in db.execute(stmt.order_by(PollingTable.number)).scalars().all()
    ]


@router.get("/tables/{table_id}")
def get_table_context(
    table_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    table = ensure_table_access(db, user, table_id)
    allowed = _allowed_parties(db, table.id, table.process_id)
    parties = db.execute(
        select(PoliticalParty).where(
            PoliticalParty.process_id == table.process_id
        ).order_by(PoliticalParty.name)
    ).scalars().all()
    record = db.execute(
        select(VoteRecord).where(VoteRecord.table_id == table.id)
    ).scalar_one_or_none()

    return {
        "table": {
            "id": table.id,
            "number": table.number,
            "code": table.code,
            "electores_habilitados": table.electores_habilitados,
            "school_id": table.school_id,
            "school_name": table.school.name,
            "school_address": table.school.address,
            "district": table.school.district.name,
            "province": table.school.district.province.name,
            "process_id": table.process_id,
        },
        "parties": [
            {"id": p.id, "name": p.name, "code": p.code, "color": p.color} for p in parties
        ],
        "table_parties": {
            cat.value: sorted(party_ids) for cat, party_ids in allowed.items()
        },
        "record": VoteRecordRead.model_validate(record) if record else None,
    }


def _validate_input(
    db: Session, table: PollingTable, payload: VoteRecordInput
) -> tuple[int, int, list[VoteEntry]]:
    allowed = _allowed_parties(db, table.id, table.process_id)
    electores = (
        payload.electores_habilitados
        if payload.electores_habilitados is not None
        else table.electores_habilitados
    )
    total_asistentes = payload.total_asistentes

    entries: list[VoteEntry] = []
    totals: dict[Category, int] = {cat: 0 for cat in Category}
    seen: set[tuple] = set()

    for item in payload.entries:
        key = (item.category, item.vote_type, item.party_id)
        if key in seen:
            raise HTTPException(400, f"Entrada duplicada: {key}")
        seen.add(key)

        if item.vote_type == VoteType.VALIDO:
            if item.party_id is None:
                raise HTTPException(400, "Voto valido requiere party_id")
            party_ids = allowed.get(item.category)
            if party_ids and item.party_id not in party_ids:
                raise HTTPException(
                    400,
                    f"Partido {item.party_id} no aplica a la categoria {item.category.value}",
                )
        else:
            if item.party_id is not None:
                raise HTTPException(400, "Nulos y blancos no llevan party_id")

        totals[item.category] += item.quantity
        entries.append(
            VoteEntry(
                category=item.category,
                vote_type=item.vote_type,
                party_id=item.party_id,
                quantity=item.quantity,
            )
        )

    if total_asistentes is None:
        totals_set = {t for t in totals.values()}
        if len(totals_set) != 1:
            raise HTTPException(
                400,
                "total_asistentes es obligatorio cuando las categorias no coinciden",
            )
        total_asistentes = totals_set.pop()

    mismatches = [
        f"{cat.value}: {total} != {total_asistentes}"
        for cat, total in totals.items()
        if total != total_asistentes
    ]
    if mismatches:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {
                "message": "Los votos no cuadran con el total de asistentes",
                "detalle": mismatches,
            },
        )
    return electores, total_asistentes, entries


def _notify(record: VoteRecord, db: Session) -> None:
    result = build_table_result(record)
    payload = {
        "event": "record.updated",
        "process_id": record.process_id,
        "table_id": record.table_id,
        "result": json.loads(result.model_dump_json()),
    }
    manager.broadcast_threadsafe(payload)


@router.post("/tables/{table_id}/votes", response_model=VoteRecordResponse, status_code=201)
def create_or_replace_votes(
    table_id: int,
    payload: VoteRecordInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    table = ensure_table_access(db, user, table_id)
    electores, total_asistentes, entries = _validate_input(db, table, payload)

    record = db.execute(
        select(VoteRecord).where(VoteRecord.table_id == table.id)
    ).scalar_one_or_none()
    if record:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ya existe un registro para esta mesa; use PUT para editar",
        )

    record = VoteRecord(
        table_id=table.id,
        process_id=table.process_id,
        electores_habilitados=electores,
        total_asistentes=total_asistentes,
        comment=payload.comment,
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    if user.role == Role.ADMIN:
        record.status = RecordStatus.CONFIRMADO
    db.add(record)
    db.flush()
    for entry in entries:
        entry.record_id = record.id
        db.add(entry)
    db.commit()
    db.refresh(record)

    _notify(record, db)
    return VoteRecordResponse(record=record, validation=validate_record(record))


@router.put("/votes/{record_id}", response_model=VoteRecordResponse)
def update_votes(
    record_id: int,
    payload: VoteRecordInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = db.get(VoteRecord, record_id)
    if not record:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro no encontrado")
    table = ensure_table_access(db, user, record.table_id)
    electores, total_asistentes, entries = _validate_input(db, table, payload)

    snapshot = [
        {
            "category": e.category.value,
            "vote_type": e.vote_type.value,
            "party_id": e.party_id,
            "quantity": e.quantity,
        }
        for e in record.entries
    ]
    db.add(
        VoteRecordHistory(
            record_id=record.id,
            changed_by_id=user.id,
            snapshot=json.dumps(snapshot),
            reason=payload.comment,
        )
    )

    for entry in list(record.entries):
        db.delete(entry)
    db.flush()

    record.electores_habilitados = electores
    record.total_asistentes = total_asistentes
    record.comment = payload.comment
    record.updated_by_id = user.id
    for entry in entries:
        entry.record_id = record.id
        db.add(entry)
    db.commit()
    db.refresh(record)

    _notify(record, db)
    return VoteRecordResponse(record=record, validation=validate_record(record))


@router.post("/votes/{record_id}/confirm", response_model=VoteRecordResponse)
def confirm_votes(
    record_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    record = db.get(VoteRecord, record_id)
    if not record:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro no encontrado")
    ensure_table_access(db, user, record.table_id)
    validation = validate_record(record)
    if not all(v.ok for v in validation):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El acta no cuadra")
    record.status = RecordStatus.CONFIRMADO
    record.updated_by_id = user.id
    db.commit()
    db.refresh(record)
    _notify(record, db)
    return VoteRecordResponse(record=record, validation=validation)


@router.get("/votes/{record_id}/history", response_model=list[HistoryRead])
def get_history(
    record_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    record = db.get(VoteRecord, record_id)
    if not record:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro no encontrado")
    ensure_table_access(db, user, record.table_id)
    return db.execute(
        select(VoteRecordHistory)
        .where(VoteRecordHistory.record_id == record_id)
        .order_by(VoteRecordHistory.created_at.desc())
    ).scalars().all()
