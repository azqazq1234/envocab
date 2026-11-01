from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine
from app.dictionary import lookup_word
from app.models import VocabularyGroup, Word, WordGroup
from app.refine_project import apply_refinement, meanings, plan_refinement
from app.reviewed_vocabulary import canonical_term
from app.vocabulary import MeaningInput, store_meanings


@pytest.fixture
def db():
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            try:
                yield session
            finally:
                transaction.rollback()


def make_word(db, term):
    word = Word(term=term, phonetic="before")
    db.add(word)
    db.flush()
    store_meanings(db, word.id, [MeaningInput(part_of_speech="noun", meaning="原释义")])
    return word


@pytest.mark.parametrize("overlapping_group", [False, True])
def test_project_merge_preserves_all_groups_and_source_occurrences(db, overlapping_group):
    term = "project-" + uuid4().hex.translate(str.maketrans("0123456789", "ghijklmnop"))
    target, old = make_word(db, term), make_word(db, term.upper())
    groups = list(db.scalars(select(VocabularyGroup.id).order_by(VocabularyGroup.id).limit(2)))
    first, second = groups
    source = {"position": 100002, "list_code": "core01", "source_term": old.term}
    target_source = {"position": 100001, "list_code": "basic01", "source_term": target.term}
    db.add(WordGroup(word_id=old.id, group_id=first, **source, source_entries=[source]))
    db.add(WordGroup(word_id=target.id, group_id=first if overlapping_group else second,
                     **target_source, source_entries=[target_source]))
    # The old identity also appears in another group when the first overlaps.
    if overlapping_group:
        db.add(WordGroup(word_id=old.id, group_id=second, **source, source_entries=[source]))
    db.flush()
    old_id = old.id
    aliases = {old.term: target.term}
    entries = {target.term: {"phonetic": "after", "meanings": [{"part_of_speech": "noun", "meaning": "修正释义"}]}}
    plan = plan_refinement(db, aliases, entries)
    result = apply_refinement(db, plan, aliases, entries)
    assert result["merged_duplicates"] == 1
    assert db.get(Word, old_id) is None
    assert meanings(db, target.id) == entries[target.term]["meanings"]
    membership = db.get(WordGroup, (target.id, first))
    if overlapping_group:
        assert membership.position == 100001
        assert membership.source_entries == [target_source, source]
    else:
        assert membership.position == 100002
        assert membership.source_entries == [source]
    assert db.get(WordGroup, (target.id, second)) is not None
    assert plan_refinement(db, aliases, entries) == {"renames": [], "replacements": []}


def test_project_rename_without_existing_target_retains_id(db):
    word = make_word(db, "PROJECT-" + uuid4().hex)
    word_id = word.id
    target = word.term.lower()
    aliases = {word.term: target}
    plan = plan_refinement(db, aliases, {})
    apply_refinement(db, plan, aliases, {})
    assert db.get(Word, word_id).term == target


def test_project_refinement_rejects_stale_plan_before_any_write(db):
    word = make_word(db, "project-" + uuid4().hex)
    entries = {word.term: {"phonetic": "after", "meanings": [{"part_of_speech": "noun", "meaning": "修正释义"}]}}
    plan = plan_refinement(db, {}, entries)
    word.phonetic = "a newer user edit"
    db.flush()
    with pytest.raises(ValueError, match="changed since preview"):
        apply_refinement(db, plan, {}, entries)
    assert word.phonetic == "a newer user edit"
    assert meanings(db, word.id)[0]["meaning"] == "原释义"


@pytest.mark.parametrize("term,required,forbidden", [
    ("heroine", "女主角", "海洛因"),
    ("supersonic", "超音速", "超声"),
    ("Thanksgiving", "感恩节", "感谢"),
    ("hectic", "繁忙", "肺病"),
    ("mundane", "平凡", "宇宙"),
    ("inmate", "囚犯", "内在"),
    ("obscene", "淫秽", "海洋"),
    ("collaboration", "协作", "奸细"),
    ("corporation", "公司", "合作"),
    ("march", "行军", "三月"),
    ("turkey", "火鸡", "土耳其"),
])
def test_project_review_prevents_known_mistranslations(term, required, forbidden):
    entry = lookup_word(term)
    text = "；".join(m.meaning for m in entry.meanings)
    assert required in text and forbidden not in text
    assert all(m.part_of_speech for m in entry.meanings)


def test_case_normalization_is_explicit_and_preserves_distinct_pairs():
    assert canonical_term("waX") == "wax"
    assert canonical_term("Depreciate") == "depreciate"
    for term in ["US", "us", "China", "china", "May", "may", "Miss", "miss", "Catholic", "catholic", "BOOK"]:
        assert canonical_term(term) == term
    assert "三月" in lookup_word("March").meanings[0].meaning
    assert "土耳其" in lookup_word("Turkey").meanings[0].meaning


def test_source_imports_resolve_reviewed_pos_and_preserve_raw_spelling():
    from app.import_cet4 import parse_source, resolve_words
    from app.import_ielts import parse_source as parse_ielts
    from app.import_senior import parse_source as parse_senior
    from app.import_senior import resolve_words as resolve_senior

    cet4 = parse_source(split_coverage_lettering=True)
    assert cet4["wax"][0]["source_term"] == "waX"
    for occurrences in [cet4, parse_source(path=Path(__file__).resolve().parents[2] / "rawlist/cet6.txt"), parse_ielts()]:
        assert all(m.part_of_speech for entry in resolve_words(occurrences).values() for m in entry.meanings)
    assert all(m.part_of_speech for entry in resolve_senior(parse_senior()) for m in entry.meanings)
