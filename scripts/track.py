"""CLI for updating a posting's application status.

    track.py <fuzzy-company-name> <status>   -- fast path, you know what you want
    track.py                                 -- browse not-yet-applied postings

`status` accepts the full word or shorthand: a=applied, i=interviewing,
r=rejected, o=offer.
"""

import sys

from hire_me_bot.db import postings_repo

STATUS_ALIASES = {
    "a": "applied",
    "applied": "applied",
    "i": "interviewing",
    "interviewing": "interviewing",
    "r": "rejected",
    "rejected": "rejected",
    "o": "offer",
    "offer": "offer",
}


def resolve_status(raw: str) -> str | None:
    return STATUS_ALIASES.get(raw.strip().lower())


def print_update(posting: dict, status: str) -> None:
    print(f"✅ {posting['company']} — {posting['title']} → {status}")


def _pick_number(prompt: str, count: int) -> int | None:
    choice = input(prompt).strip()
    if not choice:
        return None
    try:
        idx = int(choice) - 1
    except ValueError:
        print("Not a number, cancelled.")
        return None
    if not (0 <= idx < count):
        print("Out of range, cancelled.")
        return None
    return idx


def disambiguate(matches: list[dict]) -> dict | None:
    print("Multiple matches:")
    for i, m in enumerate(matches, start=1):
        print(f"  {i}. {m['company']} — {m['title']} ({m['status']})")
    idx = _pick_number("Pick a number (or blank to cancel): ", len(matches))
    return matches[idx] if idx is not None else None


def run_arg_mode(fuzzy_name: str, raw_status: str) -> None:
    status = resolve_status(raw_status)
    if status is None:
        print(f"Unknown status '{raw_status}'. Use applied/interviewing/rejected/offer or a/i/r/o.")
        return

    matches = postings_repo.search_by_company(fuzzy_name)
    if not matches:
        print(f"No postings found matching '{fuzzy_name}'.")
        return

    posting = matches[0] if len(matches) == 1 else disambiguate(matches)
    if posting is None:
        return

    postings_repo.update_status(posting["id"], status)
    print_update(posting, status)


def run_interactive_mode() -> None:
    postings = postings_repo.get_not_applied()
    if not postings:
        print("Nothing to update -- no postings are currently not_applied.")
        return

    print("Not-yet-applied postings:")
    for i, p in enumerate(postings, start=1):
        print(f"  {i}. {p['company']} — {p['title']}")

    idx = _pick_number("Pick a number (or blank to cancel): ", len(postings))
    if idx is None:
        return
    posting = postings[idx]

    print("Status: [a]pplied / [i]nterviewing / [r]ejected / [o]ffer")
    raw_status = input("Status: ")
    status = resolve_status(raw_status)
    if status is None:
        print(f"Unknown status '{raw_status}'.")
        return

    postings_repo.update_status(posting["id"], status)
    print_update(posting, status)


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if len(args) == 0:
        run_interactive_mode()
    elif len(args) == 2:
        run_arg_mode(args[0], args[1])
    else:
        print("Usage: track.py [<company> <status>]")
        sys.exit(1)


if __name__ == "__main__":
    main()
