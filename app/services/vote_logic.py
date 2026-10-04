from app.db.base import ACTIVE_CATEGORIES, Category, VoteType
from app.models import VoteRecord
from app.schemas import (
    CategoryResult,
    PartyResult,
    TableResult,
    ValidationResult,
)


def categorize_entries(record: VoteRecord) -> dict[Category, dict]:
    data: dict[Category, dict] = {
        cat: {"validos": 0, "nulos": 0, "blancos": 0, "parties": {}}
        for cat in ACTIVE_CATEGORIES
    }
    for entry in record.entries:
        if entry.category not in data:
            continue
        bucket = data[entry.category]
        if entry.vote_type == VoteType.VALIDO:
            bucket["validos"] += entry.quantity
            if entry.party_id is not None:
                bucket["parties"][entry.party_id] = (
                    bucket["parties"].get(entry.party_id, 0) + entry.quantity
                )
        elif entry.vote_type == VoteType.NULO:
            bucket["nulos"] += entry.quantity
        elif entry.vote_type == VoteType.BLANCO:
            bucket["blancos"] += entry.quantity
    return data


def validate_record(record: VoteRecord) -> list[ValidationResult]:
    """Valida que cada categoria cuadre con el total de asistentes."""
    data = categorize_entries(record)
    results: list[ValidationResult] = []
    for category, bucket in data.items():
        total_cat = bucket["validos"] + bucket["nulos"] + bucket["blancos"]
        results.append(
            ValidationResult(
                category=category,
                validos=bucket["validos"],
                nulos=bucket["nulos"],
                blancos=bucket["blancos"],
                total_categoria=total_cat,
                total_asistentes=record.total_asistentes,
                ok=total_cat == record.total_asistentes,
            )
        )
    return results


def is_balanced(record: VoteRecord) -> bool:
    return all(item.ok for item in validate_record(record))


def build_table_result(record: VoteRecord) -> TableResult:
    data = categorize_entries(record)
    categories: list[CategoryResult] = []
    for category in ACTIVE_CATEGORIES:
        bucket = data[category]
        total = bucket["validos"] + bucket["nulos"] + bucket["blancos"]
        parties: list[PartyResult] = []
        for party_id, votes in sorted(bucket["parties"].items(), key=lambda kv: -kv[1]):
            entry = next(
                (e for e in record.entries if e.party_id == party_id and e.category == category),
                None,
            )
            parties.append(
                PartyResult(
                    party_id=party_id,
                    party_name=entry.party.name if entry and entry.party else str(party_id),
                    color=entry.party.color if entry and entry.party else None,
                    votes=votes,
                    percentage=round(votes * 100 / bucket["validos"], 2)
                    if bucket["validos"]
                    else 0.0,
                )
            )
        categories.append(
            CategoryResult(
                category=category,
                validos=bucket["validos"],
                nulos=bucket["nulos"],
                blancos=bucket["blancos"],
                total=total,
                parties=parties,
            )
        )

    habilitados = record.electores_habilitados
    ausentismo = max(habilitados - record.total_asistentes, 0)
    participation = round(record.total_asistentes * 100 / habilitados, 2) if habilitados else 0.0

    return TableResult(
        table_id=record.table_id,
        table_number=record.table.number,
        school_name=record.table.school.name,
        electores_habilitados=habilitados,
        total_asistentes=record.total_asistentes,
        ausentismo=ausentismo,
        participation=participation,
        status=record.status,
        comment=record.comment,
        categories=categories,
    )
