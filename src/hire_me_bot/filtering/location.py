import re

# Real location strings seen across connectors: Workday uses "US-TX-RICHARDSON-..."
# / "GB-PLY-PLYMOUTH-..." (ISO-country-code prefix), Greenhouse/Ashby/Lever use
# plain text like "New York, NY (HQ)", "Dublin", "Remote", "N/A".
#
# No positive-match "N/A"/bare "Remote"/foreign-city text -> excluded by
# default. That's a deliberate choice: better to miss an ambiguous listing
# than show European/APAC roles to someone explicitly looking for the US.
_US_STATE_ABBREVIATIONS = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL",
    "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT",
    "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
}

_EXPLICIT_US_RE = re.compile(r"\bU\.?S\.?A?\.?\b|\bUnited States\b", re.IGNORECASE)
_WORKDAY_US_PREFIX_RE = re.compile(r"^US-")
_STATE_SUFFIX_RE = re.compile(r"[,-]\s*([A-Z]{2})\b(?!\w)")

# SmartRecruiters formats locations as "City, Region, country_code" with a
# lowercase trailing ISO country code -- e.g. "Chennai, TN, in",
# "Pomerode, SC, br", "Madrid, MD, es". The region code can collide with a US
# state abbreviation (India's Tamil Nadu "TN" vs Tennessee "TN", Brazil's
# Santa Catarina "SC" vs South Carolina "SC", Spain's Madrid "MD" vs
# Maryland "MD", Spain's Cataluña "CT" vs Connecticut "CT", Netherlands'
# Utrecht "UT" vs Utah "UT") -- a live run had 41 non-US postings pass
# incorrectly because of this. The trailing lowercase country code is an
# unambiguous signal and takes priority over the state-abbreviation guess.
_TRAILING_COUNTRY_CODE_RE = re.compile(r",\s*([a-z]{2})\s*$")


def is_usa_location(location: str | None) -> bool:
    if not location:
        return False
    trailing_country = _TRAILING_COUNTRY_CODE_RE.search(location)
    if trailing_country and trailing_country.group(1) != "us":
        return False
    if _WORKDAY_US_PREFIX_RE.match(location):
        return True
    if _EXPLICIT_US_RE.search(location):
        return True
    for match in _STATE_SUFFIX_RE.finditer(location):
        if match.group(1) in _US_STATE_ABBREVIATIONS:
            return True
    return False
