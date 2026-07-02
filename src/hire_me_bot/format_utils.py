from datetime import datetime, timezone


def posted_days_ago_text(posted_at: str | None) -> str:
    if not posted_at:
        return "Posted date unknown"
    try:
        posted_dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
    except ValueError:
        return "Posted date unknown"
    days = (datetime.now(timezone.utc) - posted_dt).days
    if days <= 0:
        return "Posted today"
    if days == 1:
        return "Posted 1 day ago"
    return f"Posted {days} days ago"
