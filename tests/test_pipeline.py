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
        Posting("greenhouse", "Acme", "1", "Software Engineer Intern", None, "https://x/1", "desc", None),
        Posting("greenhouse", "Acme", "2", "Sales Account Executive", None, "https://x/2", "desc", None),
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
