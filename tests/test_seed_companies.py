import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from seed_companies import build_companies, detect_source_and_token, merge_companies  # noqa: E402


def test_greenhouse_url():
    assert detect_source_and_token(
        "https://job-boards.greenhouse.io/truveta/jobs/5696523004"
    ) == ("greenhouse", "truveta")


def test_greenhouse_legacy_domain():
    assert detect_source_and_token(
        "https://boards.greenhouse.io/acme/jobs/123"
    ) == ("greenhouse", "acme")


def test_lever_url():
    assert detect_source_and_token(
        "https://jobs.lever.co/thinkahead/ea0c65d1-dd6b-4f68-8abb-2bacebbd98a1"
    ) == ("lever", "thinkahead")


def test_ashby_url_with_encoded_space():
    assert detect_source_and_token(
        "https://jobs.ashbyhq.com/Citizen%20Health/0db9efc6-cdc3-44c6-a93a-59a57808e451/application"
    ) == ("ashby", "Citizen Health")


def test_smartrecruiters_url():
    assert detect_source_and_token(
        "https://jobs.smartrecruiters.com/Visa/615efbc7-5ef9-4dc3-b65a-cf364e55674e?dcr_ci=Visa"
    ) == ("smartrecruiters", "Visa")


def test_recruitee_url():
    assert detect_source_and_token(
        "https://1x.recruitee.com/o/compliance-testing-technician"
    ) == ("recruitee", "1x")


def test_workday_url():
    assert detect_source_and_token(
        "https://globalhr.wd5.myworkdayjobs.com/rec_rtx_ext_gateway/job/MA133/XMLNAME-abc"
    ) == ("workday", "globalhr/wd5/rec_rtx_ext_gateway")


def test_unsupported_domain_returns_none():
    assert detect_source_and_token("https://amazon.jobs/en/jobs/123") is None
    assert detect_source_and_token("https://jobs.apple.com/en-us/details/123") is None


def test_build_companies_strips_whitespace_from_company_name():
    listings = [{"company_name": " Acme ", "url": "https://jobs.lever.co/acme/1"}]
    companies = build_companies(listings)
    assert companies == [{"name": "Acme", "source": "lever", "token": "acme"}]


def test_build_companies_picks_majority_source_per_company():
    listings = [
        {"company_name": "Acme", "url": "https://jobs.lever.co/acme/1"},
        {"company_name": "Acme", "url": "https://jobs.lever.co/acme/2"},
        {"company_name": "Acme", "url": "https://job-boards.greenhouse.io/acme-old/3"},
        {"company_name": "Beta", "url": "https://amazon.jobs/en/jobs/1"},
    ]
    companies = build_companies(listings)
    assert companies == [{"name": "Acme", "source": "lever", "token": "acme"}]


def test_merge_adds_new_company_not_already_present():
    existing = [{"name": "Acme", "source": "lever", "token": "acme"}]
    detected = [
        {"name": "Acme", "source": "lever", "token": "acme"},
        {"name": "Beta", "source": "greenhouse", "token": "beta"},
    ]
    merged = merge_companies(existing, detected, excluded_names=set())
    assert merged == [
        {"name": "Acme", "source": "lever", "token": "acme"},
        {"name": "Beta", "source": "greenhouse", "token": "beta"},
    ]


def test_merge_never_removes_or_modifies_existing_entries():
    # Simulates a hand-renamed/hand-edited existing entry -- merge must
    # preserve it exactly even if upstream now reports something different
    # for the same (source, token).
    existing = [{"name": "Acme Corp (Renamed)", "source": "lever", "token": "acme"}]
    detected = [{"name": "Acme", "source": "lever", "token": "acme"}]
    merged = merge_companies(existing, detected, excluded_names=set())
    assert merged == [{"name": "Acme Corp (Renamed)", "source": "lever", "token": "acme"}]


def test_merge_skips_excluded_company_names():
    existing = []
    detected = [{"name": "Sonsoft", "source": "smartrecruiters", "token": "sonsoft"}]
    merged = merge_companies(existing, detected, excluded_names={"sonsoft"})
    assert merged == []


def test_merge_excluded_names_case_insensitive():
    existing = []
    detected = [{"name": "SONSOFT", "source": "smartrecruiters", "token": "sonsoft"}]
    merged = merge_companies(existing, detected, excluded_names={"sonsoft"})
    assert merged == []


def test_merge_sorts_by_name_case_insensitive():
    existing = [{"name": "zebra co", "source": "lever", "token": "zebra"}]
    detected = [{"name": "Acme", "source": "greenhouse", "token": "acme"}]
    merged = merge_companies(existing, detected, excluded_names=set())
    assert [c["name"] for c in merged] == ["Acme", "zebra co"]
