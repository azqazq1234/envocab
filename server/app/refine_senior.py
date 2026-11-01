"""Preview Senior learner corrections; --apply backs up and commits atomically."""

import argparse
import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from app.database import engine
from app.models import VocabularyGroup, Word, WordGroup, WordMeaning
from app.refine_junior import meaning_rows
from app.reviewed_vocabulary import SENIOR_LEARNER_ENTRIES
from app.vocabulary import MeaningInput, store_meanings

SENIOR_CORRECTIONS = {"Run": "run"}
PROTECTED = {"march", "turkey"}


def senior_rows(db: Session):
    return db.execute(
        select(Word, WordGroup).join(WordGroup).join(VocabularyGroup)
        .where(VocabularyGroup.slug == "senior")
        .order_by(WordGroup.position.asc().nulls_last(), Word.id)
    ).all()


def plan_refinement(db: Session) -> dict:
    current = {word.term: word for word, _ in senior_rows(db)}
    renames = []
    for old, new in SENIOR_CORRECTIONS.items():
        if old not in current:
            continue
        if new in current:
            raise ValueError(f"Senior already contains both {old} and {new}; review memberships")
        target = db.scalar(select(Word).where(Word.term == new))
        source = current.pop(old)
        renames.append({"old": old, "new": new, "old_id": source.id,
                        "target_id": target.id if target else None})
        current[new] = target or source
    replacements = []
    for term, word in current.items():
        if term in PROTECTED or term not in SENIOR_LEARNER_ENTRIES:
            continue
        entry = SENIOR_LEARNER_ENTRIES[term]
        after = [MeaningInput(**m).model_dump() for m in entry["meanings"]]
        if not after or any(not m["part_of_speech"] for m in after):
            raise ValueError(f"Reviewed entry lacks a meaning or POS: {term}")
        before = meaning_rows(db, word.id)
        if before != after or word.phonetic != entry["phonetic"]:
            replacements.append({"word_id": word.id, "term": term, "before": before,
                                 "before_phonetic": word.phonetic, "after": after,
                                 "phonetic": entry["phonetic"]})
    return {"renames": renames, "replacements": replacements}


def membership_state(db: Session):
    """Include raw source metadata, not just the visible ordering."""
    return {
        (row.group_id, row.word_id): (row.list_code, row.position, row.source_term, row.source_entries)
        for row in db.scalars(select(WordGroup))
    }


def apply_refinement(db: Session, plan: dict) -> None:
    # Reject stale previews before performing any mutation.
    if plan != plan_refinement(db):
        raise ValueError("Vocabulary changed since the preview; regenerate the plan")
    original_memberships = membership_state(db)
    protected = {
        word.id: (word.term, word.phonetic, meaning_rows(db, word.id))
        for word in db.scalars(select(Word).where(Word.term.in_(PROTECTED)))
    }
    group_id = db.scalar(select(VocabularyGroup.id).where(VocabularyGroup.slug == "senior"))
    id_changes = {}
    for rename in plan["renames"]:
        old = db.get(Word, rename["old_id"])
        if old is None or old.term != rename["old"]:
            raise ValueError("Renamed source word changed")
        target = db.get(Word, rename["target_id"]) if rename["target_id"] else None
        if target is None:
            old.term = rename["new"]
        else:
            if target.term != rename["new"]:
                raise ValueError("Rename target changed")
            source = db.get(WordGroup, (old.id, group_id))
            if source is None or db.get(WordGroup, (target.id, group_id)) is not None:
                raise ValueError("Rename membership changed")
            db.add(WordGroup(word_id=target.id, group_id=group_id,
                             list_code=source.list_code, position=source.position,
                             source_term=source.source_term, source_entries=source.source_entries))
            db.delete(source)
            id_changes[old.id] = target.id
            db.flush()
            if not db.scalar(select(exists().where(WordGroup.word_id == old.id))):
                db.delete(old)
    db.flush()
    for change in plan["replacements"]:
        word_id = id_changes.get(change["word_id"], change["word_id"])
        word = db.get(Word, word_id)
        db.execute(delete(WordMeaning).where(WordMeaning.word_id == word_id))
        store_meanings(db, word_id, [MeaningInput(**m) for m in change["after"]])
        word.phonetic = change["phonetic"]
    db.flush()
    expected = {
        (group, id_changes.get(word_id, word_id) if group == group_id else word_id): metadata
        for (group, word_id), metadata in original_memberships.items()
    }
    if membership_state(db) != expected:
        raise ValueError("Group membership, source metadata or ordering changed unexpectedly")
    for word_id, state in protected.items():
        word = db.get(Word, word_id)
        if (word.term, word.phonetic, meaning_rows(db, word_id)) != state:
            raise ValueError("Protected word changed")
    if plan_refinement(db) != {"renames": [], "replacements": []}:
        raise ValueError("Senior corrections are not idempotent")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with Session(engine) as db, db.begin():
        if args.apply:
            # The application also takes word locks for editing. Lock all current
            # vocabulary rows to keep this one-off migration internally consistent.
            list(db.scalars(select(VocabularyGroup).order_by(VocabularyGroup.id).with_for_update()))
            list(db.scalars(select(Word).order_by(Word.id).with_for_update()))
            list(db.scalars(select(WordGroup).with_for_update()))
        plan = plan_refinement(db)
        print(f"Renames: {len(plan['renames'])}; meaning replacements: {len(plan['replacements'])}.")
        if args.apply and (plan["renames"] or plan["replacements"]):
            directory = Path(__file__).resolve().parents[1] / "data"
            directory.mkdir(exist_ok=True)
            backup = directory / f"before-senior-refinement-{uuid4().hex[:10]}.json"
            snapshot = {model.__tablename__: [dict(row) for row in db.execute(select(model.__table__)).mappings()]
                        for model in [Word, WordMeaning, WordGroup, VocabularyGroup]}
            with backup.open("x") as file:
                json.dump({"snapshot": snapshot, "plan": plan}, file, ensure_ascii=False, default=str)
            apply_refinement(db, plan)
            print(f"Backup: {backup}")
    if args.apply:
        print("Committed; all group positions and source metadata preserved; march/turkey unchanged.")


if __name__ == "__main__":
    main()
