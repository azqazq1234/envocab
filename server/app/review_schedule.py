"""FSRS scheduling; score is a display level, not an input to the scheduler."""

from datetime import UTC, datetime, timedelta

from fsrs import Card, Rating, Scheduler, State

from app.models import LearningProgress, WordReview

SCHEDULER = Scheduler(
    desired_retention=0.9,
    learning_steps=(timedelta(minutes=1), timedelta(minutes=10)),
    relearning_steps=(timedelta(minutes=10),),
)
ANSWER_RATINGS = {"no": Rating.Again, "not_sure": Rating.Hard, "yes": Rating.Good}


def learning_level(card: Card, rating: Rating) -> int:
    if rating == Rating.Again:
        return 0
    if card.state != State.Review:
        return 1
    stability = card.stability or 0
    # Six display levels, based on stability in days, independent of scheduling.
    return 1 + sum(stability >= days for days in (1, 3, 7, 30))


def schedule_answer(
    progress: LearningProgress, answer: str, now: datetime | None = None
) -> WordReview:
    now = now or datetime.now(UTC)
    card = (
        Card.from_dict(progress.fsrs_card)
        if progress.fsrs_card
        else Card(card_id=progress.word_id, due=now)
    )
    before = card.to_dict()
    rating = ANSWER_RATINGS[answer]
    card, _ = SCHEDULER.review_card(card, rating, review_datetime=now)
    progress.fsrs_card = card.to_dict()
    progress.due_at = card.due
    progress.updated_at = now
    progress.attempts = (progress.attempts or 0) + 1
    progress.score = learning_level(card, rating)
    return WordReview(
        user_id=progress.user_id,
        word_id=progress.word_id,
        reviewed_at=now,
        rating=int(rating),
        card_before=before,
        card_after=card.to_dict(),
    )
