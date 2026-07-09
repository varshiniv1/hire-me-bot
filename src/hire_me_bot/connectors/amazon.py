import logging
import re
from datetime import datetime, timezone

from hire_me_bot.connectors.base import Connector, Posting, strip_html

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.amazon.jobs/en/search.json"
_PAGE_SIZE = 100

# Amazon has no Greenhouse/Lever/Ashby/SmartRecruiters/Recruitee/Workday
# presence (see connectors/detect.py) -- normally that means routing it
# through the JSearch aggregator (connectors/jsearch.py), same as Google/
# Meta/Microsoft. But amazon.jobs exposes a stable, public, unauthenticated
# JSON search endpoint that returns full job details (title, description,
# qualifications, location, apply link) directly in the listing response --
# no separate per-job detail fetch needed, unlike Workday -- so a direct
# connector is both possible and cheap here.
#
# base_query does AND-ish matching across title+description text rather than
# fuzzy/OR matching (e.g. "software engineer new grad" returns 0 hits even
# though thousands of new-grad SWE postings exist; "software development
# engineer" -- Amazon's actual title convention -- returns 900+). A single
# broad query like "software" returns 6800+ US hits, far too much to
# paginate every run, so this targets Amazon's own title convention plus
# each TECH_TERMS category from filtering/keywords.py instead. Precise
# seniority/experience/clearance/citizenship filtering happens afterward via
# pipeline.passes_all_filters, same as every other connector.
SEARCH_QUERIES = [
    "software development engineer",
    "site reliability",
    "backend",
    "full stack",
    "frontend",
]

_WHITESPACE_RE = re.compile(r"\s+")


class AmazonConnector(Connector):
    """token is unused -- Amazon is one company with one public search API,
    not a shared ATS platform keyed by per-company board tokens."""

    source_name = "amazon"

    def fetch_raw(self) -> list[dict]:
        # Queries can overlap (e.g. a "backend" posting whose description
        # also says "full stack") -- dedupe by job id across all of them.
        by_id: dict[str, dict] = {}
        for query in SEARCH_QUERIES:
            offset = 0
            total = None
            while total is None or offset < total:
                resp = self.http.get(
                    _BASE_URL,
                    params={
                        "base_query": query,
                        "result_limit": _PAGE_SIZE,
                        "offset": offset,
                        "sort": "recent",
                        "normalized_country_code[]": "USA",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                total = data.get("hits", 0)
                jobs = data.get("jobs", [])
                if not jobs:
                    break
                for job in jobs:
                    job_id = job.get("id_icims") or job.get("id")
                    if job_id:
                        by_id[job_id] = job
                offset += len(jobs)
        logger.info(
            "amazon: fetched %d unique job postings across %d queries", len(by_id), len(SEARCH_QUERIES)
        )
        return list(by_id.values())

    def normalize(self, raw: dict) -> Posting:
        description = "\n\n".join(
            strip_html(part)
            for part in (
                raw.get("description"),
                raw.get("basic_qualifications"),
                raw.get("preferred_qualifications"),
            )
            if part
        )

        posted_at = None
        posted_date = raw.get("posted_date")
        if posted_date:
            try:
                # e.g. "July  9, 2026" -- Amazon's own feed has occasional
                # double spaces between month and day.
                normalized = _WHITESPACE_RE.sub(" ", posted_date).strip()
                posted_at = datetime.strptime(normalized, "%B %d, %Y").replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        job_id = raw.get("id_icims") or raw.get("id") or ""
        job_path = raw.get("job_path") or ""
        url = raw.get("url_next_step") or (f"https://www.amazon.jobs{job_path}" if job_path else "")

        return Posting(
            source=self.source_name,
            # Not raw.get("company_name") -- Amazon's own feed tags many
            # direct Amazon postings with a staffing/subsidiary name (e.g.
            # "KGS LLC") instead of "Amazon", which would both mislabel the
            # posting and risk matching an unrelated entry in
            # excluded_companies.yaml.
            company="Amazon",
            external_id=str(job_id),
            title=raw.get("title") or "",
            location=raw.get("normalized_location"),
            url=url,
            description=description,
            posted_at=posted_at,
        )
