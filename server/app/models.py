from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
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
