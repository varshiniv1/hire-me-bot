import logging
from datetime import datetime

from hire_me_bot.connectors.base import Connector, Posting, strip_html

logger = logging.getLogger(__name__)


class AshbyConnector(Connector):
    source_name = "ashby"

    def fetch_raw(self) -> list[dict]:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{self.token}"
        resp = self.http.get(url)
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("jobs", [])
        logger.info("ashby: fetched %d jobs for %s", len(jobs), self.company)
        return jobs

    def normalize(self, raw: dict) -> Posting:
        description = raw.get("descriptionPlain") or strip_html(raw.get("descriptionHtml"))
        posted_at = None
        raw_published = raw.get("publishedAt") or raw.get("publishedDate")
        if raw_published:
            try:
                posted_at = datetime.fromisoformat(raw_published.replace("Z", "+00:00"))
            except ValueError:
                pass
        return Posting(
            source=self.source_name,
            company=self.company,
            external_id=str(raw["id"]),
            title=raw["title"],
            location=raw.get("location"),
            url=raw.get("jobUrl") or raw.get("applyUrl"),
            description=description,
            posted_at=posted_at,
        )
