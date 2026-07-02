import re

# Matches an affirmative clearance requirement -- title patterns like
# "(Clearance Required)" (common at defense contractors: RTX, L3Harris,
# Sierra Space) and JD-body mentions of specific clearance types/levels.
_CLEARANCE_RE = re.compile(
    r"\bclearance required\b"
    r"|\bsecurity clearance\b"
    r"|\bts/sci\b"
    r"|\btop secret\b"
    r"|\bsecret clearance\b"
    r"|\bdod clearance\b"
    r"|\bpublic trust clearance\b"
    r"|\bactive clearance\b"
    r"|\bclearance eligib",
    re.IGNORECASE,
)

# "No security clearance required" / "does not require a clearance" should
# NOT be excluded -- crude negation check for the common phrasings.
_NO_CLEARANCE_RE = re.compile(
    r"\b(?:no|not|without"
    r"|does\s+not\s+require|doesn'?t\s+require"
    r"|do\s+not\s+need|don'?t\s+need)\s+"
    r"(?:an?\s+)?(?:active\s+|current\s+)?(?:security\s+)?clearance",
    re.IGNORECASE,
)


def requires_clearance(text: str | None) -> bool:
    if not text:
        return False
    if not _CLEARANCE_RE.search(text):
        return False
    return not _NO_CLEARANCE_RE.search(text)
