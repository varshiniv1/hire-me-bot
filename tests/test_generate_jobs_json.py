import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import generate_jobs_json  # noqa: E402


def _posting(**overrides):
    base = {
        "id": 1,
        "company": "Stripe",
        "title": "SWE Intern",
        "location": "San Francisco, CA",
        "source": "greenhouse",
        "status": "not_applied",
        "posted_at": "2026-06-30T00:00:00+00:00",
        "url": "https://stripe.com/jobs/1",
    }
    base.update(overrides)
    return base


def test_to_entry_shape():
    entry = generate_jobs_json._to_entry(_posting())
    assert entry == {
        "id": 1,
        "company": "Stripe",
        "role": "SWE Intern",
        "location": "San Francisco, CA",
        "source": "Greenhouse",
        "status": "not_applied",
        "url": "https://stripe.com/jobs/1",
        "age": entry["age"],  # exact value covered by format_utils tests
        "is_internship": True,
    }


def test_to_entry_flags_full_time_correctly():
    entry = generate_jobs_json._to_entry(_posting(title="Software Engineer II"))
    assert entry["is_internship"] is False


def test_to_entry_handles_missing_location():
    entry = generate_jobs_json._to_entry(_posting(location=None))
    assert entry["location"] == "-"
