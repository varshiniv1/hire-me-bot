import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"[ \t]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


def strip_html(html: str | None) -> str:
    """Best-effort HTML -> plain text. Good enough for keyword filtering and
    feeding Claude a job description; not meant to be a full HTML parser."""
    if not html:
        return ""
    text = re.sub(r"(?i)<br\s*/?>", "\n", html)
    text = re.sub(r"(?i)</p>", "\n\n", text)
    text = _TAG_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    return text.strip()


@dataclass
class Posting:
    source: str
    company: str
    external_id: str
    title: str
    location: str | None
    url: str
    description: str
    posted_at: datetime | None


class Connector(ABC):
    """Shared shape for every job board connector. Subclasses implement
    fetch_raw() (one or more HTTP calls returning raw per-job dicts) and
    normalize() (mapping one raw dict into a Posting)."""

    source_name: str

    def __init__(self, company: str, token: str, http_client: httpx.Client | None = None):
        self.company = company
        self.token = token
        self._owns_client = http_client is None
        self.http = http_client or httpx.Client(timeout=30.0)

    @abstractmethod
    def fetch_raw(self) -> list[dict]:
        """Return every raw job dict for this company's board. Must not silently
        stop at the first page if the API signals more results exist."""

    @abstractmethod
    def normalize(self, raw: dict) -> Posting:
        """Map one raw job dict into the common Posting shape. Must preserve the
        full job description text verbatim (never truncate/discard it here --
        later stages depend on having it all)."""

    def fetch(self) -> list[Posting]:
        raw_jobs = self.fetch_raw()
        postings = []
        for raw in raw_jobs:
            try:
                postings.append(self.normalize(raw))
            except Exception:
                logger.exception(
                    "Failed to normalize a %s posting for %s, skipping it",
                    self.source_name,
                    self.company,
                )
        return postings

    def close(self) -> None:
        if self._owns_client:
            self.http.close()

    def __enter__(self) -> "Connector":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
