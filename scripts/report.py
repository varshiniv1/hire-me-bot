"""Writes REPORT.md: every scored posting, including low scores that never
triggered a Discord notification. Run as part of every 3-hourly pipeline
workflow and committed back to the repo, so git history itself becomes a
timestamped log of every posting found (title, company, location, posted
date, age, application link) -- similar to how SimplifyJobs' tracker repos
work."""

from hire_me_bot import settings
from hire_me_bot.db import postings_repo
from hire_me_bot.format_utils import posted_days_ago_text

REPORT_PATH = settings.REPO_ROOT / "REPORT.md"


def _escape(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def _format_row(posting: dict) -> str:
    score = posting["fit_score"] if posting["fit_score"] is not None else "-"
    posted_at = posting.get("posted_at")
    posted_date = posted_at[:10] if posted_at else "-"
    age = posted_days_ago_text(posted_at).removeprefix("Posted ")
    company = _escape(posting["company"])
    title = _escape(posting["title"])
    location = _escape(posting.get("location") or "-")
    return (
        f"| {company} | {title} | {location} | {posted_date} | {age} "
        f"| {score} | {posting['status']} | [apply]({posting['url']}) |"
    )


def build_report(postings: list[dict]) -> str:
    lines = [
        "# Job Postings Report",
        "",
        f"{len(postings)} postings tracked.",
        "",
        "| Company | Title | Location | Posted | Age | Score | Status | Link |",
        "|---|---|---|---|---|---|---|---|",
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
