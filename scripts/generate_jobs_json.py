"""Regenerates docs/jobs.json for the GitHub Pages job-browser page
(docs/jobs.html) -- a styled, tabbed (Internships / Full-Time) table view,
since a plain .md file can't render clickable Apply buttons the way a real
webpage can. Uses its own, wider freshness window (settings.JOBS_MAX_AGE_DAYS)
than Discord notifications and REPORT.md (settings.NOTIFY_MAX_AGE_DAYS),
plus only postings you haven't already acted on -- once you mark something
applied (via the page's button or track.py), it drops out here even if it's
still within the freshness window."""

import json

from hire_me_bot import settings
from hire_me_bot.db import postings_repo
from hire_me_bot.filtering.keywords import is_internship_title
from hire_me_bot.format_utils import SOURCE_LABELS, compact_age_text

JOBS_PATH = settings.REPO_ROOT / "docs" / "jobs.json"


def _to_entry(posting: dict) -> dict:
    return {
        "id": posting["id"],
        "company": posting["company"],
        "role": posting["title"],
        "location": posting.get("location") or "-",
        "source": SOURCE_LABELS.get(posting.get("source"), posting.get("source", "-")),
        "status": posting["status"],
        "url": posting["url"],
        "age": compact_age_text(posting.get("posted_at")),
        "is_internship": is_internship_title(posting["title"]),
    }


def main() -> None:
    postings = postings_repo.get_recent_not_applied(settings.JOBS_MAX_AGE_DAYS)
    entries = [_to_entry(p) for p in postings]
    JOBS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JOBS_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
    print(f"Wrote {len(entries)} postings to {JOBS_PATH}")


if __name__ == "__main__":
    main()
