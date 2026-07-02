import logging
import time
from datetime import datetime, timezone

import httpx

from hire_me_bot import settings
from hire_me_bot.db import postings_repo
from hire_me_bot.filtering.keywords import is_internship_title
from hire_me_bot.format_utils import posted_days_ago_text

logger = logging.getLogger(__name__)

_MAX_RATE_LIMIT_RETRIES = 5

# Discord allows up to 10 embeds per message, but also caps the COMBINED
# character count across every embed in one message at 6000 total (separate
# from each embed's own 4096-char description limit). Embeds are now just
# title + location + posted-date (no JD preview/apply-link line, per user
# request to keep the card minimal -- the title itself is already a link to
# the posting), so 10 fits safely under 6000 even at max title length
# (see test_batched_message_stays_under_discord_combined_embed_limit).
_MAX_EMBEDS_PER_MESSAGE = 10


def _posting_to_embed(posting: dict) -> dict:
    lines = [
        f"Location: {posting.get('location') or 'Not specified'}",
        posted_days_ago_text(posting.get("posted_at")),
    ]
    if posting.get("fit_score") is not None:
        lines.append(f"Fit: {posting['fit_score']}/5")
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
    """Push a Discord message for every unnotified posting, grouped under an
    "Internships" header and a "Full-Time" header (in that order) so it's
    scannable at a glance which bucket a posting falls into. Marks each
    notified as it sends. Returns the total count sent.

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

    internships = [p for p in postings if is_internship_title(p["title"])]
    full_time = [p for p in postings if not is_internship_title(p["title"])]

    sent = 0
    with httpx.Client(timeout=15.0) as client:
        first_request = True
        for header, group in (("Internships", internships), ("Full-Time", full_time)):
            if not group:
                continue

            if not first_request:
                # Proactive pacing, not just reactive retry -- Discord's webhook
                # rate limit is roughly 5 requests/2s, so spacing sends out
                # means far fewer 429s to begin with on a large backlog.
                time.sleep(0.3)
            first_request = False

            header_resp = _post_with_retry(client, {"content": f"**{header}**"})
            if header_resp.status_code >= 300:
                logger.error(
                    "Discord section-header webhook failed (%s): %s",
                    header_resp.status_code,
                    header_resp.text,
                )

            for batch in _chunk(group, _MAX_EMBEDS_PER_MESSAGE):
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


def send_run_summary(fetched_count: int, notified_count: int) -> None:
    """One plain-text heartbeat message every pipeline run, even when
    nothing new was found -- so a quiet Discord channel means "nothing new
    right now," not "is this thing even still running?"."""
    if not settings.DISCORD_WEBHOOK_URL:
        return
    now = datetime.now(timezone.utc)
    payload = {
        "content": (
            f"Pipeline run at {now.strftime('%Y-%m-%d %H:%M')} UTC -- "
            f"{fetched_count} posting(s) fetched, {notified_count} new notification(s) sent."
        )
    }
    with httpx.Client(timeout=15.0) as client:
        resp = _post_with_retry(client, payload)
    if resp.status_code >= 300:
        logger.error("Discord run-summary webhook failed (%s): %s", resp.status_code, resp.text)
