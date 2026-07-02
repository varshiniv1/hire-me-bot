"""Writes REPORT.md: every scored posting, including low scores that never
triggered a Discord notification. Run as part of every 3-hourly pipeline
workflow and committed back to the repo, so git history itself becomes a
timestamped log of every posting found (role, company, location, source
platform, application link, age) -- styled after SimplifyJobs' tracker
repos, which the pipeline's company list was originally seeded from."""

from hire_me_bot import settings
from hire_me_bot.db import postings_repo
from hire_me_bot.format_utils import compact_age_text

REPORT_PATH = settings.REPO_ROOT / "REPORT.md"

_SOURCE_LABELS = {
    "greenhouse": "Greenhouse",
    "lever": "Lever",
    "ashby": "Ashby",
    "smartrecruiters": "SmartRecruiters",
    "recruitee": "Recruitee",
    "workday": "Workday",
}


def _escape(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def _format_row(posting: dict) -> str:
    company = _escape(posting["company"])
    role = _escape(posting["title"])
    location = _escape(posting.get("location") or "-")
    source = _SOURCE_LABELS.get(posting.get("source"), posting.get("source", "-"))
    age = compact_age_text(posting.get("posted_at"))
    return (
        f"| {company} | {role} | {location} | {source} | {posting['status']} "
        f"| [Apply]({posting['url']}) | {age} |"
    )


def build_report(postings: list[dict]) -> str:
    lines = [
        "# Job Postings Report",
        "",
        f"{len(postings)} postings tracked.",
        "",
        "| Company | Role | Location | Source | Status | Application | Age |",
        "|---|---|---|---|---|---|---|",
    ]
    lines.extend(_format_row(p) for p in postings)
    return "\n".join(lines) + "\n"


def main() -> None:
    postings = postings_repo.get_all_ordered()
    report = build_report(postings)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Wrote {len(postings)} postings to {REPORT_PATH}")


if __name__ == "__main__":
    main()
