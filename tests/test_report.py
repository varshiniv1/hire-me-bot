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
        "fit_score": 5,
        "status": "not_applied",
        "first_seen_at": "2026-06-01T12:00:00+00:00",
        "posted_at": "2026-06-01T12:00:00+00:00",
        "url": "https://stripe.com/jobs/1",
    }
    base.update(overrides)
    return base


def test_build_report_includes_all_postings_regardless_of_score():
    postings = [_posting(fit_score=5), _posting(company="LowFit", fit_score=1)]
    report_text = report.build_report(postings)
    assert "Stripe" in report_text
    assert "LowFit" in report_text
    assert "2 postings tracked" in report_text


def test_build_report_includes_location_and_apply_link():
    postings = [_posting()]
    report_text = report.build_report(postings)
    assert "San Francisco, CA" in report_text
    assert "[apply](https://stripe.com/jobs/1)" in report_text


def test_build_report_handles_unscored_posting():
    postings = [_posting(fit_score=None)]
    report_text = report.build_report(postings)
    assert "| Stripe | SWE Intern | San Francisco, CA |" in report_text
    assert "| - | not_applied |" in report_text


def test_build_report_escapes_pipe_characters():
    postings = [_posting(title="Engineer | Backend")]
    report_text = report.build_report(postings)
    assert "Engineer \\| Backend" in report_text


def test_build_report_shows_posted_date_and_age():
    now = datetime.now(timezone.utc)
    postings = [_posting(posted_at=(now - timedelta(days=3)).isoformat())]
    report_text = report.build_report(postings)
    assert (now - timedelta(days=3)).strftime("%Y-%m-%d") in report_text
    assert "3 days ago" in report_text


def test_build_report_handles_missing_posted_at():
    postings = [_posting(posted_at=None)]
    report_text = report.build_report(postings)
    assert "| - | date unknown |" in report_text
