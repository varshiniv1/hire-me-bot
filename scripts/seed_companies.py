"""Seeder/re-seeder: builds or updates config/companies.yaml from the
SimplifyJobs internship + new-grad tracker repos.

Those repos don't publish a plain company->ATS-token map -- they publish a
`listings.json` of individual postings, each with a `url` pointing at the
actual application page. We derive the (source, token) for a company by
parsing that URL's domain/path, since the ATS token is embedded in it
(e.g. https://jobs.lever.co/{token}/... or https://{token}.recruitee.com/...).

Every company found this way is treated identically -- no ranking/priority.
Postings whose URL doesn't match one of our 6 supported ATS platforms are
simply not mappable to a connector and are skipped (e.g. Workday-adjacent
Oracle Cloud/iCIMS/custom career sites, big-tech proprietary systems).

Run with no args (or --merge) to MERGE: only ADD companies newly detected
upstream that aren't already present (by source+token) and aren't on the
excluded_companies.yaml blocklist -- this is what the weekly re-seed
workflow uses, since it must never silently undo manual curation (renamed
tokens, removed staffing agencies, hand-added companies not in Simplify's
repos). Run with --full-rewrite to fully regenerate the file from upstream
data only, discarding any hand-edits (rarely what you want).
"""

import argparse
import logging
import re
from collections import Counter
from urllib.parse import unquote, urlparse

import httpx
import yaml

from hire_me_bot import settings

logger = logging.getLogger(__name__)

LISTINGS_URLS = [
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json",
    "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json",
]

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
        # Stored as "tenant/wdN/site" -- the (not-yet-built) Workday connector
        # is responsible for parsing this composite token.
        tenant, wd = match.group(1), match.group(2)
        site = _first_path_segment(parsed.path)
        if not site:
            return None
        return ("workday", f"{tenant}/{wd}/{site}")

    return None


def fetch_listings() -> list[dict]:
    all_listings = []
    with httpx.Client(timeout=60.0) as client:
        for url in LISTINGS_URLS:
            resp = client.get(url)
            resp.raise_for_status()
            listings = resp.json()
            logger.info("fetched %d listings from %s", len(listings), url)
            all_listings.extend(listings)
    return all_listings


def build_companies(listings: list[dict]) -> list[dict]:
    # company_name -> Counter of (source, token) pairs seen across its postings
    votes: dict[str, Counter] = {}
    for item in listings:
        company = (item.get("company_name") or "").strip()
        url = item.get("url")
        if not company or not url:
            continue
        detected = detect_source_and_token(url)
        if not detected:
            continue
        votes.setdefault(company, Counter())[detected] += 1

    companies = []
    for company, counter in votes.items():
        (source, token), _ = counter.most_common(1)[0]
        companies.append({"name": company, "source": source, "token": token})

    companies.sort(key=lambda c: c["name"].lower())
    return companies


def load_existing_companies() -> list[dict]:
    if not settings.COMPANIES_CONFIG_PATH.exists():
        return []
    with open(settings.COMPANIES_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def load_excluded_names() -> set[str]:
    if not settings.EXCLUDED_COMPANIES_CONFIG_PATH.exists():
        return set()
    with open(settings.EXCLUDED_COMPANIES_CONFIG_PATH, encoding="utf-8") as f:
        names = yaml.safe_load(f) or []
    return {n.strip().lower() for n in names}


def merge_companies(existing: list[dict], detected: list[dict], excluded_names: set[str]) -> list[dict]:
    """Adds companies from `detected` that aren't already present (matched by
    (source, token), since a company may be hand-renamed) and aren't on the
    exclusion blocklist. Never removes or modifies an existing entry."""
    existing_keys = {(c["source"], c["token"]) for c in existing}
    merged = list(existing)
    added = 0
    for company in detected:
        key = (company["source"], company["token"])
        if key in existing_keys:
            continue
        if company["name"].strip().lower() in excluded_names:
            continue
        merged.append(company)
        existing_keys.add(key)
        added += 1
    merged.sort(key=lambda c: c["name"].lower())
    logger.info("merge: %d new companies added, %d already present", added, len(existing))
    return merged


def write_companies(companies: list[dict]) -> None:
    header = (
        "# Seeded/re-seeded by scripts/seed_companies.py from the SimplifyJobs internship/new-grad\n"
        "# tracker repos, then hand-edited. Hand-edit freely to add/remove companies -- every\n"
        "# company here is crawled and scored identically, no priority/bias between them.\n"
        "# Companies removed by hand (e.g. staffing agencies) should also be added to\n"
        "# excluded_companies.yaml so the weekly re-seed doesn't bring them back.\n"
        "#\n"
        "# Each entry: {name: display name, source: greenhouse|lever|ashby|smartrecruiters|recruitee|workday, token: board token/slug}\n"
    )
    with open(settings.COMPANIES_CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(header)
        yaml.safe_dump(companies, f, sort_keys=False, allow_unicode=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--full-rewrite",
        action="store_true",
        help="Discard existing companies.yaml entirely and regenerate from upstream data only",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    listings = fetch_listings()
    detected = build_companies(listings)
    logger.info("mapped %d companies to a supported ATS", len(detected))

    if args.full_rewrite:
        companies = detected
    else:
        existing = load_existing_companies()
        excluded_names = load_excluded_names()
        companies = merge_companies(existing, detected, excluded_names)

    write_companies(companies)
    print(f"Wrote {len(companies)} companies to {settings.COMPANIES_CONFIG_PATH}")


if __name__ == "__main__":
    main()
