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
#
# Narrowed further per user request to: Software Engineer, SRE/Production
# Engineer, and Backend/Frontend/Full-Stack roles specifically -- "software"
# covers Software Engineer/Developer/Development Engineer plus the SWE/SDE
# abbreviations and SDET. A bare "Developer" is no longer sufficient on its
# own -- that used to catch things like "Salesforce Developer", "ServiceNow
# Developer", ".NET Developer", "React Developer", "Database Developer",
# which aren't the general SWE/backend/frontend/full-stack roles being
# targeted. "Developer" titles still pass if backend/frontend/full-stack is
# explicit in the title (e.g. "Backend Developer", "Full Stack Developer").
# Data Engineer, Machine Learning Engineer, and generic "programmer" remain
# excluded -- "programmer" in particular was a real false positive (a live
# run matched "CAM Programmer", which is CNC/manufacturing programming, not
# software).
TECH_TERMS = [
    r"\bsoftware\b",
    r"\bswe\b",
    r"\bsde\b",
    r"\bsdet\b",
    r"\bsite reliability\b",
    r"\bsre\b",
    r"\bproduction engineer(?:ing)?\b",
    r"\bback[- ]?end\b",
    r"\bfront[- ]?end\b",
    r"\bfull[- ]?stack\b",
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
    # "(?:er)?" catches "Leader"/"Technical Leader" too -- a real live example
    # ("Software Engineering Technical Leader") slipped through since "lead"
    # alone doesn't match inside "leader" (different word, same seniority).
    r"\blead(?:er)?\b",
    r"\barchitect\b",
    r"\bvp\b",
    r"\bhead of\b",
    # "developer"/"engineer" as a bare inclusion term also matches DevRel-style
    # titles that aren't actual SWE roles (e.g. "Developer Relations",
    # "Developer Advocate") -- exclude those explicitly.
    r"\brelations\b",
    r"\badvocate\b",
    # Per user request -- "Embedded Software Engineer" would otherwise pass
    # via the "software" TECH_TERM, but embedded/firmware work is a
    # different discipline than the general SWE/backend/frontend/full-stack
    # roles being targeted.
    r"\bembedded\b",
    r"\bfirmware\b",
    # Per user request -- "Scientific Software Engineer" would otherwise
    # pass via the "software" TECH_TERM, but these are typically
    # domain-science roles (compilers/emulation for quantum hardware, etc.),
    # not general SWE/backend/frontend/full-stack.
    r"\bscientific\b",
    # Per user request -- cap at SDE/SWE/Engineer II (0-2 YoE); III+ and
    # L3+/Level 3+ (common internal leveling at Google/Amazon-style orgs)
    # signal 3+ years even without the word "senior" in the title. \b on
    # both sides means "iii"/"iv" only match as standalone tokens (e.g.
    # "Engineer III", "SDE IV"), not mid-word substrings like "Innovative".
    r"\b(?:sde|swe|engineer|developer)\s*(?:iii|iv|v|3|4|5|6|7)\b",
    r"\bl[3-9]\b",
    r"\blevel\s*[3-9]\b",
    # Per user request -- a sales role whose title happens to name a
    # software product (e.g. Bosch's "Sales Executive - Mobility Software &
    # Services") otherwise passes via the bare "software" TECH_TERM even
    # though it's not an engineering role at all.
    r"\bsales\b",
]

_TECH_RE = re.compile("|".join(TECH_TERMS), re.IGNORECASE)
_EXCLUSION_RE = re.compile("|".join(EXCLUSION_TERMS), re.IGNORECASE)

# Subset of CAREER_STAGE_TERMS that specifically signals an internship/co-op
# (as opposed to "new grad"/"entry level", which are full-time framing) --
# used to split postings into Internships vs Full-Time for reporting.
# Apprenticeship/Fellowship/Residency are grad-friendly functional
# equivalents some companies use instead of "internship" -- bucketed the
# same way (e.g. "Software Engineering Residency", "Engineering
# Fellowship").
_INTERNSHIP_TERMS = [
    r"\bintern(?:ship)?s?\b",
    r"\bco[- ]?op\b",
    r"\bapprentice(?:ship)?s?\b",
    r"\bfellow(?:ship)?s?\b",
    r"\bresidency\b",
]
_INTERNSHIP_RE = re.compile("|".join(_INTERNSHIP_TERMS), re.IGNORECASE)


def passes_keyword_filter(title: str) -> bool:
    if not title:
        return False
    if _EXCLUSION_RE.search(title):
        return False
    return bool(_TECH_RE.search(title))


def is_internship_title(title: str) -> bool:
    return bool(_INTERNSHIP_RE.search(title or ""))
