import logging
from datetime import datetime, timezone

from hire_me_bot.connectors.base import Connector, Posting, strip_html
from hire_me_bot.filtering.keywords import passes_keyword_filter

logger = logging.getLogger(__name__)

_PAGE_SIZE = 20


class WorkdayConnector(Connector):
    """Workday's CXS API needs a summary POST (paginated via offset) plus a
    separate detail GET per job for the full description -- unlike the other
    5 connectors' single-GET shape. A single company's board can run into the
    thousands of postings (e.g. RTX has 4000+), so the keyword filter is
    applied to each summary's title BEFORE fetching its detail here, not
    after like every other connector -- fetching full descriptions for
    thousands of irrelevant postings every 3 hours would be wasteful and
    slow. (pipeline.py still re-applies the filter after normalize(), same
    as for every connector; this is purely a cost optimization, not a
    behavior change.)
    """

    source_name = "workday"

    def __init__(self, company: str, token: str, http_client=None):
        super().__init__(company, token, http_client)
        # token format from seed_companies.py: "{tenant}/{wdN}/{site}"
        self.tenant, self.wd_host, self.site = token.split("/", 2)

    @property
    def _base_url(self) -> str:
        return f"https://{self.tenant}.{self.wd_host}.myworkdayjobs.com/wday/cxs/{self.tenant}/{self.site}"

    def fetch_raw(self) -> list[dict]:
        summaries = []
        offset = 0
        total = None
        while total is None or offset < total:
            resp = self.http.post(
                f"{self._base_url}/jobs",
                json={"limit": _PAGE_SIZE, "offset": offset, "searchText": ""},
            )
            resp.raise_for_status()
            data = resp.json()
            total = data.get("total", 0)
            page = data.get("jobPostings", [])
            if not page:
                break
            summaries.extend(page)
            offset += len(page)
        logger.info("workday: fetched %d job summaries for %s", len(summaries), self.company)

        matching = [s for s in summaries if passes_keyword_filter(s.get("title", ""))]
        logger.info(
            "workday: %d/%d summaries pass keyword filter for %s, fetching their details",
            len(matching),
            len(summaries),
            self.company,
        )

        full_postings = []
        for summary in matching:
            path = summary.get("externalPath")
            if not path:
                continue
            detail_resp = self.http.get(f"{self._base_url}{path}")
            if detail_resp.status_code != 200:
                logger.warning(
                    "workday: failed to fetch detail for %s (%s), skipping",
                    path,
                    detail_resp.status_code,
                )
                continue
            full_postings.append(detail_resp.json())
        return full_postings

    def normalize(self, raw: dict) -> Posting:
        info = raw.get("jobPostingInfo", {})

        posted_at = None
        start_date = info.get("startDate")
        if start_date:
            try:
                posted_at = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        return Posting(
            source=self.source_name,
            company=self.company,
            external_id=info.get("jobReqId") or info.get("id", ""),
            title=info.get("title", ""),
            location=info.get("location"),
            url=info.get("externalUrl", ""),
            description=strip_html(info.get("jobDescription")),
            posted_at=posted_at,
        )
