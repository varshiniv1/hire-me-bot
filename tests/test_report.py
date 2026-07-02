import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import report  # noqa: E402


def _posting(**overrides):
    base = {
        "company": "Stripe",
        "title": "SWE Intern",
        "location": "San Francisco, CA",
        "source": "greenhouse",
        "status": "not_applied",
        "posted_at": "2026-06-01T12:00:00+00:00",
        "url": "https://stripe.com/jobs/1",
    }
    base.update(overrides)
    return base


def test_build_report_includes_all_postings():
    postings = [_posting(), _posting(company="Ramp")]
    report_text = report.build_report(postings)
    assert "Stripe" in report_text
    assert "Ramp" in report_text
    assert "2 postings tracked" in report_text


def test_build_report_includes_location_source_and_apply_link():
    postings = [_posting()]
    report_text = report.build_report(postings)
    assert "San Francisco, CA" in report_text
    assert "Greenhouse" in report_text
    assert "[Apply](https://stripe.com/jobs/1)" in report_text


def test_build_report_row_shape():
    postings = [_posting()]
    report_text = report.build_report(postings)
    assert "| Stripe | SWE Intern | San Francisco, CA | Greenhouse | not_applied |" in report_text


def test_build_report_escapes_pipe_characters():
    postings = [_posting(title="Engineer | Backend")]
    report_text = report.build_report(postings)
    assert "Engineer \\| Backend" in report_text


def test_build_report_shows_compact_age():
    now = datetime.now(timezone.utc)
    postings = [
        _posting(posted_at=now.isoformat()),
        _posting(company="Ramp", posted_at=(now - timedelta(days=13)).isoformat()),
        _posting(company="Notion", posted_at=(now - timedelta(days=90)).isoformat()),
    ]
    report_text = report.build_report(postings)
    assert "| 0d |" in report_text
    assert "| 13d |" in report_text
    assert "| 3mo |" in report_text


def test_build_report_handles_missing_posted_at():
    postings = [_posting(posted_at=None)]
    report_text = report.build_report(postings)
    assert "| ? |" in report_text
