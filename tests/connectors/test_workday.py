import httpx

from hire_me_bot.connectors.workday import WorkdayConnector

JOBS_PAGE = {
    "total": 3,
    "jobPostings": [
        {"title": "Software Engineer Intern - Summer 2026", "externalPath": "/job/loc/Software-Engineer-Intern_R1"},
        {"title": "Senior Director of Sales", "externalPath": "/job/loc/Senior-Director-of-Sales_R2"},
        {"title": "Software Engineer 1 (Clearance Required)", "externalPath": "/job/loc/Software-Engineer-Clearance_R3"},
    ],
}

DETAIL = {
    "jobPostingInfo": {
        "id": "abc-123",
        "jobReqId": "R1",
        "title": "Software Engineer Intern - Summer 2026",
        "location": "Austin, TX",
        "jobDescription": "<p>Requirements: Python.</p>",
        "externalUrl": "https://acme.wd1.myworkdayjobs.com/acme_careers/job/loc/Software-Engineer-Intern_R1",
        "startDate": "2026-06-01",
    }
}


def _client_with_fixture():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/jobs"):
            return httpx.Response(200, json=JOBS_PAGE)
        if request.method == "GET" and "Senior-Director-of-Sales" in str(request.url):
            raise AssertionError("should not fetch detail for a filtered-out summary")
        if request.method == "GET" and "Software-Engineer-Clearance" in str(request.url):
            raise AssertionError("should not fetch detail for a clearance-required summary")
        if request.method == "GET":
            return httpx.Response(200, json=DETAIL)
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_filters_before_detail_and_normalizes():
    connector = WorkdayConnector(
        "Acme", "acme/wd1/acme_careers", http_client=_client_with_fixture()
    )
    postings = connector.fetch()

    # Only the intern posting should have made it through -- the "Senior
    # Director of Sales" summary must never trigger a detail GET.
    assert len(postings) == 1
    posting = postings[0]
    assert posting.source == "workday"
    assert posting.external_id == "R1"
    assert posting.title == "Software Engineer Intern - Summer 2026"
    assert posting.location == "Austin, TX"
    assert posting.url == "https://acme.wd1.myworkdayjobs.com/acme_careers/job/loc/Software-Engineer-Intern_R1"
    assert "Requirements" in posting.description
    assert posting.posted_at is not None


def test_token_is_parsed_into_tenant_wd_host_site():
    connector = WorkdayConnector("Acme", "acme/wd5/acme_careers")
    assert connector.tenant == "acme"
    assert connector.wd_host == "wd5"
    assert connector.site == "acme_careers"
