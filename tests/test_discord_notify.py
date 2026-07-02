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
    monkeypatch.setattr(discord.postings_repo, "get_unnotified_above_threshold", lambda t: [])
    assert discord.send_notifications() == 0


def test_scoring_enabled_uses_threshold_query(monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x/y")
    monkeypatch.setattr(settings, "SCORING_ENABLED", True)
    postings = [_posting(i) for i in range(12)]  # forces 2 batches (10 + 2)

    calls = []
    monkeypatch.setattr(
        discord.postings_repo,
        "get_unnotified_above_threshold",
        lambda t: calls.append(t) or postings,
    )
    monkeypatch.setattr(discord.postings_repo, "get_unnotified", lambda: (_ for _ in ()).throw(
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
    assert len(sent_payloads) == 2  # batched into 2 webhook calls
    assert sorted(marked) == list(range(12))
    assert calls == [settings.FIT_SCORE_NOTIFY_THRESHOLD]


def test_scoring_disabled_notifies_all_unnotified_regardless_of_score(monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x/y")
    monkeypatch.setattr(settings, "SCORING_ENABLED", False)
    postings = [_posting(1, score=None), _posting(2, score=None)]

    monkeypatch.setattr(discord.postings_repo, "get_unnotified", lambda: postings)
    monkeypatch.setattr(
        discord.postings_repo,
        "get_unnotified_above_threshold",
        lambda t: (_ for _ in ()).throw(
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


def test_embed_includes_fit_score_when_scored():
    posting = _posting(1, score=4)
    embed = discord._posting_to_embed(posting)
    assert "⭐ Fit: 4/5" in embed["description"]


def test_jd_preview_truncates_long_descriptions():
    long_description = "x" * 1000
    preview = discord._jd_preview(long_description)
    assert len(preview) == discord._JD_PREVIEW_CHARS + 3  # + "..."
    assert preview.endswith("...")


def test_jd_preview_leaves_short_descriptions_untouched():
    assert discord._jd_preview("Short JD.") == "Short JD."


def test_failed_webhook_call_does_not_mark_notified(monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x/y")
    monkeypatch.setattr(settings, "SCORING_ENABLED", True)
    postings = [_posting(1)]
    monkeypatch.setattr(discord.postings_repo, "get_unnotified_above_threshold", lambda t: postings)

    marked = []
    monkeypatch.setattr(discord.postings_repo, "mark_notified", lambda pid: marked.append(pid))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "bad request"})

    _mock_client(monkeypatch, handler)

    count = discord.send_notifications()

    assert count == 0
    assert marked == []
