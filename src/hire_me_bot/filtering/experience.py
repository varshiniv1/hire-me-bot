import re

# Captures the leading (minimum) number, and -- for a "N-M years" range --
# the upper bound too, in "N years of ... experience", "N+ years ...
# experience", or "N-M years ... experience" -- e.g. "3-5 years of
# professional experience" -> (3, 5), "8+ years of ... experience,
# including 3+ years in a technical leadership role" -> (8, None) (the
# first match is enough to flag it; a second phrase like "3+ years in a
# leadership role" without the word "experience" nearby isn't required to
# also match). Requires "experience" within a short window after "years"
# so unrelated mentions ("founded 10 years ago") don't false-positive.
_YOE_RE = re.compile(
    r"(\d+)\+?\s*(?:-\s*(\d+)\+?\s*)?\s*years?\s+(?:of\s+)?(?:[a-zA-Z,/&'\s-]{0,40}?)experience",
    re.IGNORECASE,
)


def min_years_required(text: str | None) -> list[int]:
    if not text:
        return []
    return [int(m.group(1)) for m in _YOE_RE.finditer(text)]


def _effective_years_required(text: str | None) -> list[int]:
    """Like min_years_required, but for a "N-M years" range uses the upper
    bound M -- a strict cap must reject e.g. "1-3 years of experience" even
    though the range's minimum (1) is within cap, since the role is openly
    asking for candidates up to 3 years in."""
    if not text:
        return []
    results = []
    for m in _YOE_RE.finditer(text):
        lo = int(m.group(1))
        hi = int(m.group(2)) if m.group(2) else lo
        results.append(max(lo, hi))
    return results


def requires_too_much_experience(text: str | None, max_years: int = 2) -> bool:
    """True if any "N years experience" mention in text states a
    requirement above max_years -- e.g. "3-5 years of experience" or
    "1-3 years of experience" (upper bound 3) with max_years=2."""
    return any(years > max_years for years in _effective_years_required(text))
