import logging
from datetime import datetime, timezone

import httpx

from hire_me_bot import settings
from hire_me_bot.db import postings_repo

logger = logging.getLogger(__name__)

# Discord allows up to 10 embeds per message, but also caps the COMBINED
# character count across every embed in one message at 6000 total (separate
# from each embed's own 4096-char description limit). A shorter JD preview
# means more embeds safely fit per message before hitting that combined cap
# (see test_batched_message_stays_under_discord_combined_embed_limit, which
# guards this tradeoff against a future bump to either constant).
_MAX_EMBEDS_PER_MESSAGE = 5

_JD_PREVIEW_CHARS = 500


def _jd_preview(description: str) -> str:
    description = (description or "").strip()
    if len(description) <= _JD_PREVIEW_CHARS:
        return description
    return description[:_JD_PREVIEW_CHARS].rstrip() + "..."


def _posted_days_ago_text(posted_at: str | None) -> str:
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


def _posting_to_embed(posting: dict) -> dict:
    lines = [
        f"Location: {posting.get('location') or 'Not specified'}",
        _posted_days_ago_text(posting.get("posted_at")),
    ]
    if posting.get("fit_score") is not None:
        lines.append(f"Fit: {posting['fit_score']}/5")
    jd_preview = _jd_preview(posting.get("description", ""))
    if jd_preview:
        lines.append("")
        lines.append(jd_preview)
    lines.append("")
    lines.append(f"[Apply here]({posting['url']})")
    return {
        "title": f"{posting['title']} @ {posting['company']}"[:256],
        "url": posting["url"],
        "description": "\n".join(lines)[:4096],
    }


def _chunk(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def send_notifications() -> int:
    """Push a Discord message for every unnotified posting, and mark each as
    notified. Returns the count sent.

    While settings.SCORING_ENABLED is False, every keyword-matched posting is
    notified (fit_score never gets set, so the threshold gate can't apply).
    Once scoring is wired back in, this goes back to only notifying postings
    scoring >= FIT_SCORE_NOTIFY_THRESHOLD.
    """
    if not settings.DISCORD_WEBHOOK_URL:
        raise RuntimeError("DISCORD_WEBHOOK_URL must be set to send notifications.")

    if settings.SCORING_ENABLED:
        postings = postings_repo.get_unnotified_above_threshold(settings.FIT_SCORE_NOTIFY_THRESHOLD)
    else:
        postings = postings_repo.get_unnotified()
    if not postings:
        return 0

    sent = 0
    with httpx.Client(timeout=15.0) as client:
        for batch in _chunk(postings, _MAX_EMBEDS_PER_MESSAGE):
            payload = {"embeds": [_posting_to_embed(p) for p in batch]}
            resp = client.post(settings.DISCORD_WEBHOOK_URL, json=payload)
            if resp.status_code >= 300:
                logger.error("Discord webhook failed (%s): %s", resp.status_code, resp.text)
                continue
            for posting in batch:
                postings_repo.mark_notified(posting["id"])
            sent += len(batch)

    return sent
