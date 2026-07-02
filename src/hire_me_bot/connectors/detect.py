"""Detects which of our 6 supported ATS platforms (if any) a job posting URL
belongs to, and extracts the company's board token from it. Shared by
scripts/seed_companies.py (mapping SimplifyJobs listings to companies.yaml
entries) and connectors/jsearch.py (skipping JSearch results that duplicate
a company we already crawl directly -- direct ATS connectors give more
complete data than a search-aggregator result for the same job)."""

import re
from urllib.parse import unquote, urlparse

_GREENHOUSE_RE = re.compile(r"(?:job-boards|boards)(?:\.\w+)?\.greenhouse\.io$")
_ASHBY_RE = re.compile(r"jobs\.ashbyhq\.com$")
_LEVER_RE = re.compile(r"jobs\.lever\.co$")
_SMARTRECRUITERS_RE = re.compile(r"jobs\.smartrecruiters\.com$")
_RECRUITEE_RE = re.compile(r"^([\w-]+)\.recruitee\.com$")
_WORKDAY_RE = re.compile(r"^([\w-]+)\.(wd\d+)\.myworkdayjobs\.com$")


def _first_path_segment(path: str) -> str | None:
    parts = [p for p in path.split("/") if p]
    return unquote(parts[0]) if parts else None


def detect_source_and_token(url: str) -> tuple[str, str] | None:
    """Return (source, token) if this posting URL is on one of our supported
    ATS platforms, else None."""
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()

    if _GREENHOUSE_RE.search(netloc):
        token = _first_path_segment(parsed.path)
        return ("greenhouse", token) if token else None

    if _ASHBY_RE.search(netloc):
        token = _first_path_segment(parsed.path)
        return ("ashby", token) if token else None

    if _LEVER_RE.search(netloc):
        token = _first_path_segment(parsed.path)
        return ("lever", token) if token else None

    if _SMARTRECRUITERS_RE.search(netloc):
        token = _first_path_segment(parsed.path)
        return ("smartrecruiters", token) if token else None

    match = _RECRUITEE_RE.match(netloc)
    if match:
        return ("recruitee", match.group(1))

    match = _WORKDAY_RE.match(netloc)
    if match:
        # Workday needs both the tenant subdomain and the site path segment
        # (e.g. "rec_rtx_ext_gateway") to build its CXS API endpoint later.
        tenant, wd = match.group(1), match.group(2)
        site = _first_path_segment(parsed.path)
        if not site:
            return None
        return ("workday", f"{tenant}/{wd}/{site}")

    return None
