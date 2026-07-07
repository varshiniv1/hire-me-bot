"""CLI for recording a posting you applied to outside the crawled pipeline --
e.g. something found directly on Indeed/LinkedIn, which aren't scraped (see
README). Inserts it straight in as already-applied, so it shows up in the
Applied tab and the stats calendar without ever going through a connector.

    add_applied.py <company> <title> <url> [source]   -- fast path
    add_applied.py                                     -- prompts for each field

`source` defaults to "manual" if omitted.
"""

import sys

from hire_me_bot.db import postings_repo


def _prompt(label: str, required: bool = True) -> str:
    while True:
        value = input(f"{label}: ").strip()
        if value or not required:
            return value
        print(f"{label} is required.")


def add(company: str, title: str, url: str, source: str) -> None:
    try:
        posting = postings_repo.add_manual_applied(company, title, url, source)
    except Exception as exc:
        print(f"Couldn't add posting (already added this company/url before?): {exc}")
        return
    print(f"✅ Added {posting['company']} — {posting['title']} as applied.")


def run_interactive_mode() -> None:
    company = _prompt("Company")
    title = _prompt("Title")
    url = _prompt("Link")
    source = _prompt("Source (blank = manual)", required=False) or "manual"
    add(company, title, url, source)


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if len(args) == 0:
        run_interactive_mode()
    elif len(args) in (3, 4):
        company, title, url = args[0], args[1], args[2]
        source = args[3] if len(args) == 4 else "manual"
        add(company, title, url, source)
    else:
        print("Usage: add_applied.py [<company> <title> <url> [source]]")
        sys.exit(1)


if __name__ == "__main__":
    main()
