import re

# Cheap, free pre-filter applied to every fetched posting's title before it's
# ever persisted or sent to Claude. Both internship AND new-grad/full-time
# roles should pass -- this isn't internship-only.
#
# Every term is wrapped in \b...\b: without it "intern" matches inside
# "Internal Auditor" / "Internal Product Engineer" as a bare substring.
INCLUSION_TERMS = [
    r"\bintern(?:ship)?s?\b",
    r"\bco[- ]?op\b",
    r"\bnew grad(?:uate)?\b",
    r"\buniversity grad(?:uate)?\b",
    r"\bcampus\b",
    r"\bentry[- ]level\b",
    r"\bearly career\b",
    r"\bearly[- ]in[- ]career\b",
    r"\bsoftware engineer\b",
    r"\bsoftware developer\b",
    r"\bswe\b",
    r"\bprogrammer\b",
    r"\bdeveloper\b",
]

EXCLUSION_TERMS = [
    r"\bsenior\b",
    r"\bsr\.?\b",
    r"\bstaff\b",
    r"\bprincipal\b",
    r"\bdistinguished\b",
    r"\bmanager\b",
    r"\bdirector\b",
    r"\blead\b",
    r"\barchitect\b",
    r"\bvp\b",
    r"\bhead of\b",
]

_INCLUSION_RE = re.compile("|".join(INCLUSION_TERMS), re.IGNORECASE)
_EXCLUSION_RE = re.compile("|".join(EXCLUSION_TERMS), re.IGNORECASE)


def passes_keyword_filter(title: str) -> bool:
    if not title:
        return False
    if _EXCLUSION_RE.search(title):
        return False
    return bool(_INCLUSION_RE.search(title))
