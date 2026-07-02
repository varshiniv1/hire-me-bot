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
        "location": "Remote",
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
    assert b"Unscored" in embed


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
