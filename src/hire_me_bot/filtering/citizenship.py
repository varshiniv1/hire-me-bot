import re

# Scoped narrowly to actual CITIZENSHIP requirements -- "U.S. Citizen",
# "citizenship required" -- not the much more common (and much weaker)
# "authorized to work in the US" / "no visa sponsorship" language, which
# international students/visa holders can still satisfy. Conflating the two
# would over-filter a huge fraction of postings that don't actually require
# citizenship.
_CITIZENSHIP_RE = re.compile(
    r"\bu\.?s\.?\s+citizen(?:ship|s)?\b(?!\s+and\s+immigration\s+services)"
    r"|\bunited states citizen(?:ship|s)?\b"
    r"|\bamerican citizen(?:ship|s)?\b"
    r"|\bcitizenship\s+(?:is\s+)?required\b"
    r"|\bmust be a\s+(?:u\.?s\.?|united states)\s+citizen\b",
    re.IGNORECASE,
)

# "No U.S. citizenship required" / "does not require citizenship" should
# NOT be excluded -- same negation-handling pattern as filtering/clearance.py.
_NO_CITIZENSHIP_RE = re.compile(
    r"\b(?:no|not|without"
    r"|does\s+not\s+require|doesn'?t\s+require)\s+"
    r"(?:[a-z.\s]{0,20})?citizenship",
    re.IGNORECASE,
)


def requires_citizenship(text: str | None) -> bool:
    if not text:
        return False
    if not _CITIZENSHIP_RE.search(text):
        return False
    return not _NO_CITIZENSHIP_RE.search(text)
