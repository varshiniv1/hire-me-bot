import httpx

from hire_me_bot.connectors.smartrecruiters import SmartRecruitersConnector

LIST_PAGE_1 = {
    "totalFound": 1,
    "content": [{"id": "999", "name": "Software Engineer, New Grad"}],
}

DETAIL = {
    "id": "999",
    "name": "Software Engineer, New Grad",
    "location": {"city": "Austin", "region": "TX", "country": "US"},
    "applyUrl": "https://careers.acme.com/jobs/999?oga=true",
    "postingUrl": "https://careers.acme.com/jobs/999",
    "releasedDate": "2026-06-24T10:00:11.853Z",
    "jobAd": {
        "sections": {
            "jobDescription": {"text": "<p>About the role.</p>"},
            "qualifications": {"text": "<p>Requirements: Java.</p>"},
        }
    },
}


def _client_with_fixture():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/postings/999"):
            return httpx.Response(200, json=DETAIL)
        assert request.url.params["offset"] == "0"
        return httpx.Response(200, json=LIST_PAGE_1)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_and_normalize():
    connector = SmartRecruitersConnector("Acme", "acme", http_client=_client_with_fixture())
    postings = connector.fetch()

    assert len(postings) == 1
    posting = postings[0]
    assert posting.source == "smartrecruiters"
    assert posting.external_id == "999"
    assert posting.title == "Software Engineer, New Grad"
    assert posting.location == "Austin, TX, US"
    # postingUrl preferred over applyUrl (which skips straight to the
    # application form via its ?oga=true param, past the JD).
    assert posting.url == "https://careers.acme.com/jobs/999"
    assert "Requirements" in posting.description
    assert posting.posted_at is not None


def test_clearance_required_summary_is_filtered_before_detail_fetch():
    list_with_clearance_role = {
        "totalFound": 1,
        "content": [{"id": "888", "name": "Software Engineer 1 (Clearance Required)"}],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/postings/888"):
            raise AssertionError("should not fetch detail for a clearance-required summary")
        return httpx.Response(200, json=list_with_clearance_role)

    connector = SmartRecruitersConnector(
        "Acme", "acme", http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    assert connector.fetch() == []


def test_falls_back_to_apply_url_when_posting_url_missing():
    detail_without_posting_url = dict(DETAIL)
    del detail_without_posting_url["postingUrl"]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/postings/999"):
            return httpx.Response(200, json=detail_without_posting_url)
        return httpx.Response(200, json=LIST_PAGE_1)

    connector = SmartRecruitersConnector(
        "Acme", "acme", http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    posting = connector.fetch()[0]
    assert posting.url == "https://careers.acme.com/jobs/999?oga=true"
