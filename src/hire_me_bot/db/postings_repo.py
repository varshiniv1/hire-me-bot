from datetime import datetime, timezone

from hire_me_bot.connectors.base import Posting
from hire_me_bot.db.client import get_client

TABLE = "postings"


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
    resp = client.table(TABLE).select("*").is_("fit_score", "null").execute()
    return resp.data


def update_score(posting_id: int, score: int) -> None:
    client = get_client()
    client.table(TABLE).update(
        {"fit_score": score, "scored_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", posting_id).execute()


def get_unnotified_above_threshold(threshold: int) -> list[dict]:
    client = get_client()
    resp = (
        client.table(TABLE)
        .select("*")
        .gte("fit_score", threshold)
        .is_("notified_at", "null")
        .execute()
    )
    return resp.data


def get_unnotified() -> list[dict]:
    """All not-yet-notified postings regardless of fit_score -- used while
    settings.SCORING_ENABLED is False, since fit_score never gets set."""
    client = get_client()
    resp = client.table(TABLE).select("*").is_("notified_at", "null").execute()
    return resp.data


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
    resp = (
        client.table(TABLE)
        .select("*")
        .ilike("company", f"%{fuzzy_name}%")
        .execute()
    )
    return resp.data


def get_not_applied() -> list[dict]:
    client = get_client()
    resp = client.table(TABLE).select("*").eq("status", "not_applied").execute()
    return resp.data


def update_status(posting_id: int, status: str) -> None:
    client = get_client()
    client.table(TABLE).update({"status": status}).eq("id", posting_id).execute()


def get_all_ordered() -> list[dict]:
    client = get_client()
    resp = client.table(TABLE).select("*").order("first_seen_at", desc=True).execute()
    return resp.data
