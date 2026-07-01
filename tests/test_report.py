import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import report  # noqa: E402


def _posting(**overrides):
    base = {
        "company": "Stripe",
        "title": "SWE Intern",
        "fit_score": 5,
        "status": "not_applied",
        "first_seen_at": "2026-06-01T12:00:00+00:00",
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


def test_build_report_handles_unscored_posting():
    postings = [_posting(fit_score=None)]
    report_text = report.build_report(postings)
    assert "| Stripe | SWE Intern | - | not_applied |" in report_text


def test_build_report_escapes_pipe_characters():
    postings = [_posting(title="Engineer | Backend")]
    report_text = report.build_report(postings)
    assert "Engineer \\| Backend" in report_text


def test_build_report_truncates_first_seen_to_date():
    postings = [_posting(first_seen_at="2026-06-01T12:34:56.789+00:00")]
    report_text = report.build_report(postings)
    assert "2026-06-01" in report_text
    assert "12:34:56" not in report_text
