import httpx
import pytest

from hire_me_bot import settings
from hire_me_bot.notify import discord


def _posting(i: int, score: int | None = 5) -> dict:
    return {
        "id": i,
        "title": f"Software Engineer {i}",
        "company": "Acme",
        "url": f"https://example.com/{i}",
        "location": "Austin, TX",
        "description": "Requirements: Python, SQL.",
        "posted_at": "2026-06-30T00:00:00+00:00",
        "fit_score": score,
    }


def _mock_client(monkeypatch, handler):
    real_client_cls = httpx.Client
    monkeypatch.setattr(
        discord.httpx, "Client", lambda timeout=None: real_client_cls(transport=httpx.MockTransport(handler))
    )


def test_raises_if_webhook_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", None)
    with pytest.raises(RuntimeError):
        discord.send_notifications()


def test_no_postings_sends_nothing(monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x/y")
    monkeypatch.setattr(settings, "SCORING_ENABLED", True)
    monkeypatch.setattr(discord.postings_repo, "get_unnotified_above_threshold", lambda t, a: [])
    assert discord.send_notifications() == 0


def test_scoring_enabled_uses_threshold_query(monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x/y")
    monkeypatch.setattr(settings, "SCORING_ENABLED", True)
    monkeypatch.setattr(discord.time, "sleep", lambda seconds: None)
    postings = [_posting(i) for i in range(12)]  # forces 3 batches at MAX_EMBEDS_PER_MESSAGE=5 (5+5+2)

    calls = []
    monkeypatch.setattr(
        discord.postings_repo,
        "get_unnotified_above_threshold",
        lambda t, a: calls.append((t, a)) or postings,
    )
    monkeypatch.setattr(discord.postings_repo, "get_unnotified", lambda a: (_ for _ in ()).throw(
        AssertionError("should not call get_unnotified when scoring is enabled")
    ))

    marked = []
    monkeypatch.setattr(discord.postings_repo, "mark_notified", lambda pid: marked.append(pid))

    sent_payloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent_payloads.append(request)
        return httpx.Response(200, json={"ok": True})

    _mock_client(monkeypatch, handler)

    count = discord.send_notifications()

    assert count == 12
    assert len(sent_payloads) == 3  # batched into 3 webhook calls
    assert sorted(marked) == list(range(12))
    assert calls == [(settings.FIT_SCORE_NOTIFY_THRESHOLD, settings.NOTIFY_MAX_AGE_DAYS)]


def test_scoring_disabled_notifies_all_unnotified_regardless_of_score(monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x/y")
    monkeypatch.setattr(settings, "SCORING_ENABLED", False)
    postings = [_posting(1, score=None), _posting(2, score=None)]

    monkeypatch.setattr(discord.postings_repo, "get_unnotified", lambda a: postings)
    monkeypatch.setattr(
        discord.postings_repo,
        "get_unnotified_above_threshold",
        lambda t, a: (_ for _ in ()).throw(
            AssertionError("should not call get_unnotified_above_threshold when scoring is disabled")
        ),
    )

    marked = []
    monkeypatch.setattr(discord.postings_repo, "mark_notified", lambda pid: marked.append(pid))

    sent_payloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent_payloads.append(request)
        return httpx.Response(200, json={"ok": True})

    _mock_client(monkeypatch, handler)

    count = discord.send_notifications()

    assert count == 2
    assert sorted(marked) == [1, 2]
    embed = sent_payloads[0].content
    assert b"Unscored" not in embed
    assert b"Fit:" not in embed
    assert b"Austin, TX" in embed
    assert b"Requirements" in embed


def test_embed_includes_role_company_location_and_jd_preview():
    posting = _posting(1, score=None)
    embed = discord._posting_to_embed(posting)

    assert embed["title"] == "Software Engineer 1 @ Acme"
    assert embed["url"] == "https://example.com/1"
    assert "Austin, TX" in embed["description"]
    assert "Requirements: Python, SQL." in embed["description"]
    assert "Fit:" not in embed["description"]
    assert "[Apply here](https://example.com/1)" in embed["description"]


def test_embed_includes_fit_score_when_scored():
    posting = _posting(1, score=4)
    embed = discord._posting_to_embed(posting)
    assert "Fit: 4/5" in embed["description"]


def test_embed_has_no_emojis():
    posting = _posting(1, score=4)
    embed = discord._posting_to_embed(posting)
    full_text = embed["title"] + embed["description"]
    assert all(ord(ch) < 0x2190 for ch in full_text)  # below the emoji/symbol Unicode ranges


def test_posted_days_ago_text():
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    assert discord._posted_days_ago_text(now.isoformat()) == "Posted today"
    assert discord._posted_days_ago_text((now - timedelta(days=1)).isoformat()) == "Posted 1 day ago"
    assert discord._posted_days_ago_text((now - timedelta(days=5)).isoformat()) == "Posted 5 days ago"
    assert discord._posted_days_ago_text(None) == "Posted date unknown"
    assert discord._posted_days_ago_text("not-a-date") == "Posted date unknown"


def test_jd_preview_truncates_long_descriptions():
    long_description = "x" * (discord._JD_PREVIEW_CHARS + 500)
    preview = discord._jd_preview(long_description)
    assert len(preview) == discord._JD_PREVIEW_CHARS + 3  # + "..."
    assert preview.endswith("...")


def test_jd_preview_leaves_short_descriptions_untouched():
    assert discord._jd_preview("Short JD.") == "Short JD."


def test_batched_message_stays_under_discord_combined_embed_limit():
    # Discord caps the COMBINED character count across all embeds in a single
    # message at 6000, separate from each embed's own 4096-char description
    # limit. Worst case: max-length title (256) + a long location/URL, repeated
    # _MAX_EMBEDS_PER_MESSAGE times -- must stay comfortably under 6000, or a
    # future bump to the preview length or batch size could get a real
    # notification message silently rejected by Discord.
    worst_case_posting = {
        "id": 1,
        "title": "x" * 256,
        "company": "y" * 100,
        "url": "https://example.com/" + "z" * 200,
        "location": "Some Very Long Location String, NY",
        "description": "d" * (discord._JD_PREVIEW_CHARS + 500),
        "fit_score": 5,
    }
    embed = discord._posting_to_embed(worst_case_posting)
    per_embed_size = len(embed["title"]) + len(embed["description"])
    total = per_embed_size * discord._MAX_EMBEDS_PER_MESSAGE
    assert total < 6000


def test_rate_limit_retries_instead_of_dropping_the_batch(monkeypatch):
    # A prior real run hit Discord's 429 after ~57 messages and silently
    # dropped ~1900 remaining batches (logged an error and moved on, never
    # retried) -- they never got marked notified, so the next scheduled run
    # would have tried (and likely failed) all of them again.
    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x/y")
    monkeypatch.setattr(settings, "SCORING_ENABLED", False)
    monkeypatch.setattr(discord.time, "sleep", lambda seconds: None)

    postings = [_posting(1)]
    monkeypatch.setattr(discord.postings_repo, "get_unnotified", lambda a: postings)

    marked = []
    monkeypatch.setattr(discord.postings_repo, "mark_notified", lambda pid: marked.append(pid))

    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(429, json={"message": "rate limited", "retry_after": 0.1})
        return httpx.Response(200, json={"ok": True})

    _mock_client(monkeypatch, handler)

    count = discord.send_notifications()

    assert call_count == 2
    assert count == 1
    assert marked == [1]


def test_failed_webhook_call_does_not_mark_notified(monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x/y")
    monkeypatch.setattr(settings, "SCORING_ENABLED", True)
    postings = [_posting(1)]
    monkeypatch.setattr(discord.postings_repo, "get_unnotified_above_threshold", lambda t, a: postings)

    marked = []
    monkeypatch.setattr(discord.postings_repo, "mark_notified", lambda pid: marked.append(pid))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "bad request"})

    _mock_client(monkeypatch, handler)

    count = discord.send_notifications()

    assert count == 0
    assert marked == []
