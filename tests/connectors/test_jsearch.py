from hire_me_bot.connectors import jsearch

RAW_POSTING = {
    "job_id": "abc123",
    "employer_name": "Acme Corp",
    "job_title": "Software Engineer, New Grad",
    "job_apply_link": "https://acme.com/careers/12345",
    "job_description": "Join our team as a new grad software engineer.",
    "job_city": "Austin",
    "job_state": "TX",
    "job_country": "US",
    "job_posted_at_datetime_utc": "2026-06-30T12:00:00Z",
}


def test_normalize_valid_posting():
    posting = jsearch.normalize(RAW_POSTING)
    assert posting is not None
    assert posting.source == "jsearch"
    assert posting.company == "Acme Corp"
    assert posting.external_id == "abc123"
    assert posting.title == "Software Engineer, New Grad"
    assert posting.location == "Austin, TX, USA"
    assert posting.url == "https://acme.com/careers/12345"
    assert posting.posted_at is not None


def test_normalize_missing_required_fields_returns_none():
    assert jsearch.normalize({**RAW_POSTING, "job_apply_link": None}) is None
    assert jsearch.normalize({**RAW_POSTING, "job_title": None}) is None
    assert jsearch.normalize({**RAW_POSTING, "employer_name": None}) is None
    assert jsearch.normalize({**RAW_POSTING, "job_id": None}) is None


def test_normalize_skips_non_usa_country():
    assert jsearch.normalize({**RAW_POSTING, "job_country": "IN"}) is None
    assert jsearch.normalize({**RAW_POSTING, "job_country": None}) is None


def test_normalize_skips_result_already_covered_by_direct_ats_connector():
    # A JSearch result whose apply link resolves to a Greenhouse/Lever/etc.
    # board should be skipped -- the direct connector already covers it
    # with more complete data.
    raw = {**RAW_POSTING, "job_apply_link": "https://job-boards.greenhouse.io/acme/jobs/12345"}
    assert jsearch.normalize(raw) is None


def test_normalize_location_falls_back_to_bare_usa():
    raw = {**RAW_POSTING, "job_city": None, "job_state": None}
    posting = jsearch.normalize(raw)
    assert posting.location == "USA"


def test_normalize_missing_posted_at_is_none():
    raw = {**RAW_POSTING, "job_posted_at_datetime_utc": None}
    posting = jsearch.normalize(raw)
    assert posting.posted_at is None


def test_fetch_jsearch_postings_noop_without_api_key(monkeypatch):
    monkeypatch.setattr(jsearch.settings, "RAPIDAPI_KEY", None)
    assert jsearch.fetch_jsearch_postings() == []


def test_fetch_jsearch_postings_aggregates_across_queries(monkeypatch):
    monkeypatch.setattr(jsearch.settings, "RAPIDAPI_KEY", "fake-key")
    monkeypatch.setattr(jsearch, "SEARCH_QUERIES", ["query one", "query two"])

    def fake_fetch_query(client, query):
        return [RAW_POSTING]

    monkeypatch.setattr(jsearch, "_fetch_query", fake_fetch_query)

    postings = jsearch.fetch_jsearch_postings()
    assert len(postings) == 2


def test_fetch_jsearch_postings_skips_failed_query(monkeypatch):
    monkeypatch.setattr(jsearch.settings, "RAPIDAPI_KEY", "fake-key")
    monkeypatch.setattr(jsearch, "SEARCH_QUERIES", ["good query", "bad query"])

    def fake_fetch_query(client, query):
        if query == "bad query":
            raise RuntimeError("boom")
        return [RAW_POSTING]

    monkeypatch.setattr(jsearch, "_fetch_query", fake_fetch_query)

    # Should not raise -- one failed query can't take down the whole fetch.
    postings = jsearch.fetch_jsearch_postings()
    assert len(postings) == 1
