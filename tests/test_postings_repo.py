from hire_me_bot.connectors.base import Posting
from hire_me_bot.db import postings_repo


class _FakeQuery:
    def __init__(self, log: list, rows: list):
        self._log = log
        self._rows = rows

    def upsert(self, rows, on_conflict, ignore_duplicates):
        self._log.append({"rows": rows, "on_conflict": on_conflict, "ignore_duplicates": ignore_duplicates})
        return self

    def execute(self):
        return None


class _FakeClient:
    def __init__(self):
        self.calls: list = []

    def table(self, name):
        assert name == postings_repo.TABLE
        return _FakeQuery(self.calls, [])


def _posting(i: int) -> Posting:
    return Posting(
        source="greenhouse",
        company=f"Company{i}",
        external_id=str(i),
        title="Software Engineer",
        location=None,
        url=f"https://example.com/{i}",
        description="Requirements: Python.",
        posted_at=None,
    )


def test_empty_list_makes_no_calls(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(postings_repo, "get_client", lambda: fake)
    postings_repo.upsert_postings([])
    assert fake.calls == []


def test_upsert_chunks_large_batches(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(postings_repo, "get_client", lambda: fake)
    postings = [_posting(i) for i in range(1200)]  # 3 chunks at 500

    postings_repo.upsert_postings(postings)

    assert len(fake.calls) == 3
    assert [len(c["rows"]) for c in fake.calls] == [500, 500, 200]
    assert all(c["on_conflict"] == "source,company,external_id" for c in fake.calls)
    assert all(c["ignore_duplicates"] is True for c in fake.calls)


def test_upsert_row_shape(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(postings_repo, "get_client", lambda: fake)
    postings_repo.upsert_postings([_posting(1)])

    row = fake.calls[0]["rows"][0]
    assert row["source"] == "greenhouse"
    assert row["company"] == "Company1"
    assert row["external_id"] == "1"
    assert row["description"] == "Requirements: Python."
    assert row["posted_at"] is None


class _FakeUpdateQuery:
    def __init__(self, log: list):
        self._log = log
        self._row = None

    def update(self, row):
        self._row = row
        return self

    def eq(self, col, val):
        self._log.append({"row": self._row, "col": col, "val": val})
        return self

    def execute(self):
        return None


class _FakeUpdateClient:
    def __init__(self):
        self.calls: list = []

    def table(self, name):
        return _FakeUpdateQuery(self.calls)


def test_update_status_sets_applied_at_when_applied(monkeypatch):
    fake = _FakeUpdateClient()
    monkeypatch.setattr(postings_repo, "get_client", lambda: fake)

    postings_repo.update_status(1, "applied")

    assert fake.calls[0]["col"] == "id"
    assert fake.calls[0]["val"] == 1
    assert fake.calls[0]["row"]["status"] == "applied"
    assert "applied_at" in fake.calls[0]["row"]


def test_update_status_does_not_set_applied_at_for_other_statuses(monkeypatch):
    fake = _FakeUpdateClient()
    monkeypatch.setattr(postings_repo, "get_client", lambda: fake)

    postings_repo.update_status(1, "interviewing")

    assert fake.calls[0]["row"] == {"status": "interviewing"}


class _FakeSelectQuery:
    def __init__(self, rows: list):
        self._rows = rows

    def select(self, *args):
        return self

    @property
    def not_(self):
        return self

    def is_(self, col, val):
        return self

    def execute(self):
        class Resp:
            pass

        resp = Resp()
        resp.data = self._rows
        return resp


class _FakeSelectClient:
    def __init__(self, rows: list):
        self._rows = rows

    def table(self, name):
        return _FakeSelectQuery(self._rows)


def test_get_applications_per_day_groups_by_date(monkeypatch):
    rows = [
        {"applied_at": "2026-06-30T10:00:00+00:00"},
        {"applied_at": "2026-06-30T18:00:00+00:00"},
        {"applied_at": "2026-07-01T09:00:00+00:00"},
    ]
    monkeypatch.setattr(postings_repo, "get_client", lambda: _FakeSelectClient(rows))

    counts = postings_repo.get_applications_per_day()

    assert counts == {"2026-06-30": 2, "2026-07-01": 1}
