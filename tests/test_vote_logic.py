from types import SimpleNamespace

from app.db.base import ACTIVE_CATEGORIES, Category, VoteType
from app.services.vote_logic import is_balanced, validate_record


class FakeEntry:
    def __init__(self, category, vote_type, party_id, quantity):
        self.category = category
        self.vote_type = vote_type
        self.party_id = party_id
        self.quantity = quantity
        self.party = None


class FakeRecord:
    def __init__(self, entries, total_asistentes=170):
        self.entries = entries
        self.total_asistentes = total_asistentes
        self.electores_habilitados = 200
        self.table_id = 1
        self.status = None
        self.comment = None
        self.table = SimpleNamespace(
            number=1, school=SimpleNamespace(name="Colegio")
        )


def build_balanced_entries():
    entries = []
    for cat in ACTIVE_CATEGORIES:
        entries.append(FakeEntry(cat, VoteType.VALIDO, 1, 30))
        entries.append(FakeEntry(cat, VoteType.VALIDO, 2, 18))
        entries.append(FakeEntry(cat, VoteType.VALIDO, 3, 100))
        entries.append(FakeEntry(cat, VoteType.NULO, None, 10))
        entries.append(FakeEntry(cat, VoteType.BLANCO, None, 12))
    return entries


def test_balanced_record():
    record = FakeRecord(build_balanced_entries(), total_asistentes=170)
    assert is_balanced(record) is True
    results = validate_record(record)
    assert len(results) == len(ACTIVE_CATEGORIES)
    assert all(r.total_categoria == 170 for r in results)


def test_unbalanced_record():
    entries = build_balanced_entries()
    entries[0].quantity = 25
    record = FakeRecord(entries, total_asistentes=170)
    assert is_balanced(record) is False
