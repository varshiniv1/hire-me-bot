import logging
from datetime import datetime

from hire_me_bot.connectors.base import Connector, Posting, strip_html

logger = logging.getLogger(__name__)


class GreenhouseConnector(Connector):
    source_name = "greenhouse"

    def fetch_raw(self) -> list[dict]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{self.token}/jobs"
        resp = self.http.get(url, params={"content": "true"})
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("jobs", [])
        # Greenhouse's public boards endpoint returns every job in one response
        # (no offset/page params); log the count so a company with an unusually
        # large board doesn't go unnoticed.
        logger.info("greenhouse: fetched %d jobs for %s", len(jobs), self.company)
        return jobs

    def normalize(self, raw: dict) -> Posting:
        location = None
        loc = raw.get("location")
        if isinstance(loc, dict):
            location = loc.get("name")
        posted_at = None
        if raw.get("updated_at"):
            try:
                posted_at = datetime.fromisoformat(raw["updated_at"])
            except ValueError:
                pass
        return Posting(
            source=self.source_name,
            company=self.company,
            external_id=str(raw["id"]),
            title=raw["title"],
            location=location,
            url=raw["absolute_url"],
            description=strip_html(raw.get("content")),
            posted_at=posted_at,
        )
