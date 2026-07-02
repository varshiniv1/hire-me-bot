"""Regenerates docs/applied.json -- every posting you've acted on (applied,
interviewing, rejected, offer), for the "Applied" tab on the GitHub Pages
job browser (docs/jobs.html) so you can review your own application
history including the date. Not age-limited, unlike jobs.json/REPORT.md."""

import json

from hire_me_bot import settings
from hire_me_bot.db import postings_repo
from hire_me_bot.format_utils import SOURCE_LABELS

APPLIED_PATH = settings.REPO_ROOT / "docs" / "applied.json"


def _to_entry(posting: dict) -> dict:
    return {
        "id": posting["id"],
        "company": posting["company"],
        "role": posting["title"],
        "location": posting.get("location") or "-",
        "source": SOURCE_LABELS.get(posting.get("source"), posting.get("source", "-")),
        "status": posting["status"],
        "url": posting["url"],
        "applied_at": posting.get("applied_at"),
    }


def main() -> None:
    postings = postings_repo.get_applied_history()
    entries = [_to_entry(p) for p in postings]
    APPLIED_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(APPLIED_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
    print(f"Wrote {len(entries)} applied postings to {APPLIED_PATH}")


if __name__ == "__main__":
    main()
