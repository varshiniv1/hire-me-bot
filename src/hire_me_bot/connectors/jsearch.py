"""JSearch (Google for Jobs, via RapidAPI) -- a search-query-keyed source,
unlike the 6 company-keyed ATS connectors. Catches postings from companies
that have no Greenhouse/Lever/Ashby/SmartRecruiters/Recruitee/Workday
presence at all. A legitimate aggregator API, not a LinkedIn/Indeed scraper.

Optional: no-ops cleanly if RAPIDAPI_KEY isn't set (see settings.py), so it
never blocks the core pipeline. Meant to run on its own infrequent schedule
(scripts/fetch_jsearch.py, .github/workflows/jsearch.yml) separate from the
main pipeline, since the free tier caps at 200 requests/month."""

import logging
from datetime import datetime

import httpx

from hire_me_bot import settings
from hire_me_bot.connectors.base import Posting
from hire_me_bot.connectors.detect import detect_source_and_token

logger = logging.getLogger(__name__)

API_HOST = "jsearch.p.rapidapi.com"

# Kept short deliberately -- 11 queries x 10 runs/month (every 3 days) = 110
# requests, well under the 200/month free-tier cap with room to grow.
# Precise role-type/seniority/experience/clearance/citizenship filtering
# happens afterward via pipeline.passes_all_filters, the exact same filters
# the ATS connectors use -- these queries just need to cast a reasonably
# relevant net, not be exhaustive.
#
# The last 3 target off-cycle/grad-friendly internships specifically --
# Big Tech's ATS boards (covered by the 6 direct connectors) are almost
# entirely locked to the summer academic-calendar pipeline, but smaller/
# mid-size companies posting off-cycle programs are more likely to show up
# via a search aggregator like this than a direct connector.
SEARCH_QUERIES = [
    "software engineer new grad",
    "software engineer entry level",
    "backend engineer entry level",
    "frontend engineer entry level",
    "full stack engineer new grad",
    "site reliability engineer new grad",
    "software engineering internship",
    "software engineering co-op",
    "software engineering off-cycle internship",
    "software engineering internship recent graduate",
    "software engineering fellowship",
]


def _fetch_query(client: httpx.Client, query: str) -> list[dict]:
    # RapidAPI retired the old "/search" route in favor of "/search-v2"
    # (cursor-based pagination) -- same auth and params, but the response
    # envelope now nests the job list one level deeper: {"data": {"jobs":
    # [...]}} instead of {"data": [...]}. The old route now 404s with a
    # RapidAPI-level "Endpoint '/search' does not exist" error.
    resp = client.get(
        f"https://{API_HOST}/search-v2",
        params={"query": query, "num_pages": "1", "country": "us", "date_posted": "week"},
        headers={"X-RapidAPI-Key": settings.RAPIDAPI_KEY, "X-RapidAPI-Host": API_HOST},
    )
    if resp.status_code >= 400:
        # RapidAPI's error body (e.g. "not subscribed", "endpoint doesn't
        # exist") is far more diagnostic than a bare status code -- log it
        # before raising so a misconfigured key/host is debuggable from CI
        # logs alone, without needing to reproduce locally with the secret.
        logger.error("JSearch request failed (%d): %s", resp.status_code, resp.text[:500])
    resp.raise_for_status()
    return resp.json().get("data", {}).get("jobs", [])


def _parse_posted_at(raw: dict) -> datetime | None:
    raw_date = raw.get("job_posted_at_datetime_utc")
    if not raw_date:
        return None
    try:
        return datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
    except ValueError:
        return None


def normalize(raw: dict) -> Posting | None:
    """Returns None (not an exception) for results we deliberately skip --
    missing required fields, already covered by a direct ATS connector, or
    not confirmed USA. Distinct from a parse failure, which is a bug."""
    apply_link = raw.get("job_apply_link")
    title = raw.get("job_title")
    company = raw.get("employer_name")
    job_id = raw.get("job_id")
    if not (apply_link and title and company and job_id):
        return None

    # A direct ATS connector gives more complete data (full JD, exact
    # posted date, guaranteed liveness) for the same job than a
    # search-aggregator result -- skip rather than duplicate it.
    if detect_source_and_token(apply_link) is not None:
        return None

    # The query already scopes country=us, but don't trust that blindly --
    # skip (don't guess) if country is missing or not confirmed US.
    if (raw.get("job_country") or "").upper() != "US":
        return None

    location_parts = [p for p in (raw.get("job_city"), raw.get("job_state")) if p]
    location = (", ".join(location_parts) + ", USA") if location_parts else "USA"

    return Posting(
        source="jsearch",
        company=company,
        external_id=job_id,
        title=title,
        location=location,
        url=apply_link,
        description=raw.get("job_description") or "",
        posted_at=_parse_posted_at(raw),
    )


def fetch_jsearch_postings() -> list[Posting]:
    if not settings.RAPIDAPI_KEY:
        logger.info("RAPIDAPI_KEY not set, skipping JSearch fetch")
        return []

    postings: list[Posting] = []
    with httpx.Client(timeout=30.0) as client:
        for query in SEARCH_QUERIES:
            try:
                raw_jobs = _fetch_query(client, query)
            except Exception:
                logger.exception("JSearch query failed: %r, skipping it", query)
                continue
            for raw in raw_jobs:
                try:
                    posting = normalize(raw)
                except Exception:
                    logger.exception("Failed to normalize a JSearch posting, skipping it")
                    continue
                if posting is not None:
                    postings.append(posting)

    logger.info("jsearch: fetched %d postings across %d queries", len(postings), len(SEARCH_QUERIES))
    return postings
