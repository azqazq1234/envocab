from datetime import UTC, datetime, timedelta

import pytest
from fsrs import Card, Rating, Scheduler, State

from app.models import LearningProgress
from app.review_schedule import learning_level, schedule_answer


@pytest.mark.parametrize("answer,rating,seconds,level", [
    ("no", Rating.Again, 60, 0),
    ("not_sure", Rating.Hard, 330, 1),
    ("yes", Rating.Good, 600, 1),
])
def test_initial_ratings_and_due_times(answer, rating, seconds, level):
    now = datetime(2026, 11, 2, tzinfo=UTC)
    progress = LearningProgress(user_id=1, word_id=2, attempts=0)
    log = schedule_answer(progress, answer, now)
    assert log.rating == rating
    assert progress.due_at == now + timedelta(seconds=seconds)
    assert progress.score == level
    assert progress.attempts == 1
    assert log.card_before["last_review"] is None
    assert log.card_after == progress.fsrs_card
    assert Card.from_dict(progress.fsrs_card).last_review == now


def test_saved_state_drives_fsrs_instead_of_score(monkeypatch):
    scheduler = Scheduler(enable_fuzzing=False)
    monkeypatch.setattr("app.review_schedule.SCHEDULER", scheduler)
    now = datetime(2026, 11, 2, tzinfo=UTC)
    progress = LearningProgress(user_id=1, word_id=2, attempts=0)
    schedule_answer(progress, "yes", now)
    before = Card.from_dict(progress.fsrs_card)
    next_time = progress.due_at
    expected, _ = scheduler.review_card(before, Rating.Good, review_datetime=next_time)
    progress.score = 5  # Display score is not an input to FSRS.
    log = schedule_answer(progress, "yes", next_time)
    assert progress.fsrs_card == expected.to_dict()
    assert progress.due_at > next_time + timedelta(hours=23)
    assert progress.attempts == 2
    assert log.card_before == before.to_dict()
    assert expected.state == State.Review


def test_mature_words_continue_reviewing_and_lapses_relearn(monkeypatch):
    monkeypatch.setattr("app.review_schedule.SCHEDULER", Scheduler(enable_fuzzing=False))
    now = datetime(2026, 11, 2, tzinfo=UTC)
    progress = LearningProgress(user_id=1, word_id=2, attempts=0)
    for _ in range(12):
        schedule_answer(progress, "yes", now)
        now = progress.due_at
    assert progress.score == 5
    assert progress.due_at is not None
    log = schedule_answer(progress, "no", now)
    assert log.card_before["stability"] > progress.fsrs_card["stability"]
    assert progress.score == 0
    assert progress.fsrs_card["state"] == State.Relearning
    assert progress.due_at == now + timedelta(minutes=10)


def test_legacy_progress_preserves_attempts_without_inventing_history():
    progress = LearningProgress(user_id=1, word_id=2, score=5, attempts=19)
    log = schedule_answer(progress, "yes")
    assert log.card_before["last_review"] is None
    assert progress.attempts == 20
    assert progress.score == 1
    assert progress.fsrs_card["state"] == State.Learning


@pytest.mark.parametrize("stability,level", [(0.5, 1), (1, 2), (3, 3), (7, 4), (30, 5), (365, 5)])
def test_display_levels_are_based_on_memory_stability(stability, level):
    card = Card(state=State.Review, stability=stability, difficulty=5)
    assert learning_level(card, Rating.Good) == level
