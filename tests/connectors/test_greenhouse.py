import httpx

from hire_me_bot.connectors.greenhouse import GreenhouseConnector

FIXTURE = {
    "jobs": [
        {
            "id": 12345,
            "title": "Software Engineering Intern - Summer 2026",
            "updated_at": "2026-01-15T10:00:00-05:00",
            "location": {"name": "Remote"},
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/12345",
            "content": "<p>Join us.</p><p><b>Requirements:</b><br>Python experience.</p>",
        }
    ]
}


def _client_with_fixture():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["content"] == "true"
        return httpx.Response(200, json=FIXTURE)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_and_normalize():
    connector = GreenhouseConnector("Acme", "acme", http_client=_client_with_fixture())
    postings = connector.fetch()

    assert len(postings) == 1
    posting = postings[0]
    assert posting.source == "greenhouse"
    assert posting.company == "Acme"
    assert posting.external_id == "12345"
    assert posting.title == "Software Engineering Intern - Summer 2026"
    assert posting.location == "Remote"
    assert posting.url == "https://boards.greenhouse.io/acme/jobs/12345"
    assert "Requirements:" in posting.description
    assert "<p>" not in posting.description
    assert posting.posted_at is not None
