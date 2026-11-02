import hashlib
import re
import unicodedata
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Select, case, cast, delete, exists, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONPATH, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import CurrentUser, OptionalUser, require_admin, require_mutation_header
from app.database import get_session
from app.models import (
    LearningProgress,
    User,
    VocabularyGroup,
    Word,
    WordGroup,
    WordMeaning,
)
from app.review_schedule import schedule_answer
from app.reviewed_vocabulary import canonical_term

router = APIRouter(prefix="/api")
DB = Annotated[Session, Depends(get_session)]


class MeaningInput(BaseModel):
    part_of_speech: str | None = Field(default=None, max_length=40)
    meaning: str = Field(min_length=1, max_length=10000)

    @field_validator("part_of_speech", "meaning", mode="before")
    @classmethod
    def normalize(cls, value):
        return (
            unicodedata.normalize("NFC", value.strip())
            if isinstance(value, str)
            else value
        )


class WordInput(BaseModel):
    term: str = Field(min_length=1, max_length=100)
    phonetic: str = Field(default="", max_length=200)
    meanings: list[MeaningInput] = Field(min_length=1, max_length=100)

    @field_validator("term", mode="before")
    @classmethod
    def normalize_term(cls, value):
        return canonical_term(value) if isinstance(value, str) else value

    @field_validator("term")
    @classmethod
    def validate_term(cls, value):
        if not re.fullmatch(r"[A-Za-z][A-Za-z .'/\-]*", value):
            raise ValueError("Enter an English word.")
        return value


class GroupOut(BaseModel):
    slug: str
    name: str


class WordOut(BaseModel):
    id: int
    term: str
    phonetic: str
    meanings: list[MeaningInput]
    groups: list[GroupOut]
    score: int = 0
    studied: bool = False
    next_review_at: datetime | None = None
    senior_type: Literal["core", "extend", "basic"] | None = None
    senior_types: list[Literal["core", "extend", "basic"]] = Field(default_factory=list)


class WordPage(BaseModel):
    items: list[WordOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class GroupSummary(GroupOut):
    total: int
    studied: int = 0
    completion: float = 0
    score_counts: list[int] = Field(default_factory=lambda: [0] * 6)


class RandomWord(BaseModel):
    word: WordOut | None
    total: int
    next_due: datetime | None = None


def words_in_group(db: Session, group: str) -> Select:
    query = select(Word)
    if group == "all":
        return query
    group_id = db.scalar(
        select(VocabularyGroup.id).where(VocabularyGroup.slug == group)
    )
    if group_id is None:
        raise HTTPException(404, "Group not found.")
    return query.join(WordGroup).where(WordGroup.group_id == group_id)


def serialize_words(
    db: Session, words: list[Word], user: User | None = None
) -> list[WordOut]:
    if not words:
        return []
    ids = [word.id for word in words]
    progress = (
        {
            item.word_id: item
            for item in db.scalars(
                select(LearningProgress).where(
                    LearningProgress.user_id == user.id,
                    LearningProgress.word_id.in_(ids),
                )
            )
        }
        if user
        else {}
    )
    meanings: dict[int, list[MeaningInput]] = {word_id: [] for word_id in ids}
    groups: dict[int, list[GroupOut]] = {word_id: [] for word_id in ids}
    senior_types: dict[int, list[str]] = {}
    for meaning in db.scalars(
        select(WordMeaning).where(WordMeaning.word_id.in_(ids)).order_by(WordMeaning.id)
    ):
        meanings[meaning.word_id].append(
            MeaningInput(
                part_of_speech=meaning.part_of_speech or None, meaning=meaning.meaning
            )
        )
    for word_id, group, list_code, source_entries in db.execute(
        select(
            WordGroup.word_id,
            VocabularyGroup,
            WordGroup.list_code,
            WordGroup.source_entries,
        )
        .join(VocabularyGroup, VocabularyGroup.id == WordGroup.group_id)
        .where(WordGroup.word_id.in_(ids))
        .order_by(VocabularyGroup.id)
    ):
        groups[word_id].append(GroupOut(slug=group.slug, name=group.name))
        if group.slug == "senior":
            codes = [list_code] + [
                item.get("list_code") for item in source_entries or []
            ]
            types = []
            for code in codes:
                match = re.fullmatch(r"(core|extend|basic)\d+", code or "")
                if match and match[1] not in types:
                    types.append(match[1])
            senior_types[word_id] = types
    return [
        WordOut(
            id=word.id,
            score=progress[word.id].score if word.id in progress else 0,
            studied=word.id in progress,
            next_review_at=progress[word.id].due_at if word.id in progress else None,
            term=word.term,
            phonetic=word.phonetic,
            meanings=meanings[word.id],
            groups=groups[word.id],
            senior_type=next(iter(senior_types.get(word.id, [])), None),
            senior_types=senior_types.get(word.id, []),
        )
        for word in words
    ]


def store_meanings(db: Session, word_id: int, meanings: list[MeaningInput]) -> None:
    rows = {}
    for item in meanings:
        part_of_speech = (item.part_of_speech or "").lower()
        key = (part_of_speech, item.meaning)
        if key not in rows:
            rows[key] = {
                "word_id": word_id,
                "part_of_speech": part_of_speech,
                "meaning": item.meaning,
                "meaning_hash": hashlib.sha256(item.meaning.encode()).hexdigest(),
            }
    if rows:
        db.execute(
            insert(WordMeaning)
            .values(list(rows.values()))
            .on_conflict_do_nothing(constraint="uq_word_meaning")
        )


def lock_word(db: Session, word_id: int) -> Word:
    word = db.scalar(select(Word).where(Word.id == word_id).with_for_update())
    if word is None:
        raise HTTPException(404, "Word not found.")
    return word


@router.get("/words/exists")
def word_exists(
    db: DB, term: str = Query(..., min_length=1, max_length=100), group: str = "all"
) -> dict[str, bool]:
    query = words_in_group(db, group).where(Word.term == canonical_term(term))
    return {"exists": db.scalar(select(query.exists()))}


@router.get("/groups", response_model=list[GroupSummary])
def list_groups(
    db: DB, user: OptionalUser, response: Response, include_all: bool = False
):
    response.headers["Cache-Control"] = "no-store"
    summaries = {
        group.id: GroupSummary(slug=group.slug, name=group.name, total=0)
        for group in db.scalars(select(VocabularyGroup).order_by(VocabularyGroup.id))
    }
    user_id = user.id if user else -1
    counts = (
        select(WordGroup.group_id, LearningProgress.score, func.count())
        .outerjoin(
            LearningProgress,
            (LearningProgress.word_id == WordGroup.word_id)
            & (LearningProgress.user_id == user_id),
        )
        .group_by(WordGroup.group_id, LearningProgress.score)
    )
    if include_all:
        summaries[-1] = GroupSummary(slug="all", name="All", total=0)
        counts = counts.union_all(
            select(literal(-1), LearningProgress.score, func.count(Word.id))
            .select_from(Word)
            .outerjoin(
                LearningProgress,
                (LearningProgress.word_id == Word.id)
                & (LearningProgress.user_id == user_id),
            )
            .group_by(LearningProgress.score)
        )
    for group_id, score, count in db.execute(counts):
        summary = summaries[group_id]
        summary.total += count
        summary.score_counts[score or 0] += count
        if score is not None:
            summary.studied += count
    for summary in summaries.values():
        summary.completion = (
            (
                sum(score * count for score, count in enumerate(summary.score_counts))
                / (summary.total * 5)
                * 100
            )
            if summary.total
            else 0
        )
    return list(summaries.values())


@router.post(
    "/groups/{slug}/words",
    response_model=WordOut,
    dependencies=[Depends(require_admin), Depends(require_mutation_header)],
)
def save_word(slug: str, data: WordInput, db: DB, user: CurrentUser):
    group = db.scalar(select(VocabularyGroup).where(VocabularyGroup.slug == slug))
    if group is None:
        raise HTTPException(404, "Group not found.")
    statement = insert(Word).values(term=data.term, phonetic=data.phonetic)
    word_id = db.scalar(
        statement.on_conflict_do_update(
            index_elements=[Word.term],
            set_={"phonetic": data.phonetic if data.phonetic else Word.phonetic},
        ).returning(Word.id)
    )
    membership = db.scalar(
        insert(WordGroup)
        .values(word_id=word_id, group_id=group.id)
        .on_conflict_do_nothing()
        .returning(WordGroup.word_id)
    )
    if membership is None:
        db.rollback()
        raise HTTPException(409, "This word already exists in this group.")
    store_meanings(db, word_id, data.meanings)
    db.commit()
    return serialize_words(db, [db.get(Word, word_id)], user)[0]


@router.get("/words/random", response_model=RandomWord)
def random_word(
    db: DB,
    user: OptionalUser,
    response: Response,
    group: str = "all",
    exclude_id: int | None = Query(None, ge=1),
):
    response.headers["Cache-Control"] = "no-store"
    query = words_in_group(db, group)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    next_due = None
    if user is not None:
        query = query.outerjoin(
            LearningProgress,
            (LearningProgress.word_id == Word.id)
            & (LearningProgress.user_id == user.id),
        )
        now = datetime.now(UTC)
        previous_last = case((Word.id == exclude_id, 1), else_=0)
        # Due learning/relearning cards come first, then due reviews. Legacy
        # progress without a due date is eligible for its first FSRS review.
        due = query.where(
            LearningProgress.word_id.is_not(None),
            or_(LearningProgress.due_at.is_(None), LearningProgress.due_at <= now),
        )
        learning_first = case(
            (LearningProgress.fsrs_card["state"].as_integer().in_([1, 3]), 0),
            else_=1,
        )
        word = db.scalar(due.order_by(
            learning_first, previous_last, LearningProgress.due_at.asc().nulls_first(), Word.id
        ).limit(1))
        if word is None:
            word = db.scalar(query.where(LearningProgress.word_id.is_(None))
                .order_by(previous_last, func.random()).limit(1))
        if word is None:
            next_due = db.scalar(query.with_only_columns(func.min(LearningProgress.due_at)))
    else:
        if total > 1 and exclude_id is not None:
            query = query.where(Word.id != exclude_id)
        word = db.scalar(query.order_by(func.random()).limit(1))
    return RandomWord(
        word=serialize_words(db, [word], user)[0] if word is not None else None,
        total=total,
        next_due=next_due,
    )


@router.get("/words", response_model=WordPage)
def list_words(
    db: DB,
    user: OptionalUser,
    response: Response,
    group: str = "all",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: Literal["id", "english", "chinese"] = "id",
    sort_order: Literal["asc", "desc"] = "asc",
    q: str = Query("", max_length=200),
    locate_id: int | None = Query(None, ge=1),
    member_of: str | None = Query(None, max_length=200),
    senior_types: str | None = Query(None, max_length=50),
):
    response.headers["Cache-Control"] = "no-store"
    query = words_in_group(db, group)
    if member_of is not None:
        slugs = {slug.strip() for slug in member_of.split(",")}
        membership_groups = list(
            db.scalars(
                select(VocabularyGroup.id).where(VocabularyGroup.slug.in_(slugs))
            )
        )
        if len(membership_groups) != len(slugs):
            raise HTTPException(404, "Group not found.")
        query = query.where(
            exists()
            .where(
                WordGroup.word_id == Word.id,
                WordGroup.group_id.in_(membership_groups),
            )
            .correlate(Word)
        )
    if senior_types is not None:
        types = {item.strip() for item in senior_types.split(",")}
        if not types <= {"core", "extend", "basic"}:
            raise HTTPException(422, "Unknown Senior type.")
        senior_id = (
            select(VocabularyGroup.id)
            .where(VocabularyGroup.slug == "senior")
            .scalar_subquery()
        )
        pattern = rf"^({'|'.join(sorted(types))})[0-9]+$"
        query = query.where(
            exists()
            .where(
                WordGroup.word_id == Word.id,
                WordGroup.group_id == senior_id,
                or_(
                    WordGroup.list_code.op("~")(pattern),
                    func.jsonb_path_exists(
                        WordGroup.source_entries,
                        cast(
                            '$[*] ? (@.list_code like_regex "' + pattern + '")',
                            JSONPATH,
                        ),
                    ),
                ),
            )
            .correlate(Word)
        )
    search = canonical_term(q)
    if search:
        query = query.where(
            or_(
                Word.term.contains(search, autoescape=True),
                exists().where(
                    WordMeaning.word_id == Word.id,
                    WordMeaning.meaning.icontains(search, autoescape=True),
                ),
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, total_pages)
    sort_column = Word.id if sort_by == "id" else Word.term
    if sort_by == "chinese":
        # Match the first meaning displayed in the Chinese column.
        sort_column = func.coalesce(
            select(WordMeaning.meaning)
            .where(WordMeaning.word_id == Word.id)
            .order_by(WordMeaning.id)
            .limit(1)
            .correlate(Word)
            .scalar_subquery(),
            "",
        )
    ordering = sort_column.desc() if sort_order == "desc" else sort_column.asc()
    orderings = (ordering, Word.id.asc())
    if sort_by == "id" and group != "all":
        source_order = (
            WordGroup.position.desc()
            if sort_order == "desc"
            else WordGroup.position.asc()
        )
        orderings = (source_order.nulls_last(), *orderings)
    if locate_id is not None:
        ranked = query.with_only_columns(
            Word.id.label("word_id"),
            func.row_number().over(order_by=orderings).label("position"),
        ).subquery()
        position = db.scalar(
            select(ranked.c.position).where(ranked.c.word_id == locate_id)
        )
        if position is None:
            raise HTTPException(404, "Word not found in this group.")
        page = (position - 1) // page_size + 1
    words = list(
        db.scalars(
            query.order_by(*orderings).limit(page_size).offset((page - 1) * page_size)
        )
    )
    return WordPage(
        items=serialize_words(db, words, user),
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.patch(
    "/words/{word_id}",
    response_model=WordOut,
    dependencies=[Depends(require_admin), Depends(require_mutation_header)],
)
def edit_word(word_id: int, data: WordInput, db: DB, user: CurrentUser):
    word = lock_word(db, word_id)
    try:
        word.term = data.term
        word.phonetic = data.phonetic
        db.flush()
        db.execute(delete(WordMeaning).where(WordMeaning.word_id == word_id))
        store_meanings(db, word_id, data.meanings)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "This English word already exists. Edit its existing entry instead."
        ) from None
    return serialize_words(db, [word], user)[0]


@router.delete(
    "/words/{word_id}",
    status_code=204,
    dependencies=[Depends(require_admin), Depends(require_mutation_header)],
)
def delete_word(word_id: int, db: DB, group: str = Query(...)):
    word = lock_word(db, word_id)
    if group == "all":
        db.delete(word)
    else:
        group_id = db.scalar(
            select(VocabularyGroup.id).where(VocabularyGroup.slug == group)
        )
        membership = (
            db.get(WordGroup, (word_id, group_id)) if group_id is not None else None
        )
        if membership is None:
            raise HTTPException(404, "Word not found in this group.")
        db.delete(membership)
        db.flush()
        if not db.scalar(select(exists().where(WordGroup.word_id == word_id))):
            db.delete(word)
    db.commit()
    return Response(status_code=204)


class AnswerInput(BaseModel):
    answer: Literal["yes", "not_sure", "no"]


@router.post(
    "/words/{word_id}/progress",
    response_model=WordOut,
    dependencies=[Depends(require_mutation_header)],
)
def record_answer(word_id: int, data: AnswerInput, db: DB, user: CurrentUser):
    # Serialize answers and vocabulary deletion; persist state and log atomically.
    word = lock_word(db, word_id)
    progress = db.get(LearningProgress, (user.id, word_id))
    if progress is None:
        progress = LearningProgress(user_id=user.id, word_id=word_id, attempts=0)
        db.add(progress)
    review = schedule_answer(progress, data.answer)
    db.flush()
    db.add(review)
    db.commit()
    return serialize_words(db, [word], user)[0]
