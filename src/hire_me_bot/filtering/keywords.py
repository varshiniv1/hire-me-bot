import re

# Cheap, free pre-filter applied to every fetched posting's title before it's
# ever persisted or sent to Claude. Both internship AND new-grad/full-time
# roles should pass -- this isn't internship-only.
#
# A title must match a TECH_TERM to pass at all -- a bare "intern"/"new
# grad"/"campus" match used to be sufficient on its own, which meant literally
# any internship (Pharmacy Intern, Campus Recruiter, Operations Associate New
# Grad, ...) passed the filter. Caught live: a real pipeline run against the
# full company list returned ~21,000 "matching" postings, most of them
# non-technical roles at non-tech companies (e.g. CVS Health's pharmacy
# internships) that only matched because the title said "intern". Requiring
# an explicit software/tech signal fixes that; CAREER_STAGE_TERMS alone no
# longer passes anything.
#
# Every term is wrapped in \b...\b: without it "intern" matches inside
# "Internal Auditor" / "Internal Product Engineer" as a bare substring.
TECH_TERMS = [
    r"\bsoftware\b",
    r"\bswe\b",
    r"\bsde\b",
    r"\bsdet\b",
    r"\bprogrammer\b",
    r"\bdeveloper\b",
    r"\bcomputer science\b",
    r"\bdata engineer(?:ing)?\b",
    r"\bmachine learning engineer\b",
    r"\bml engineer\b",
]

# Internship/new-grad framing -- informational, and combined with a
# TECH_TERM in the title is how a posting actually passes (see below), but
# never sufficient on its own anymore.
CAREER_STAGE_TERMS = [
    r"\bintern(?:ship)?s?\b",
    r"\bco[- ]?op\b",
    r"\bnew grad(?:uate)?\b",
    r"\buniversity grad(?:uate)?\b",
    r"\bcampus\b",
    r"\bentry[- ]level\b",
    r"\bearly career\b",
    r"\bearly[- ]in[- ]career\b",
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
    # "developer"/"engineer" as a bare inclusion term also matches DevRel-style
    # titles that aren't actual SWE roles (e.g. "Developer Relations",
    # "Developer Advocate") -- exclude those explicitly.
    r"\brelations\b",
    r"\badvocate\b",
]

_TECH_RE = re.compile("|".join(TECH_TERMS), re.IGNORECASE)
_EXCLUSION_RE = re.compile("|".join(EXCLUSION_TERMS), re.IGNORECASE)


def passes_keyword_filter(title: str) -> bool:
    if not title:
        return False
    if _EXCLUSION_RE.search(title):
        return False
    return bool(_TECH_RE.search(title))
