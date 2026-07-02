import re

# Captures the leading (minimum) number in "N years of ... experience",
# "N+ years ... experience", or "N-M years ... experience" -- e.g. "3-5
# years of professional experience" -> 3, "8+ years of ... experience,
# including 3+ years in a technical leadership role" -> 8 (the first
# match is enough to flag it; a second phrase like "3+ years in a
# leadership role" without the word "experience" nearby isn't required to
# also match). Requires "experience" within a short window after "years"
# so unrelated mentions ("founded 10 years ago") don't false-positive.
_YOE_RE = re.compile(
    r"(\d+)\+?\s*(?:-\s*\d+\+?\s*)?\s*years?\s+(?:of\s+)?(?:[a-zA-Z,/&\s]{0,40}?)experience",
    re.IGNORECASE,
)


def min_years_required(text: str | None) -> list[int]:
    if not text:
        return []
    return [int(m.group(1)) for m in _YOE_RE.finditer(text)]


def requires_too_much_experience(text: str | None, max_years: int = 2) -> bool:
    """True if any "N years experience" mention in text states a minimum
    above max_years -- e.g. "3-5 years of experience" with max_years=2."""
    return any(years > max_years for years in min_years_required(text))
