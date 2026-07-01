import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import track  # noqa: E402


def _posting(id_=1, company="Stripe", title="SWE Intern", status="not_applied"):
    return {"id": id_, "company": company, "title": title, "status": status}


def test_resolve_status_accepts_shorthand_and_full_word():
    assert track.resolve_status("a") == "applied"
    assert track.resolve_status("Applied") == "applied"
    assert track.resolve_status("i") == "interviewing"
    assert track.resolve_status("r") == "rejected"
    assert track.resolve_status("o") == "offer"
    assert track.resolve_status("bogus") is None


def test_arg_mode_single_match_updates_and_prints(monkeypatch, capsys):
    posting = _posting()
    monkeypatch.setattr(track.postings_repo, "search_by_company", lambda name: [posting])
    updates = []
    monkeypatch.setattr(track.postings_repo, "update_status", lambda pid, status: updates.append((pid, status)))

    track.run_arg_mode("stripe", "a")

    assert updates == [(1, "applied")]
    out = capsys.readouterr().out
    assert "✅ Stripe — SWE Intern → applied" in out


def test_arg_mode_no_match_prints_message(monkeypatch, capsys):
    monkeypatch.setattr(track.postings_repo, "search_by_company", lambda name: [])
    updates = []
    monkeypatch.setattr(track.postings_repo, "update_status", lambda pid, status: updates.append((pid, status)))

    track.run_arg_mode("nonexistent", "applied")

    assert updates == []
    assert "No postings found" in capsys.readouterr().out


def test_arg_mode_unknown_status_does_not_update(monkeypatch, capsys):
    updates = []
    monkeypatch.setattr(track.postings_repo, "update_status", lambda pid, status: updates.append((pid, status)))

    track.run_arg_mode("stripe", "banana")

    assert updates == []
    assert "Unknown status" in capsys.readouterr().out


def test_arg_mode_multiple_matches_disambiguates_by_number(monkeypatch, capsys):
    matches = [_posting(1, title="SWE Intern"), _posting(2, title="Data Intern")]
    monkeypatch.setattr(track.postings_repo, "search_by_company", lambda name: matches)
    updates = []
    monkeypatch.setattr(track.postings_repo, "update_status", lambda pid, status: updates.append((pid, status)))
    monkeypatch.setattr("builtins.input", lambda prompt="": "2")

    track.run_arg_mode("stripe", "applied")

    assert updates == [(2, "applied")]
    assert "Data Intern → applied" in capsys.readouterr().out


def test_arg_mode_multiple_matches_blank_input_cancels(monkeypatch):
    matches = [_posting(1), _posting(2)]
    monkeypatch.setattr(track.postings_repo, "search_by_company", lambda name: matches)
    updates = []
    monkeypatch.setattr(track.postings_repo, "update_status", lambda pid, status: updates.append((pid, status)))
    monkeypatch.setattr("builtins.input", lambda prompt="": "")

    track.run_arg_mode("stripe", "applied")

    assert updates == []


def test_interactive_mode_no_postings(monkeypatch, capsys):
    monkeypatch.setattr(track.postings_repo, "get_not_applied", lambda: [])
    track.run_interactive_mode()
    assert "Nothing to update" in capsys.readouterr().out


def test_interactive_mode_full_flow(monkeypatch, capsys):
    postings = [_posting(1, title="SWE Intern"), _posting(2, title="Data Intern")]
    monkeypatch.setattr(track.postings_repo, "get_not_applied", lambda: postings)
    updates = []
    monkeypatch.setattr(track.postings_repo, "update_status", lambda pid, status: updates.append((pid, status)))

    inputs = iter(["1", "i"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    track.run_interactive_mode()

    assert updates == [(1, "interviewing")]
    assert "SWE Intern → interviewing" in capsys.readouterr().out
