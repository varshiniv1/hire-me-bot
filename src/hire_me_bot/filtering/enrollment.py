import re

# A lot of internship postings hard-require you to be a current student
# returning to campus afterward -- a disqualifier once you've graduated,
# regardless of an otherwise-perfect keyword/experience/location match.
# "Expected graduation" is included on its own: a graduated candidate has no
# such date to give, so the phrase itself (any date) presupposes you haven't
# graduated yet.
_ENROLLMENT_RE = re.compile(
    r"\bcurrently enrolled\b"
    r"|\bmust be enrolled\b"
    r"|\benrolled students?\b"
    r"|\bmust (?:be )?return(?:ing)? to (?:school|campus)\b"
    r"|\breturning to (?:school|campus)\b"
    r"|\bexpected graduation\b"
    r"|\bcurrently pursuing (?:an?\s+)?(?:bachelor|master|degree)\b",
    re.IGNORECASE,
)


def requires_current_enrollment(text: str | None) -> bool:
    if not text:
        return False
    return bool(_ENROLLMENT_RE.search(text))
