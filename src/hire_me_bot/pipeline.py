import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from zoneinfo import ZoneInfo

import yaml

from hire_me_bot import settings
from hire_me_bot.connectors.ashby import AshbyConnector
from hire_me_bot.connectors.base import Posting
from hire_me_bot.connectors.greenhouse import GreenhouseConnector
from hire_me_bot.connectors.lever import LeverConnector
from hire_me_bot.connectors.recruitee import RecruiteeConnector
from hire_me_bot.connectors.smartrecruiters import SmartRecruitersConnector
from hire_me_bot.connectors.workday import WorkdayConnector
from hire_me_bot.db import postings_repo
from hire_me_bot.filtering.citizenship import requires_citizenship
from hire_me_bot.filtering.clearance import requires_clearance
from hire_me_bot.filtering.experience import requires_too_much_experience
from hire_me_bot.filtering.keywords import passes_keyword_filter
from hire_me_bot.filtering.location import is_usa_location
from hire_me_bot.notify import discord
from hire_me_bot.scoring.scorer import score_new_postings

logger = logging.getLogger(__name__)

CONNECTOR_CLASSES = {
    "greenhouse": GreenhouseConnector,
    "lever": LeverConnector,
    "ashby": AshbyConnector,
    "workday": WorkdayConnector,
    "smartrecruiters": SmartRecruitersConnector,
    "recruitee": RecruiteeConnector,
}

# All I/O-bound HTTP calls against ~3000+ companies -- fetch concurrently, but
# capped so we're not hammering everyone's job boards at once.
MAX_WORKERS = 20


def _load_companies() -> list[dict]:
    with open(settings.COMPANIES_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def _load_profile() -> dict:
    with open(settings.PROFILE_CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def passes_all_filters(posting: Posting) -> bool:
    if not passes_keyword_filter(posting.title):
        return False
    if not is_usa_location(posting.location):
        return False
    for text in (posting.title, posting.description):
        if requires_clearance(text):
            return False
        if requires_citizenship(text):
            return False
        if requires_too_much_experience(text, settings.MAX_YEARS_EXPERIENCE):
            return False
    return True


def _fetch_company(company: dict) -> list[Posting]:
    connector_cls = CONNECTOR_CLASSES.get(company.get("source"))
    if connector_cls is None:
        return []
    try:
        with connector_cls(company["name"], company["token"]) as connector:
            postings = connector.fetch()
    except Exception:
        logger.exception(
            "Failed to fetch %s (%s), skipping this run", company["name"], company.get("source")
        )
        return []
    return [p for p in postings if passes_all_filters(p)]


def _fetch_all(companies: list[dict]) -> list[Posting]:
    all_postings: list[Posting] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_fetch_company, company): company for company in companies}
        for future in as_completed(futures):
            all_postings.extend(future.result())
    return all_postings


def run() -> None:
    now_eastern = datetime.now(ZoneInfo("America/New_York"))
    # Logging context only -- scoring's batch-vs-individual choice is driven by
    # actual volume (scoring/scorer.py), not by day of week.
    is_busy_day = now_eastern.weekday() in (1, 2, 3)  # Tue/Wed/Thu
    logger.info(
        "Starting pipeline run at %s Eastern (busy_day=%s)",
        now_eastern.isoformat(),
        is_busy_day,
    )

    companies = _load_companies()
    profile = _load_profile()
    logger.info("Loaded %d companies from config", len(companies))

    fetched = _fetch_all(companies)
    logger.info("Fetched %d postings passing the keyword filter", len(fetched))

    postings_repo.upsert_postings(fetched)

    if settings.SCORING_ENABLED:
        unscored = postings_repo.get_unscored()
        logger.info("%d postings need scoring", len(unscored))
        score_new_postings(unscored, profile)
    else:
        logger.info("Scoring disabled (no LLM provider wired in yet), skipping")

    notified_count = discord.send_notifications()
    logger.info("Sent Discord notifications for %d postings", notified_count)

    discord.send_run_summary(len(fetched), notified_count)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
