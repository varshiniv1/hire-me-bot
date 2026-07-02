from datetime import datetime, timezone


def _days_since(posted_at: str | None) -> int | None:
    if not posted_at:
        return None
    try:
        posted_dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - posted_dt).days


def posted_days_ago_text(posted_at: str | None) -> str:
    days = _days_since(posted_at)
    if days is None:
        return "Posted date unknown"
    if days <= 0:
        return "Posted today"
    if days == 1:
        return "Posted 1 day ago"
    return f"Posted {days} days ago"


def compact_age_text(posted_at: str | None) -> str:
    """SimplifyJobs-style compact age: "0d", "13d", "1mo", "3mo", "1y"."""
    days = _days_since(posted_at)
    if days is None:
        return "?"
    days = max(days, 0)
    if days < 30:
        return f"{days}d"
    if days < 365:
        return f"{days // 30}mo"
    return f"{days // 365}y"
