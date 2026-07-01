import httpx
import pytest

from hire_me_bot import settings
from hire_me_bot.notify import discord


def _posting(i: int, score: int = 5) -> dict:
    return {
        "id": i,
        "title": f"Software Engineer {i}",
        "company": "Acme",
        "url": f"https://example.com/{i}",
        "location": "Remote",
        "fit_score": score,
    }


def test_raises_if_webhook_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", None)
    with pytest.raises(RuntimeError):
        discord.send_notifications()


def test_no_postings_sends_nothing(monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x/y")
    monkeypatch.setattr(discord.postings_repo, "get_unnotified_above_threshold", lambda t: [])
    assert discord.send_notifications() == 0


def test_sends_batched_embeds_and_marks_notified(monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x/y")
    postings = [_posting(i) for i in range(12)]  # forces 2 batches (10 + 2)
    monkeypatch.setattr(discord.postings_repo, "get_unnotified_above_threshold", lambda t: postings)

    marked = []
    monkeypatch.setattr(discord.postings_repo, "mark_notified", lambda pid: marked.append(pid))

    sent_payloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent_payloads.append(request)
        return httpx.Response(200, json={"ok": True})

    real_client_cls = httpx.Client
    monkeypatch.setattr(
        discord.httpx, "Client", lambda timeout=None: real_client_cls(transport=httpx.MockTransport(handler))
    )

    count = discord.send_notifications()

    assert count == 12
    assert len(sent_payloads) == 2  # batched into 2 webhook calls
    assert sorted(marked) == list(range(12))


def test_failed_webhook_call_does_not_mark_notified(monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x/y")
    postings = [_posting(1)]
    monkeypatch.setattr(discord.postings_repo, "get_unnotified_above_threshold", lambda t: postings)

    marked = []
    monkeypatch.setattr(discord.postings_repo, "mark_notified", lambda pid: marked.append(pid))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "bad request"})

    real_client_cls = httpx.Client
    monkeypatch.setattr(
        discord.httpx, "Client", lambda timeout=None: real_client_cls(transport=httpx.MockTransport(handler))
    )

    count = discord.send_notifications()

    assert count == 0
    assert marked == []
