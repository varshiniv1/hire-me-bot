import logging
from datetime import datetime, timezone

from hire_me_bot.connectors.base import Connector, Posting, strip_html
from hire_me_bot.filtering.keywords import passes_keyword_filter

logger = logging.getLogger(__name__)

_PAGE_SIZE = 100


class SmartRecruitersConnector(Connector):
    """The list endpoint only returns summaries -- fetching every posting's
    full detail (needed for its description) before filtering would mean
    hundreds of wasted calls for a large board, so the keyword filter is
    applied to each summary's title first, same as WorkdayConnector."""

    source_name = "smartrecruiters"

    def fetch_raw(self) -> list[dict]:
        base_url = f"https://api.smartrecruiters.com/v1/companies/{self.token}/postings"
        summaries = []
        offset = 0
        total = None
        while total is None or offset < total:
            resp = self.http.get(base_url, params={"limit": _PAGE_SIZE, "offset": offset})
            resp.raise_for_status()
            data = resp.json()
            total = data.get("totalFound", 0)
            page = data.get("content", [])
            if not page:
                break
            summaries.extend(page)
            offset += len(page)
        logger.info("smartrecruiters: fetched %d job summaries for %s", len(summaries), self.company)

        matching = [s for s in summaries if passes_keyword_filter(s.get("name", ""))]
        logger.info(
            "smartrecruiters: %d/%d summaries pass keyword filter for %s, fetching their details",
            len(matching),
            len(summaries),
            self.company,
        )

        full_postings = []
        for summary in matching:
            detail_url = f"{base_url}/{summary['id']}"
            detail_resp = self.http.get(detail_url)
            if detail_resp.status_code != 200:
                logger.warning(
                    "smartrecruiters: failed to fetch detail for posting %s (%s), skipping",
                    summary.get("id"),
                    detail_resp.status_code,
                )
                continue
            full_postings.append(detail_resp.json())
        return full_postings

    def normalize(self, raw: dict) -> Posting:
        location = raw.get("location") or {}
        location_str = ", ".join(
            filter(None, [location.get("city"), location.get("region"), location.get("country")])
        ) or None

        job_ad = raw.get("jobAd") or {}
        sections = job_ad.get("sections") or {}
        description_parts = []
        for key in ("jobDescription", "qualifications", "additionalInformation"):
            section = sections.get(key) or {}
            text = section.get("text")
            if text:
                description_parts.append(strip_html(text))
        description = "\n\n".join(description_parts)

        url = raw.get("applyUrl") or raw.get("postingUrl") or (raw.get("ref") or {}).get("jobAd", "")

        posted_at = None
        released_date = raw.get("releasedDate")
        if released_date:
            try:
                posted_at = datetime.fromisoformat(released_date.replace("Z", "+00:00"))
            except ValueError:
                pass

        return Posting(
            source=self.source_name,
            company=self.company,
            external_id=str(raw["id"]),
            title=raw["name"],
            location=location_str,
            url=url,
            description=description,
            posted_at=posted_at,
        )
