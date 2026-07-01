from hire_me_bot import settings
from hire_me_bot.scoring import scorer


def _fake_posting(i: int) -> dict:
    return {"id": i, "company": f"Company{i}", "title": "Software Engineer", "description": "Requirements: Python."}


def test_scores_individually_at_or_below_threshold(monkeypatch):
    postings = [_fake_posting(i) for i in range(settings.BATCH_SCORING_TRIGGER)]  # 15

    individual_calls = []
    batch_calls = []
    updates = []

    monkeypatch.setattr(
        scorer.claude_client, "score_posting",
        lambda profile, company, title, jd: individual_calls.append(company) or 3,
    )
    monkeypatch.setattr(
        scorer.claude_client, "score_batch",
        lambda profile, items: batch_calls.append(items) or {},
    )
    monkeypatch.setattr(scorer.postings_repo, "update_score", lambda pid, score: updates.append((pid, score)))

    scorer.score_new_postings(postings, profile={})

    assert len(individual_calls) == 15
    assert batch_calls == []
    assert len(updates) == 15


def test_scores_in_batches_above_threshold(monkeypatch):
    postings = [_fake_posting(i) for i in range(settings.BATCH_SCORING_TRIGGER + 1)]  # 16

    individual_calls = []
    batch_calls = []
    updates = []

    def fake_score_batch(profile, items):
        batch_calls.append(items)
        return {item["posting_id"]: 4 for item in items}

    monkeypatch.setattr(
        scorer.claude_client, "score_posting",
        lambda profile, company, title, jd: individual_calls.append(company) or 3,
    )
    monkeypatch.setattr(scorer.claude_client, "score_batch", fake_score_batch)
    monkeypatch.setattr(scorer.postings_repo, "update_score", lambda pid, score: updates.append((pid, score)))

    scorer.score_new_postings(postings, profile={})

    assert individual_calls == []
    # 16 postings at BATCH_SIZE=6 -> 3 batches (6, 6, 4)
    assert len(batch_calls) == 3
    assert len(updates) == 16


def test_batch_mismatch_only_updates_returned_ids(monkeypatch):
    postings = [_fake_posting(i) for i in range(settings.BATCH_SCORING_TRIGGER + 1)]  # forces batch path
    updates = []

    def fake_score_batch(profile, items):
        # Simulate Claude dropping one posting_id from its response.
        return {item["posting_id"]: 5 for item in items[:-1]}

    monkeypatch.setattr(scorer.claude_client, "score_batch", fake_score_batch)
    monkeypatch.setattr(scorer.postings_repo, "update_score", lambda pid, score: updates.append((pid, score)))

    scorer.score_new_postings(postings, profile={})

    # Every batch is missing exactly its last item -> total updates < total postings
    assert len(updates) < len(postings)


def test_empty_input_does_nothing(monkeypatch):
    calls = []
    monkeypatch.setattr(scorer.postings_repo, "update_score", lambda pid, score: calls.append((pid, score)))
    scorer.score_new_postings([], profile={})
    assert calls == []
