from datetime import datetime, timedelta, timezone

from hire_me_bot.format_utils import compact_age_text, posted_days_ago_text


def test_posted_days_ago_text():
    now = datetime.now(timezone.utc)
    assert posted_days_ago_text(now.isoformat()) == "Posted today"
    assert posted_days_ago_text((now - timedelta(days=1)).isoformat()) == "Posted 1 day ago"
    assert posted_days_ago_text((now - timedelta(days=5)).isoformat()) == "Posted 5 days ago"
    assert posted_days_ago_text(None) == "Posted date unknown"
    assert posted_days_ago_text("not-a-date") == "Posted date unknown"


def test_compact_age_text():
    now = datetime.now(timezone.utc)
    assert compact_age_text(now.isoformat()) == "0d"
    assert compact_age_text((now - timedelta(days=1)).isoformat()) == "1d"
    assert compact_age_text((now - timedelta(days=13)).isoformat()) == "13d"
    assert compact_age_text((now - timedelta(days=29)).isoformat()) == "29d"
    assert compact_age_text((now - timedelta(days=30)).isoformat()) == "1mo"
    assert compact_age_text((now - timedelta(days=90)).isoformat()) == "3mo"
    assert compact_age_text((now - timedelta(days=400)).isoformat()) == "1y"
    assert compact_age_text(None) == "?"
    assert compact_age_text("not-a-date") == "?"
