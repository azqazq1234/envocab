from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Word(Base):
    __tablename__ = "words"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    term: Mapped[str] = mapped_column(String(100), unique=True)
    phonetic: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class WordMeaning(Base):
    __tablename__ = "word_meanings"
    __table_args__ = (
        UniqueConstraint(
            "word_id", "part_of_speech", "meaning_hash", name="uq_word_meaning"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    word_id: Mapped[int] = mapped_column(
        ForeignKey("words.id", ondelete="CASCADE"), index=True
    )
    part_of_speech: Mapped[str] = mapped_column(String(40), default="")
    meaning: Mapped[str] = mapped_column(Text)
    meaning_hash: Mapped[str] = mapped_column(String(64))


class VocabularyGroup(Base):
    __tablename__ = "vocabulary_groups"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    slug: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(50))


class WordGroup(Base):
    __tablename__ = "word_groups"

    word_id: Mapped[int] = mapped_column(
        ForeignKey("words.id", ondelete="CASCADE"), primary_key=True
    )
    group_id: Mapped[int] = mapped_column(
        ForeignKey("vocabulary_groups.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    list_code: Mapped[str | None] = mapped_column(String(30))
    position: Mapped[int | None] = mapped_column(Integer)
    source_term: Mapped[str | None] = mapped_column(String(200))
    source_entries: Mapped[list[dict] | None] = mapped_column(JSONB)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(40), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    @property
    def is_admin(self) -> bool:
        return self.username == "harvey"


class UserSession(Base):
    __tablename__ = "user_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LearningProgress(Base):
    __tablename__ = "learning_progress"
    __table_args__ = (
        CheckConstraint("score BETWEEN 0 AND 5", name="ck_learning_score"),
        Index("ix_learning_progress_user_due", "user_id", "due_at"),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    word_id: Mapped[int] = mapped_column(
        ForeignKey("words.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    score: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    fsrs_card: Mapped[dict | None] = mapped_column(JSONB)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WordReview(Base):
    __tablename__ = "word_reviews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "word_id"],
            ["learning_progress.user_id", "learning_progress.word_id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("rating BETWEEN 1 AND 4", name="ck_word_review_rating"),
        Index("ix_word_reviews_user_word", "user_id", "word_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    word_id: Mapped[int] = mapped_column(BigInteger)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rating: Mapped[int] = mapped_column(Integer)
    card_before: Mapped[dict] = mapped_column(JSONB)
    card_after: Mapped[dict] = mapped_column(JSONB)
