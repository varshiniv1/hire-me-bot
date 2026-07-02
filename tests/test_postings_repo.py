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
    def __init__(self, rows: list, log: list | None = None):
        self._rows = rows
        self._start = 0
        self._end = None
        self._log = log

    def select(self, *args):
        return self

    @property
    def not_(self):
        return self

    def is_(self, col, val):
        return self

    def gte(self, col, val):
        if self._log is not None:
            self._log.append((col, val))
        return self

    def eq(self, col, val):
        return self

    def order(self, col, desc=False):
        return self

    def range(self, start, end):
        self._start = start
        self._end = end
        return self

    def execute(self):
        class Resp:
            pass

        resp = Resp()
        resp.data = self._rows[self._start : self._end + 1]
        return resp


class _FakeSelectClient:
    def __init__(self, rows: list, log: list | None = None):
        self._rows = rows
        self._log = log

    def table(self, name):
        return _FakeSelectQuery(self._rows, self._log)


def test_get_applications_per_day_groups_by_date(monkeypatch):
    rows = [
        {"applied_at": "2026-06-30T10:00:00+00:00"},
        {"applied_at": "2026-06-30T18:00:00+00:00"},
        {"applied_at": "2026-07-01T09:00:00+00:00"},
    ]
    monkeypatch.setattr(postings_repo, "get_client", lambda: _FakeSelectClient(rows))

    counts = postings_repo.get_applications_per_day()

    assert counts == {"2026-06-30": 2, "2026-07-01": 1}


def test_get_unnotified_filters_by_max_age(monkeypatch):
    from datetime import datetime, timedelta, timezone

    log: list = []
    monkeypatch.setattr(postings_repo, "get_client", lambda: _FakeSelectClient([], log))

    before = datetime.now(timezone.utc)
    postings_repo.get_unnotified(max_age_days=2)
    after = datetime.now(timezone.utc)

    assert len(log) == 1
    col, cutoff_str = log[0]
    assert col == "posted_at"
    cutoff = datetime.fromisoformat(cutoff_str)
    assert before - timedelta(days=2) <= cutoff <= after - timedelta(days=2)


def test_get_unnotified_above_threshold_filters_by_max_age(monkeypatch):
    from datetime import datetime, timedelta, timezone

    log: list = []
    monkeypatch.setattr(postings_repo, "get_client", lambda: _FakeSelectClient([], log))

    postings_repo.get_unnotified_above_threshold(threshold=4, max_age_days=2)

    posted_at_calls = [entry for entry in log if entry[0] == "posted_at"]
    assert len(posted_at_calls) == 1
    cutoff = datetime.fromisoformat(posted_at_calls[0][1])
    assert cutoff < datetime.now(timezone.utc) - timedelta(days=1, hours=23)


def test_get_recent_not_applied_filters_by_age(monkeypatch):
    from datetime import datetime, timedelta, timezone

    log: list = []
    monkeypatch.setattr(postings_repo, "get_client", lambda: _FakeSelectClient([], log))

    postings_repo.get_recent_not_applied(max_age_days=2)

    posted_at_calls = [entry for entry in log if entry[0] == "posted_at"]
    assert len(posted_at_calls) == 1
    cutoff = datetime.fromisoformat(posted_at_calls[0][1])
    assert cutoff < datetime.now(timezone.utc) - timedelta(days=1, hours=23)


def test_get_recent_not_applied_returns_rows(monkeypatch):
    rows = [{"id": 1, "status": "not_applied"}]
    monkeypatch.setattr(postings_repo, "get_client", lambda: _FakeSelectClient(rows))
    assert postings_repo.get_recent_not_applied(max_age_days=2) == rows


def test_paginate_fetches_every_page_past_supabase_default_cap(monkeypatch):
    # Supabase/PostgREST silently caps an unranged select at 1000 rows --
    # regression guard that _paginate actually pages through everything
    # rather than trusting a single .execute() call.
    monkeypatch.setattr(postings_repo, "_PAGE_SIZE", 1000)
    rows = [{"applied_at": f"2026-01-01T00:00:0{i % 10}+00:00"} for i in range(2500)]
    monkeypatch.setattr(postings_repo, "get_client", lambda: _FakeSelectClient(rows))

    counts = postings_repo.get_applications_per_day()

    assert sum(counts.values()) == 2500
