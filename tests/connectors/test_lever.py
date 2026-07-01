import httpx

from hire_me_bot.connectors.lever import LeverConnector

FIXTURE = [
    {
        "id": "abc-123",
        "text": "Software Engineer Intern",
        "categories": {"location": "San Francisco", "team": "Engineering"},
        "descriptionPlain": "Build things. Requirements: Python.",
        "hostedUrl": "https://jobs.lever.co/acme/abc-123",
        "createdAt": 1737000000000,
    }
]


def _client_with_fixture():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["mode"] == "json"
        return httpx.Response(200, json=FIXTURE)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_and_normalize():
    connector = LeverConnector("Acme", "acme", http_client=_client_with_fixture())
    postings = connector.fetch()

    assert len(postings) == 1
    posting = postings[0]
    assert posting.source == "lever"
    assert posting.external_id == "abc-123"
    assert posting.title == "Software Engineer Intern"
    assert posting.location == "San Francisco"
    assert posting.url == "https://jobs.lever.co/acme/abc-123"
    assert "Requirements" in posting.description
    assert posting.posted_at is not None
