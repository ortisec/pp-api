from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.base import Category, RecordStatus, VoteType
from app.db.session import get_db
from app.models import District, PollingTable, Province, School, VoteEntry, VoteRecord
from app.schemas import (
    AnalyticsResponse,
    CategoryRanking,
    DistrictParticipation,
    RankingEntry,
    SchoolRankingEntry,
    SummaryResponse,
    TableResult,
)
from app.services.security import get_current_user
from app.services.vote_logic import build_table_result

router = APIRouter(prefix="/results", tags=["resultados"])


def _records_query(
    process_id: int,
    province_id: int | None,
    district_id: int | None,
    school_id: int | None,
    status: RecordStatus | None = None,
):
    stmt = (
        select(VoteRecord)
        .join(PollingTable, VoteRecord.table_id == PollingTable.id)
        .join(School, PollingTable.school_id == School.id)
        .where(VoteRecord.process_id == process_id)
        .options(
            selectinload(VoteRecord.entries).selectinload(VoteEntry.party),
            selectinload(VoteRecord.table).selectinload(PollingTable.school).selectinload(School.district),
        )
    )
    if province_id:
        stmt = stmt.join(District, School.district_id == District.id).where(
            District.province_id == province_id
        )
    if district_id:
        stmt = stmt.where(School.district_id == district_id)
    if school_id:
        stmt = stmt.where(PollingTable.school_id == school_id)
    if status:
        stmt = stmt.where(VoteRecord.status == status)
    return stmt


@router.get("/summary", response_model=SummaryResponse)
def summary(
    process_id: int,
    province_id: int | None = None,
    district_id: int | None = None,
    school_id: int | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    table_stmt = (
        select(PollingTable)
        .join(School, PollingTable.school_id == School.id)
        .where(PollingTable.process_id == process_id)
    )
    if province_id:
        table_stmt = table_stmt.join(District, School.district_id == District.id).where(
            District.province_id == province_id
        )
    if district_id:
        table_stmt = table_stmt.where(School.district_id == district_id)
    if school_id:
        table_stmt = table_stmt.where(PollingTable.school_id == school_id)
    tables = db.execute(table_stmt).scalars().all()
    total_tables = len(tables)
    total_electores = sum(t.electores_habilitados for t in tables)

    records = db.execute(
        _records_query(process_id, province_id, district_id, school_id)
    ).scalars().all()
    total_asistentes = sum(r.total_asistentes for r in records)
    ausentismo = max(total_electores - total_asistentes, 0)
    participation = round(total_asistentes * 100 / total_electores, 2) if total_electores else 0.0

    return SummaryResponse(
        total_tables=total_tables,
        tables_reportadas=len(records),
        tables_pendientes=total_tables - len(records),
        total_electores=total_electores,
        total_asistentes=total_asistentes,
        ausentismo=ausentismo,
        participation=participation,
        comment_count=sum(1 for r in records if r.comment),
    )


@router.get("/tables", response_model=list[TableResult])
def table_results(
    process_id: int,
    province_id: int | None = None,
    district_id: int | None = None,
    school_id: int | None = None,
    status: RecordStatus | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    records = db.execute(
        _records_query(process_id, province_id, district_id, school_id, status)
    ).scalars().all()
    return [build_table_result(r) for r in records]


@router.get("/analytics", response_model=AnalyticsResponse)
def analytics(
    process_id: int,
    province_id: int | None = None,
    district_id: int | None = None,
    school_id: int | None = None,
    status: RecordStatus | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    records = db.execute(
        _records_query(process_id, province_id, district_id, school_id, status)
    ).scalars().all()

    # Ranking por categoria
    rankings: list[CategoryRanking] = []
    for category in Category:
        votes: dict[int, int] = {}
        names: dict[int, tuple[str, str | None]] = {}
        for record in records:
            for entry in record.entries:
                if entry.category != category or entry.vote_type != VoteType.VALIDO:
                    continue
                if entry.party_id is None:
                    continue
                votes[entry.party_id] = votes.get(entry.party_id, 0) + entry.quantity
                if entry.party:
                    names[entry.party_id] = (entry.party.name, entry.party.color)
        total_validos = sum(votes.values())
        ordered = sorted(votes.items(), key=lambda kv: -kv[1])
        ranking = [
            RankingEntry(
                party_id=pid,
                party_name=names.get(pid, (str(pid), None))[0],
                color=names.get(pid, (str(pid), None))[1],
                votes=qty,
                percentage=round(qty * 100 / total_validos, 2) if total_validos else 0.0,
                position=idx + 1,
            )
            for idx, (pid, qty) in enumerate(ordered)
        ]
        rankings.append(
            CategoryRanking(category=category, total_validos=total_validos, ranking=ranking)
        )

    # Ranking de colegios por votos validos totales y participacion
    school_agg: dict[int, dict] = {}
    for record in records:
        table = record.table
        school = table.school
        row = school_agg.setdefault(
            school.id,
            {
                "school_name": school.name,
                "district_name": school.district.name,
                "electores": 0,
                "asistentes": 0,
                "validos": 0,
                "nulos": 0,
                "blancos": 0,
            },
        )
        row["electores"] += record.electores_habilitados
        row["asistentes"] += record.total_asistentes
        for entry in record.entries:
            if entry.vote_type == VoteType.VALIDO:
                row["validos"] += entry.quantity
            elif entry.vote_type == VoteType.NULO:
                row["nulos"] += entry.quantity
            elif entry.vote_type == VoteType.BLANCO:
                row["blancos"] += entry.quantity

    school_ranking = [
        SchoolRankingEntry(
            school_id=sid,
            school_name=row["school_name"],
            district_name=row["district_name"],
            total_asistentes=row["asistentes"],
            validos=row["validos"],
            nulos=row["nulos"],
            blancos=row["blancos"],
            participation=round(row["asistentes"] * 100 / row["electores"], 2)
            if row["electores"]
            else 0.0,
        )
        for sid, row in school_agg.items()
    ]
    school_ranking.sort(key=lambda s: -s.validos)

    # Participacion por distrito (considerando todas las mesas, no solo reportadas)
    district_stmt = (
        select(District, Province.name)
        .join(Province, District.province_id == Province.id)
        .where(District.process_id == process_id)
    )
    if province_id:
        district_stmt = district_stmt.where(District.province_id == province_id)
    if district_id:
        district_stmt = district_stmt.where(District.id == district_id)
    district_rows = db.execute(district_stmt).all()

    district_participation: list[DistrictParticipation] = []
    for district_obj, province_name in district_rows:
        tables = db.execute(
            select(PollingTable).where(PollingTable.school_id.in_(
                select(School.id).where(School.district_id == district_obj.id)
            ))
        ).scalars().all()
        electores = sum(t.electores_habilitados for t in tables)
        table_ids = {t.id for t in tables}
        asistentes = sum(
            r.total_asistentes for r in records if r.table_id in table_ids
        )
        district_participation.append(
            DistrictParticipation(
                district_id=district_obj.id,
                district_name=district_obj.name,
                province_name=province_name,
                electores=electores,
                asistentes=asistentes,
                participation=round(asistentes * 100 / electores, 2) if electores else 0.0,
            )
        )
    district_participation.sort(key=lambda d: -d.participation)

    return AnalyticsResponse(
        process_id=process_id,
        rankings=rankings,
        school_ranking=school_ranking,
        district_participation=district_participation,
    )


@router.get("/filters")
def filters(
    process_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Catalogos para poblar los filtros del dashboard."""
    provinces = db.execute(
        select(Province).where(Province.process_id == process_id).order_by(Province.name)
    ).scalars().all()
    districts = db.execute(
        select(District).where(District.process_id == process_id).order_by(District.name)
    ).scalars().all()
    schools = db.execute(
        select(School).where(School.process_id == process_id).order_by(School.name)
    ).scalars().all()
    return {
        "provinces": [
            {"id": p.id, "name": p.name, "ubigeo": p.ubigeo} for p in provinces
        ],
        "districts": [
            {
                "id": d.id,
                "name": d.name,
                "ubigeo": d.ubigeo,
                "province_id": d.province_id,
            }
            for d in districts
        ],
        "schools": [
            {"id": s.id, "name": s.name, "district_id": s.district_id, "local_id": s.local_id}
            for s in schools
        ],
    }

