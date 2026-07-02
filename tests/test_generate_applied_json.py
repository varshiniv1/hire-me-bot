import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import generate_applied_json  # noqa: E402


def _posting(**overrides):
    base = {
        "id": 1,
        "company": "Stripe",
        "title": "SWE Intern",
        "location": "San Francisco, CA",
        "source": "greenhouse",
        "status": "applied",
        "url": "https://stripe.com/jobs/1",
        "applied_at": "2026-07-01T12:00:00+00:00",
    }
    base.update(overrides)
    return base


def test_to_entry_shape():
    entry = generate_applied_json._to_entry(_posting())
    assert entry == {
        "id": 1,
        "company": "Stripe",
        "role": "SWE Intern",
        "location": "San Francisco, CA",
        "source": "Greenhouse",
        "status": "applied",
        "url": "https://stripe.com/jobs/1",
        "applied_at": "2026-07-01T12:00:00+00:00",
    }


def test_to_entry_preserves_non_applied_statuses():
    entry = generate_applied_json._to_entry(_posting(status="interviewing"))
    assert entry["status"] == "interviewing"


def test_to_entry_handles_missing_location():
    entry = generate_applied_json._to_entry(_posting(location=None))
    assert entry["location"] == "-"
