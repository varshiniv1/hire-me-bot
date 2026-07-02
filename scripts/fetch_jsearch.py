"""Fetches postings from JSearch (Google for Jobs) and upserts the ones that
pass the same filters as the ATS connectors. Runs on its own schedule
(.github/workflows/jsearch.yml, every 3 days) separate from the main
pipeline (which runs every 3-6 hours), since JSearch's free tier caps at
200 requests/month.

Deliberately NOT part of pipeline.run() -- notifications and scoring don't
need to be duplicated here. discord.send_notifications() and
scoring.score_new_postings() query Supabase by state (notified_at IS NULL /
fit_score IS NULL), not by "postings fetched this run", so rows upserted
here get picked up automatically by the next regular pipeline run.
"""

import logging

from hire_me_bot import settings
from hire_me_bot.connectors.jsearch import fetch_jsearch_postings
from hire_me_bot.db import postings_repo
from hire_me_bot.pipeline import passes_all_filters


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    if not settings.RAPIDAPI_KEY:
        logger.info("RAPIDAPI_KEY not set, nothing to do")
        return

    fetched = fetch_jsearch_postings()
    passing = [p for p in fetched if passes_all_filters(p)]
    logger.info("jsearch: %d fetched, %d passed filters", len(fetched), len(passing))

    postings_repo.upsert_postings(passing)
    print(f"Upserted {len(passing)} JSearch postings")


if __name__ == "__main__":
    main()
