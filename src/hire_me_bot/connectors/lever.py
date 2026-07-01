import logging
from datetime import datetime, timezone

from hire_me_bot.connectors.base import Connector, Posting, strip_html

logger = logging.getLogger(__name__)


class LeverConnector(Connector):
    source_name = "lever"

    def fetch_raw(self) -> list[dict]:
        url = f"https://api.lever.co/v0/postings/{self.token}"
        resp = self.http.get(url, params={"mode": "json"})
        resp.raise_for_status()
        jobs = resp.json()
        # Lever's public postings endpoint returns the full list in one response,
        # no pagination params -- log the count for visibility on large boards.
        logger.info("lever: fetched %d jobs for %s", len(jobs), self.company)
        return jobs

    def normalize(self, raw: dict) -> Posting:
        categories = raw.get("categories") or {}
        description = raw.get("descriptionPlain") or strip_html(raw.get("description"))
        posted_at = None
        if raw.get("createdAt"):
            posted_at = datetime.fromtimestamp(raw["createdAt"] / 1000, tz=timezone.utc)
        return Posting(
            source=self.source_name,
            company=self.company,
            external_id=str(raw["id"]),
            title=raw["text"],
            location=categories.get("location"),
            url=raw.get("hostedUrl") or raw.get("applyUrl"),
            description=description,
            posted_at=posted_at,
        )
