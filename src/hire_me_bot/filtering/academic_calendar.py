import re

# Summer internship programs recruit ~6-9 months out and are aimed at
# students returning to campus afterward (see filtering/enrollment.py for the
# explicit-eligibility-language version of this same signal) -- excluded
# outright now that there's no "next school year" to return to. Matches an
# explicit "Summer 2026"/"Summer 2027"/... tag, or a bare "Summer
# Intern(ship)" mention with no year at all. Off-cycle/Fall/Winter/rolling/
# year-round programs (aimed at grads, not enrolled students) don't match
# this and are left alone.
_SUMMER_RE = re.compile(
    r"\bsummer\s*20[2-9]\d\b"
    r"|\bsummer\s+intern(?:ship)?\b",
    re.IGNORECASE,
)


def is_summer_locked(title: str | None, description: str | None = None) -> bool:
    """True if title/description tie the posting to the traditional summer
    academic-calendar internship cycle, as opposed to an off-cycle program
    open to recent grads."""
    return bool(_SUMMER_RE.search(title or "")) or bool(_SUMMER_RE.search(description or ""))
