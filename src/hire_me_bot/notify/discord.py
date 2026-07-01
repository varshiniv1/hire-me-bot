import logging

import httpx

from hire_me_bot import settings
from hire_me_bot.db import postings_repo

logger = logging.getLogger(__name__)

# Discord allows up to 10 embeds per message -- batch postings into a message
# each instead of one webhook call per posting, to stay well under rate limits.
_MAX_EMBEDS_PER_MESSAGE = 10


def _posting_to_embed(posting: dict) -> dict:
    subtitle = f"Fit score: {posting['fit_score']}/5"
    if posting.get("location"):
        subtitle += f" | {posting['location']}"
    return {
        "title": f"{posting['title']} @ {posting['company']}"[:256],
        "url": posting["url"],
        "description": subtitle,
    }


def _chunk(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def send_notifications() -> int:
    """Push a Discord message for every unnotified posting scoring >= the
    configured threshold, and mark each as notified. Returns the count sent."""
    if not settings.DISCORD_WEBHOOK_URL:
        raise RuntimeError("DISCORD_WEBHOOK_URL must be set to send notifications.")

    postings = postings_repo.get_unnotified_above_threshold(settings.FIT_SCORE_NOTIFY_THRESHOLD)
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
