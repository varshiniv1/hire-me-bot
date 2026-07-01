import httpx

from hire_me_bot.connectors.ashby import AshbyConnector

FIXTURE = {
    "jobs": [
        {
            "id": "job-1",
            "title": "New Grad Software Engineer",
            "location": "Remote - US",
            "descriptionPlain": "About the role. Requirements: SQL.",
            "jobUrl": "https://jobs.ashbyhq.com/acme/job-1",
            "publishedAt": "2026-01-15T10:00:00.000Z",
        }
    ]
}


def _client_with_fixture():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=FIXTURE)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_and_normalize():
    connector = AshbyConnector("Acme", "acme", http_client=_client_with_fixture())
    postings = connector.fetch()

    assert len(postings) == 1
    posting = postings[0]
    assert posting.source == "ashby"
    assert posting.external_id == "job-1"
    assert posting.title == "New Grad Software Engineer"
    assert posting.location == "Remote - US"
    assert posting.url == "https://jobs.ashbyhq.com/acme/job-1"
    assert "Requirements" in posting.description
    assert posting.posted_at is not None
