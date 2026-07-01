import httpx

from hire_me_bot.connectors.recruitee import RecruiteeConnector

FIXTURE = {
    "offers": [
        {
            "id": 555,
            "title": "Junior Software Developer",
            "city": "Amsterdam",
            "country": "Netherlands",
            "description": "<p>About the role.</p>",
            "requirements": "<p>Requirements: JavaScript.</p>",
            "careers_url": "https://acme.recruitee.com/o/junior-software-developer",
            "published_at": "2026-01-15 10:00:00 UTC",
        }
    ]
}


def _client_with_fixture():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=FIXTURE)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_and_normalize():
    connector = RecruiteeConnector("Acme", "acme", http_client=_client_with_fixture())
    postings = connector.fetch()

    assert len(postings) == 1
    posting = postings[0]
    assert posting.source == "recruitee"
    assert posting.external_id == "555"
    assert posting.title == "Junior Software Developer"
    assert posting.location == "Amsterdam"
    assert posting.url == "https://acme.recruitee.com/o/junior-software-developer"
    assert "Requirements" in posting.description
    assert posting.posted_at is not None
