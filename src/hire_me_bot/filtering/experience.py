import re

# Captures the leading (minimum) number, and -- for a "N-M years" range --
# the upper bound too, in "N years of ... experience", "N+ years ...
# experience", or "N-M years ... experience" -- e.g. "3-5 years of
# professional experience" -> (3, 5), "8+ years of ... experience,
# including 3+ years in a technical leadership role" -> (8, None) (the
# first match is enough to flag it; a second phrase like "3+ years in a
# leadership role" without the word "experience" nearby isn't required to
# also match). Requires "experience" within a short window after "years" so
# unrelated mentions ("founded 10 years ago") don't false-positive -- the
# filler between "years ... of" and "experience" excludes newlines
# specifically (not just periods -- "." was never actually excluded, \s
# matches \n too) so the match can't bridge across separate bullets/
# sections in a job description. That distinction mattered in practice: a
# wide-open version of this filler (still newline-permissive) matched
# DreamWorks/NBCUniversal's "18 years or older[...]Desired
# Characteristics\n\nExperience" as "18 years of experience" and Pebl's "3
# years of formal education [...]\n\n - Experience" as "3 years of
# experience" -- both false positives bridging unrelated bullets via a
# blank line. Newlines split description text into <br/>-separated bullets
# (see connectors/base.py's strip_html), so excluding them keeps a match
# confined to one bullet, which is exactly where a real "N years of X
# experience" phrase lives.
#
# The filler is otherwise wide (130 chars, letters/digits/comma/slash/amp/
# apostrophe/parens/space/tab/hyphen) to handle verbose single-bullet
# phrasing -- a real live posting (Amazon SDE II, job ID 10467411) needed
# this: "3+ years of non-internship professional software development
# experience" (49-char filler) and "2+ years of non-internship design or
# architecture (design patterns, reliability and scaling) of new and
# existing systems experience" (109-char filler, with parens/commas a
# narrower class wouldn't allow at all) both slipped through undetected
# before this was widened.
_YOE_RE = re.compile(
    r"(\d+)\+?[ \t]*(?:-[ \t]*(\d+)\+?[ \t]*)?[ \t]*years?[ \t]+(?:of[ \t]+)?(?:[a-zA-Z0-9,/&'()\ \t-]{0,130}?)experience",
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
