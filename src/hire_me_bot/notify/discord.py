import logging
import time
from datetime import datetime, timezone

import httpx

from hire_me_bot import settings
from hire_me_bot.db import postings_repo

logger = logging.getLogger(__name__)

_MAX_RATE_LIMIT_RETRIES = 5

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


def _post_with_retry(client: httpx.Client, payload: dict) -> httpx.Response:
    """POST to the webhook, retrying on Discord's 429 rate-limit response
    (honoring the retry_after it returns) instead of dropping the batch.

    A prior run without this hit Discord's rate limit after ~57 messages and
    silently skipped the remaining ~1900+ batches -- they never got flagged
    as failed, they just never went out and never got marked notified,
    which meant next run's get_unnotified() would try (and likely fail) all
    of them again.
    """
    resp = client.post(settings.DISCORD_WEBHOOK_URL, json=payload)
    for attempt in range(_MAX_RATE_LIMIT_RETRIES):
        if resp.status_code != 429:
            return resp
        retry_after = 1.0
        try:
            retry_after = float(resp.json().get("retry_after", 1.0))
        except (ValueError, KeyError):
            pass
        logger.warning(
            "Discord rate limited, retrying in %.1fs (attempt %d/%d)",
            retry_after,
            attempt + 1,
            _MAX_RATE_LIMIT_RETRIES,
        )
        time.sleep(retry_after + 0.25)
        resp = client.post(settings.DISCORD_WEBHOOK_URL, json=payload)
    return resp


def send_notifications() -> int:
    """Push a Discord message for every unnotified posting, and mark each as
    notified. Returns the count sent.

    While settings.SCORING_ENABLED is False, every keyword-matched posting is
    notified (fit_score never gets set, so the threshold gate can't apply).
    Once scoring is wired back in, this goes back to only notifying postings
    scoring >= FIT_SCORE_NOTIFY_THRESHOLD.

    Postings older than settings.NOTIFY_MAX_AGE_DAYS are never notified
    (still stored forever, just not surfaced) -- catching a 3-week-old
    listing for the first time isn't actionable the way a fresh one is.
    """
    if not settings.DISCORD_WEBHOOK_URL:
        raise RuntimeError("DISCORD_WEBHOOK_URL must be set to send notifications.")

    if settings.SCORING_ENABLED:
        postings = postings_repo.get_unnotified_above_threshold(
            settings.FIT_SCORE_NOTIFY_THRESHOLD, settings.NOTIFY_MAX_AGE_DAYS
        )
    else:
        postings = postings_repo.get_unnotified(settings.NOTIFY_MAX_AGE_DAYS)
    if not postings:
        return 0

    sent = 0
    with httpx.Client(timeout=15.0) as client:
        for i, batch in enumerate(_chunk(postings, _MAX_EMBEDS_PER_MESSAGE)):
            if i > 0:
                # Proactive pacing, not just reactive retry -- Discord's webhook
                # rate limit is roughly 5 requests/2s, so spacing sends out
                # means far fewer 429s to begin with on a large backlog.
                time.sleep(0.3)
            payload = {"embeds": [_posting_to_embed(p) for p in batch]}
            resp = _post_with_retry(client, payload)
            if resp.status_code >= 300:
                logger.error("Discord webhook failed (%s): %s", resp.status_code, resp.text)
                continue
            for posting in batch:
                postings_repo.mark_notified(posting["id"])
            sent += len(batch)

    return sent
