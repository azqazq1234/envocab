import hashlib
import re
import unicodedata
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Select, cast, delete, exists, func, or_, select
from sqlalchemy.dialects.postgresql import JSONPATH, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import VocabularyGroup, Word, WordGroup, WordMeaning
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


class RandomWord(BaseModel):
    word: WordOut | None
    total: int


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


def serialize_words(db: Session, words: list[Word]) -> list[WordOut]:
    if not words:
        return []
    ids = [word.id for word in words]
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
        select(WordGroup.word_id, VocabularyGroup, WordGroup.list_code, WordGroup.source_entries)
        .join(VocabularyGroup, VocabularyGroup.id == WordGroup.group_id)
        .where(WordGroup.word_id.in_(ids))
        .order_by(VocabularyGroup.id)
    ):
        groups[word_id].append(GroupOut(slug=group.slug, name=group.name))
        if group.slug == "senior":
            codes = [list_code] + [item.get("list_code") for item in source_entries or []]
            types = []
            for code in codes:
                match = re.fullmatch(r"(core|extend|basic)\d+", code or "")
                if match and match[1] not in types:
                    types.append(match[1])
            senior_types[word_id] = types
    return [
        WordOut(
            id=word.id,
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
def list_groups(db: DB):
    return [
        GroupSummary(slug=slug, name=name, total=total)
        for slug, name, total in db.execute(
            select(
                VocabularyGroup.slug,
                VocabularyGroup.name,
                func.count(WordGroup.word_id),
            )
            .outerjoin(WordGroup, WordGroup.group_id == VocabularyGroup.id)
            .group_by(VocabularyGroup.id)
            .order_by(VocabularyGroup.id)
        )
    ]


@router.post("/groups/{slug}/words", response_model=WordOut)
def save_word(slug: str, data: WordInput, db: DB):
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
    return serialize_words(db, [db.get(Word, word_id)])[0]


@router.get("/words/random", response_model=RandomWord)
def random_word(
    db: DB,
    group: str = "all",
    exclude_id: int | None = Query(None, ge=1),
):
    query = words_in_group(db, group)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    if total > 1 and exclude_id is not None:
        query = query.where(Word.id != exclude_id)
    word = db.scalar(query.order_by(func.random()).limit(1))
    return RandomWord(
        word=serialize_words(db, [word])[0] if word is not None else None,
        total=total,
    )


@router.get("/words", response_model=WordPage)
def list_words(
    db: DB,
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
            exists().where(
                WordGroup.word_id == Word.id,
                WordGroup.group_id.in_(membership_groups),
            ).correlate(Word)
        )
    if senior_types is not None:
        types = {item.strip() for item in senior_types.split(",")}
        if not types <= {"core", "extend", "basic"}:
            raise HTTPException(422, "Unknown Senior type.")
        senior_id = select(VocabularyGroup.id).where(
            VocabularyGroup.slug == "senior"
        ).scalar_subquery()
        pattern = rf"^({'|'.join(sorted(types))})[0-9]+$"
        query = query.where(
            exists().where(
                WordGroup.word_id == Word.id,
                WordGroup.group_id == senior_id,
                or_(
                    WordGroup.list_code.op("~")(pattern),
                    func.jsonb_path_exists(
                        WordGroup.source_entries,
                        cast('$[*] ? (@.list_code like_regex "' + pattern + '")', JSONPATH),
                    ),
                ),
            ).correlate(Word)
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
            func.row_number()
            .over(order_by=orderings)
            .label("position"),
        ).subquery()
        position = db.scalar(
            select(ranked.c.position).where(ranked.c.word_id == locate_id)
        )
        if position is None:
            raise HTTPException(404, "Word not found in this group.")
        page = (position - 1) // page_size + 1
    words = list(
        db.scalars(
            query.order_by(*orderings)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    )
    return WordPage(
        items=serialize_words(db, words),
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.patch("/words/{word_id}", response_model=WordOut)
def edit_word(word_id: int, data: WordInput, db: DB):
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
    return serialize_words(db, [word])[0]


@router.delete("/words/{word_id}", status_code=204)
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
