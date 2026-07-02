from datetime import datetime, timedelta, timezone

from hire_me_bot.connectors.base import Posting
from hire_me_bot.db.client import get_client

TABLE = "postings"

# PostgREST (Supabase's REST layer) caps an unranged select at 1000 rows by
# default -- a query that matches more than that silently returns only the
# first page instead of erroring, which is easy to miss until row counts
# grow. Every "give me all matching rows" query below pages through
# .range() explicitly instead of trusting a single .execute() to return
# everything.
_PAGE_SIZE = 1000


def _paginate(build_query) -> list[dict]:
    """build_query() must return a fresh (already-filtered, not yet ranged)
    Supabase query builder on each call, since .range() has to be applied
    per page."""
    all_rows: list[dict] = []
    offset = 0
    while True:
        resp = build_query().range(offset, offset + _PAGE_SIZE - 1).execute()
        if not resp.data:
            break
        all_rows.extend(resp.data)
        if len(resp.data) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE
    return all_rows


def _posting_to_row(posting: Posting) -> dict:
    return {
        "source": posting.source,
        "company": posting.company,
        "external_id": posting.external_id,
        "title": posting.title,
        "location": posting.location,
        "url": posting.url,
        "description": posting.description,
        "posted_at": posting.posted_at.isoformat() if posting.posted_at else None,
    }


_UPSERT_CHUNK_SIZE = 500


def upsert_postings(postings: list[Posting]) -> None:
    """Insert new postings, leave existing ones untouched (dedup by source+company+external_id).

    Uses ignore_duplicates so a posting seen again on a later run never overwrites
    first_seen_at, status, fit_score, etc. Doesn't return the upserted rows -- callers
    that need to know what's new should query get_unscored() afterward, which is a
    single query regardless of how many postings were just upserted (an earlier version
    of this function re-queried once per posting, which meant one extra round trip to
    Supabase per posting on every run -- with thousands of companies that added up fast
    for no benefit, since nothing actually used the per-row return value).
    """
    if not postings:
        return
    rows = [_posting_to_row(p) for p in postings]
    client = get_client()
    for i in range(0, len(rows), _UPSERT_CHUNK_SIZE):
        chunk = rows[i : i + _UPSERT_CHUNK_SIZE]
        client.table(TABLE).upsert(
            chunk, on_conflict="source,company,external_id", ignore_duplicates=True
        ).execute()


def get_unscored() -> list[dict]:
    client = get_client()
    return _paginate(lambda: client.table(TABLE).select("*").is_("fit_score", "null"))


def update_score(posting_id: int, score: int) -> None:
    client = get_client()
    client.table(TABLE).update(
        {"fit_score": score, "scored_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", posting_id).execute()


def get_unnotified_above_threshold(threshold: int, max_age_days: int) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
    client = get_client()
    return _paginate(
        lambda: client.table(TABLE)
        .select("*")
        .gte("fit_score", threshold)
        .is_("notified_at", "null")
        .gte("posted_at", cutoff)
    )


def get_unnotified(max_age_days: int) -> list[dict]:
    """All not-yet-notified postings regardless of fit_score -- used while
    settings.SCORING_ENABLED is False, since fit_score never gets set.

    Postings older than max_age_days (by posted_at) are excluded, as are
    postings with no posted_at at all (can't confirm they're recent) --
    they still exist in the table (never deleted), just never notified.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
    client = get_client()
    return _paginate(
        lambda: client.table(TABLE).select("*").is_("notified_at", "null").gte("posted_at", cutoff)
    )


def mark_notified(posting_id: int) -> None:
    client = get_client()
    client.table(TABLE).update(
        {"notified_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", posting_id).execute()


def search_by_company(fuzzy_name: str) -> list[dict]:
    """Case-insensitive substring match on company, across ALL postings regardless
    of status, so track.py can move applied -> interviewing etc, not just log new
    applications."""
    client = get_client()
    return _paginate(lambda: client.table(TABLE).select("*").ilike("company", f"%{fuzzy_name}%"))


def get_not_applied() -> list[dict]:
    client = get_client()
    return _paginate(lambda: client.table(TABLE).select("*").eq("status", "not_applied"))


def update_status(posting_id: int, status: str) -> None:
    row = {"status": status}
    if status == "applied":
        # Drives the applications-per-day calendar -- set every time status
        # becomes "applied" (not just the first time), since re-applying
        # after a rejection is a real scenario worth counting again.
        row["applied_at"] = datetime.now(timezone.utc).isoformat()
    client = get_client()
    client.table(TABLE).update(row).eq("id", posting_id).execute()


def get_applications_per_day() -> dict[str, int]:
    """Maps "YYYY-MM-DD" -> count of postings marked applied that day, for
    the stats calendar."""
    client = get_client()
    rows = _paginate(lambda: client.table(TABLE).select("applied_at").not_.is_("applied_at", "null"))
    counts: dict[str, int] = {}
    for row in rows:
        day = row["applied_at"][:10]
        counts[day] = counts.get(day, 0) + 1
    return counts


def get_all_ordered() -> list[dict]:
    client = get_client()
    return _paginate(lambda: client.table(TABLE).select("*").order("first_seen_at", desc=True))
