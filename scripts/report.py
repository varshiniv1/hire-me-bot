"""Writes REPORT.md: every scored posting, including low scores that never
triggered a Discord notification. Run manually whenever you want the full
picture -- not part of the 3-hourly pipeline."""

from hire_me_bot import settings
from hire_me_bot.db import postings_repo

REPORT_PATH = settings.REPO_ROOT / "REPORT.md"


def _escape(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def _format_row(posting: dict) -> str:
    score = posting["fit_score"] if posting["fit_score"] is not None else "-"
    first_seen = posting["first_seen_at"][:10] if posting.get("first_seen_at") else "-"
    company = _escape(posting["company"])
    title = _escape(posting["title"])
    return f"| {company} | {title} | {score} | {posting['status']} | {first_seen} | [link]({posting['url']}) |"


def build_report(postings: list[dict]) -> str:
    lines = [
        "# Job Postings Report",
        "",
        f"{len(postings)} postings tracked.",
        "",
        "| Company | Title | Score | Status | First Seen | Link |",
        "|---|---|---|---|---|---|",
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
