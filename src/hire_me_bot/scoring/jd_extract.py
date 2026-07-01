import re

from hire_me_bot import settings

# Matches a "Requirements:"-style header anywhere in the text (JDs vary wildly
# in formatting -- not every posting has it as its own line).
_HEADER_RE = re.compile(
    r"(requirements?|qualifications?|minimum qualifications?|"
    r"what you.?ll need|what we.?re looking for|who you are)\s*:?",
    re.IGNORECASE,
)


def extract_requirements(description: str) -> str:
    """Pull just the requirements/qualifications section out of a full job
    description to keep Claude's prompt cheap. Falls back to a plain
    truncation if no recognizable section header is found."""
    if not description:
        return ""
    match = _HEADER_RE.search(description)
    if not match:
        return description[: settings.JD_FALLBACK_TRUNCATE_CHARS]
    section = description[match.end() :].strip()
    return section[: settings.JD_FALLBACK_TRUNCATE_CHARS]
