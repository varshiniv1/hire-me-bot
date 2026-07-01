import logging

from hire_me_bot import settings
from hire_me_bot.db import postings_repo
from hire_me_bot.scoring import claude_client
from hire_me_bot.scoring.jd_extract import extract_requirements

logger = logging.getLogger(__name__)


def _chunk(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def score_new_postings(new_postings: list[dict], profile: dict) -> None:
    """Score every posting in new_postings (rows with id/company/title/description)
    against profile, writing fit_score back to storage. Branches on volume: batch
    calls when there's a lot to score in one run, one call per posting otherwise --
    not tied to day-of-week, purely how many postings this run actually found."""
    if not new_postings:
        return
    if len(new_postings) <= settings.BATCH_SCORING_TRIGGER:
        _score_individually(new_postings, profile)
    else:
        _score_in_batches(new_postings, profile)


def _score_individually(postings: list[dict], profile: dict) -> None:
    for posting in postings:
        jd_snippet = extract_requirements(posting["description"])
        try:
            score = claude_client.score_posting(
                profile, posting["company"], posting["title"], jd_snippet
            )
        except Exception:
            logger.exception(
                "Failed to score posting %s (%s), skipping", posting["id"], posting["title"]
            )
            continue
        postings_repo.update_score(posting["id"], score)


def _score_in_batches(postings: list[dict], profile: dict) -> None:
    for batch in _chunk(postings, settings.BATCH_SIZE):
        items = [
            {
                "posting_id": p["id"],
                "company": p["company"],
                "title": p["title"],
                "jd_snippet": extract_requirements(p["description"]),
            }
            for p in batch
        ]
        try:
            scores = claude_client.score_batch(profile, items)
        except Exception:
            logger.exception("Failed to score a batch of %d postings, skipping batch", len(batch))
            continue

        expected_ids = {p["id"] for p in batch}
        if set(scores.keys()) != expected_ids:
            logger.warning(
                "Batch score response mismatch: expected ids %s, got %s",
                expected_ids,
                set(scores.keys()),
            )

        for posting_id, score in scores.items():
            if posting_id in expected_ids:
                postings_repo.update_score(posting_id, score)
