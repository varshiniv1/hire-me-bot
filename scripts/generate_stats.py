"""Regenerates docs/stats.json (applications-per-day, for the GitHub Pages
calendar). Run daily by .github/workflows/stats.yml; the workflow commits
the updated file back to the repo."""

import json

from hire_me_bot import settings
from hire_me_bot.db import postings_repo

STATS_PATH = settings.REPO_ROOT / "docs" / "stats.json"


def main() -> None:
    counts = postings_repo.get_applications_per_day()
    STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(counts, f, indent=2, sort_keys=True)
    print(f"Wrote {len(counts)} day(s) of application counts to {STATS_PATH}")


if __name__ == "__main__":
    main()
