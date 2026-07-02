from hire_me_bot import pipeline
from hire_me_bot.connectors.base import Posting


def test_unknown_source_is_skipped_not_an_error():
    company = {"name": "BigCo", "source": "some_future_ats", "token": "bigco"}
    assert pipeline._fetch_company(company) == []


def test_all_six_sources_are_registered():
    assert set(pipeline.CONNECTOR_CLASSES.keys()) == {
        "greenhouse",
        "lever",
        "ashby",
        "smartrecruiters",
        "recruitee",
        "workday",
    }


def test_connector_exception_is_caught_and_logged(monkeypatch):
    class ExplodingConnector:
        def __init__(self, company, token):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def fetch(self):
            raise RuntimeError("boom")

    monkeypatch.setitem(pipeline.CONNECTOR_CLASSES, "greenhouse", ExplodingConnector)
    company = {"name": "Flaky", "source": "greenhouse", "token": "flaky"}

    # Should not raise -- one company's failure can't take down the whole run.
    assert pipeline._fetch_company(company) == []


def test_keyword_filter_applied_to_fetched_postings(monkeypatch):
    postings = [
        Posting("greenhouse", "Acme", "1", "Software Engineer Intern", "Austin, TX", "https://x/1", "desc", None),
        Posting("greenhouse", "Acme", "2", "Sales Account Executive", "Austin, TX", "https://x/2", "desc", None),
    ]

    class FakeConnector:
        def __init__(self, company, token):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def fetch(self):
            return postings

    monkeypatch.setitem(pipeline.CONNECTOR_CLASSES, "greenhouse", FakeConnector)
    company = {"name": "Acme", "source": "greenhouse", "token": "acme"}

    result = pipeline._fetch_company(company)

    assert len(result) == 1
    assert result[0].title == "Software Engineer Intern"


def test_non_usa_postings_are_filtered_out(monkeypatch):
    postings = [
        Posting("greenhouse", "Acme", "1", "Software Engineer Intern", "Austin, TX", "https://x/1", "desc", None),
        Posting("greenhouse", "Acme", "2", "Software Engineer Intern", "Dublin", "https://x/2", "desc", None),
    ]

    class FakeConnector:
        def __init__(self, company, token):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def fetch(self):
            return postings

    monkeypatch.setitem(pipeline.CONNECTOR_CLASSES, "greenhouse", FakeConnector)
    company = {"name": "Acme", "source": "greenhouse", "token": "acme"}

    result = pipeline._fetch_company(company)

    assert len(result) == 1
    assert result[0].location == "Austin, TX"


def test_clearance_required_postings_are_filtered_out(monkeypatch):
    postings = [
        Posting("greenhouse", "Acme", "1", "Software Engineer Intern", "Austin, TX", "https://x/1", "desc", None),
        Posting(
            "greenhouse", "Acme", "2", "Software Engineer 1 (Clearance Required)",
            "Austin, TX", "https://x/2", "desc", None,
        ),
        Posting(
            "greenhouse", "Acme", "3", "Software Engineer 1", "Austin, TX", "https://x/3",
            "Must have an active security clearance to be considered.", None,
        ),
    ]

    class FakeConnector:
        def __init__(self, company, token):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def fetch(self):
            return postings

    monkeypatch.setitem(pipeline.CONNECTOR_CLASSES, "greenhouse", FakeConnector)
    company = {"name": "Acme", "source": "greenhouse", "token": "acme"}

    result = pipeline._fetch_company(company)

    assert len(result) == 1
    assert result[0].external_id == "1"


def test_citizenship_required_postings_are_filtered_out(monkeypatch):
    postings = [
        Posting(
            "greenhouse", "Acme", "1", "Software Engineer I", "Austin, TX", "https://x/1",
            "Must be authorized to work in the United States.", None,
        ),
        Posting(
            "greenhouse", "Acme", "2", "Software Engineer II", "Austin, TX", "https://x/2",
            "US Citizenship Required.", None,
        ),
        Posting(
            "greenhouse", "Acme", "3", "Software Engineer III", "Austin, TX", "https://x/3",
            "Must be a US Citizen to apply.", None,
        ),
    ]

    class FakeConnector:
        def __init__(self, company, token):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def fetch(self):
            return postings

    monkeypatch.setitem(pipeline.CONNECTOR_CLASSES, "greenhouse", FakeConnector)
    company = {"name": "Acme", "source": "greenhouse", "token": "acme"}

    result = pipeline._fetch_company(company)

    assert len(result) == 1
    assert result[0].external_id == "1"


def test_too_much_experience_postings_are_filtered_out(monkeypatch):
    postings = [
        Posting(
            "greenhouse", "Acme", "1", "Software Engineer I", "Austin, TX", "https://x/1",
            "0-2 years of experience required.", None,
        ),
        Posting(
            "greenhouse", "Acme", "2", "Software Engineer II", "Austin, TX", "https://x/2",
            "3-5 years of professional experience in software development.", None,
        ),
        Posting(
            "greenhouse", "Acme", "3", "Software Engineer III", "Austin, TX", "https://x/3",
            "8+ years of software development experience, including 3+ years in a technical leadership role.",
            None,
        ),
    ]

    class FakeConnector:
        def __init__(self, company, token):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def fetch(self):
            return postings

    monkeypatch.setitem(pipeline.CONNECTOR_CLASSES, "greenhouse", FakeConnector)
    company = {"name": "Acme", "source": "greenhouse", "token": "acme"}

    result = pipeline._fetch_company(company)

    assert len(result) == 1
    assert result[0].external_id == "1"
