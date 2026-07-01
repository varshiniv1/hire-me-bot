import logging
from datetime import datetime, timezone

from hire_me_bot.connectors.base import Connector, Posting, strip_html

logger = logging.getLogger(__name__)


class RecruiteeConnector(Connector):
    source_name = "recruitee"

    def fetch_raw(self) -> list[dict]:
        url = f"https://{self.token}.recruitee.com/api/offers"
        resp = self.http.get(url)
        resp.raise_for_status()
        data = resp.json()
        offers = data.get("offers", [])
        logger.info("recruitee: fetched %d jobs for %s", len(offers), self.company)
        return offers

    def normalize(self, raw: dict) -> Posting:
        location = raw.get("city") or raw.get("country")
        description_parts = [
            strip_html(raw.get("description")),
            strip_html(raw.get("requirements")),
        ]
        description = "\n\n".join(part for part in description_parts if part)

        posted_at = None
        raw_date = raw.get("published_at") or raw.get("created_at")
        if raw_date:
            # Recruitee returns "2026-06-22 17:54:58 UTC", not ISO8601 -- no "T"
            # separator, "UTC" suffix instead of "Z"/offset, so fromisoformat()
            # can't parse it directly.
            try:
                posted_at = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S UTC").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                pass

        return Posting(
            source=self.source_name,
            company=self.company,
            external_id=str(raw["id"]),
            title=raw["title"],
            location=location,
            url=raw.get("careers_url"),
            description=description,
            posted_at=posted_at,
        )
