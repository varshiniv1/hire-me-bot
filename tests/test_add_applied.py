import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import add_applied  # noqa: E402


def _stub_add_manual_applied(monkeypatch):
    calls = []

    def fake(company, title, url, source):
        calls.append((company, title, url, source))
        return {"company": company, "title": title}

    monkeypatch.setattr(add_applied.postings_repo, "add_manual_applied", fake)
    return calls


def test_arg_mode_three_args_defaults_source_to_manual(monkeypatch, capsys):
    calls = _stub_add_manual_applied(monkeypatch)

    add_applied.main(["Indeed Co", "SWE Intern", "https://indeed.com/job/1"])

    assert calls == [("Indeed Co", "SWE Intern", "https://indeed.com/job/1", "manual")]
    assert "Added Indeed Co — SWE Intern as applied" in capsys.readouterr().out


def test_arg_mode_four_args_uses_given_source(monkeypatch, capsys):
    calls = _stub_add_manual_applied(monkeypatch)

    add_applied.main(["Indeed Co", "SWE Intern", "https://indeed.com/job/1", "indeed"])

    assert calls == [("Indeed Co", "SWE Intern", "https://indeed.com/job/1", "indeed")]


def test_arg_mode_wrong_arg_count_exits(monkeypatch):
    _stub_add_manual_applied(monkeypatch)

    with pytest.raises(SystemExit):
        add_applied.main(["only", "two"])


def test_add_prints_friendly_message_on_duplicate(monkeypatch, capsys):
    def raise_dup(company, title, url, source):
        raise Exception("duplicate key value violates unique constraint")

    monkeypatch.setattr(add_applied.postings_repo, "add_manual_applied", raise_dup)

    add_applied.add("Indeed Co", "SWE Intern", "https://indeed.com/job/1", "manual")

    assert "Couldn't add posting" in capsys.readouterr().out


def test_interactive_mode_prompts_for_each_field(monkeypatch, capsys):
    calls = _stub_add_manual_applied(monkeypatch)
    inputs = iter(["Indeed Co", "SWE Intern", "https://indeed.com/job/1", ""])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    add_applied.run_interactive_mode()

    assert calls == [("Indeed Co", "SWE Intern", "https://indeed.com/job/1", "manual")]
    assert "Added Indeed Co — SWE Intern as applied" in capsys.readouterr().out


def test_interactive_mode_reprompts_on_blank_required_field(monkeypatch):
    inputs = iter(["", "Indeed Co"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    result = add_applied._prompt("Company")

    assert result == "Indeed Co"
