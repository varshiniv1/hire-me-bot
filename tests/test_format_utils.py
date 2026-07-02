from datetime import datetime, timedelta, timezone

from hire_me_bot.format_utils import posted_days_ago_text


def test_posted_days_ago_text():
    now = datetime.now(timezone.utc)
    assert posted_days_ago_text(now.isoformat()) == "Posted today"
    assert posted_days_ago_text((now - timedelta(days=1)).isoformat()) == "Posted 1 day ago"
    assert posted_days_ago_text((now - timedelta(days=5)).isoformat()) == "Posted 5 days ago"
    assert posted_days_ago_text(None) == "Posted date unknown"
    assert posted_days_ago_text("not-a-date") == "Posted date unknown"
