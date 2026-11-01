"""Preview reviewed Junior refinements; --apply backs up and commits them."""

import argparse
import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from app.database import engine
from app.models import VocabularyGroup, Word, WordGroup, WordMeaning
from app.reviewed_vocabulary import LEARNER_ENTRIES, SPELLING_CORRECTIONS
from app.vocabulary import MeaningInput, store_meanings


def meaning_rows(db: Session, word_id: int) -> list[dict]:
    return [
        {"part_of_speech": m.part_of_speech or None, "meaning": m.meaning}
        for m in db.scalars(select(WordMeaning).where(WordMeaning.word_id == word_id).order_by(WordMeaning.id))
    ]


def junior_rows(db: Session):
    return db.execute(
        select(Word, WordGroup).join(WordGroup).join(VocabularyGroup)
        .where(VocabularyGroup.slug == "junior")
        .order_by(WordGroup.position.asc().nulls_last(), Word.id)
    ).all()


def plan_refinement(db: Session) -> dict:
    current = {word.term: word for word, membership in junior_rows(db)}
    renames = []
    for old, new in SPELLING_CORRECTIONS.items():
        if old not in current:
            continue
        if new in current:
            raise ValueError(f"Junior contains both {old} and {new}; review before merging")
        target = db.scalar(select(Word).where(Word.term == new))
        renames.append({"old": old, "new": new, "old_id": current[old].id,
                        "target_id": target.id if target else None})
        current[new] = target or current[old]
        del current[old]
    replacements = []
    for term, word in current.items():
        if term not in LEARNER_ENTRIES:
            continue
        entry = LEARNER_ENTRIES[term]
        validated = [MeaningInput(**item).model_dump() for item in entry["meanings"]]
        if not validated or any(not m["part_of_speech"] for m in validated):
            raise ValueError(f"Invalid reviewed entry: {term}")
        before = meaning_rows(db, word.id)
        if before != validated or word.phonetic != entry["phonetic"]:
            replacements.append({"word_id": word.id, "term": term, "before": before,
                                 "after": validated, "phonetic": entry["phonetic"]})
    return {"renames": renames, "replacements": replacements}


def apply_refinement(db: Session, plan: dict) -> None:
    before_order = [(word.id, word.term, membership.position) for word, membership in junior_rows(db)]
    protected = {
        word.id: (word.term, word.phonetic, meaning_rows(db, word.id))
        for word, membership in junior_rows(db) if word.term in {"march", "turkey"}
    }
    group_id = db.scalar(select(VocabularyGroup.id).where(VocabularyGroup.slug == "junior"))
    id_changes = {}
    for rename in plan["renames"]:
        old = db.get(Word, rename["old_id"])
        if old is None or old.term != rename["old"]:
            raise ValueError("Source spelling changed since preview")
        target = db.get(Word, rename["target_id"]) if rename["target_id"] else None
        if target is None:
            old.term = rename["new"]
        else:
            source_membership = db.get(WordGroup, (old.id, group_id))
            if db.get(WordGroup, (target.id, group_id)) is not None:
                raise ValueError("Destination membership changed since preview")
            db.add(WordGroup(word_id=target.id, group_id=group_id,
                             list_code=source_membership.list_code,
                             position=source_membership.position,
                             source_term=source_membership.source_term,
                             source_entries=source_membership.source_entries))
            db.delete(source_membership)
            id_changes[old.id] = target.id
            db.flush()
            if not db.scalar(select(exists().where(WordGroup.word_id == old.id))):
                db.delete(old)
    db.flush()
    for change in plan["replacements"]:
        word_id = id_changes.get(change["word_id"], change["word_id"])
        word = db.get(Word, word_id)
        db.execute(delete(WordMeaning).where(WordMeaning.word_id == word_id))
        store_meanings(db, word_id, [MeaningInput(**item) for item in change["after"]])
        word.phonetic = change["phonetic"]
    db.flush()
    after = [(word.id, word.term, membership.position) for word, membership in junior_rows(db)]
    expected = [(id_changes.get(word_id, word_id), SPELLING_CORRECTIONS.get(term, term), position)
                for word_id, term, position in before_order]
    if after != expected:
        raise ValueError("Junior count or order changed unexpectedly")
    for word_id, original in protected.items():
        word = db.get(Word, word_id)
        if (word.term, word.phonetic, meaning_rows(db, word_id)) != original:
            raise ValueError("Protected word changed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with Session(engine) as db, db.begin():
        if args.apply:
            db.scalar(select(VocabularyGroup).where(VocabularyGroup.slug == "junior").with_for_update())
        plan = plan_refinement(db)
        print(f"Spelling corrections: {len(plan['renames'])}; meaning replacements: {len(plan['replacements'])}.")
        if args.apply and (plan["renames"] or plan["replacements"]):
            backup = Path(__file__).resolve().parents[1] / "data" / f"before-junior-refinement-{uuid4().hex[:10]}.json"
            snapshot = {model.__tablename__: [dict(row) for row in db.execute(select(model.__table__)).mappings()]
                        for model in [Word, WordMeaning, WordGroup, VocabularyGroup]}
            with backup.open("x") as file:
                json.dump({"snapshot": snapshot, "plan": plan}, file, ensure_ascii=False, default=str)
            apply_refinement(db, plan)
            remaining = plan_refinement(db)
            if remaining["renames"] or remaining["replacements"]:
                raise ValueError("Refinement is not idempotent")
            print(f"Backup: {backup}")
    if args.apply:
        print("Committed; Junior order preserved; march and turkey unchanged.")


if __name__ == "__main__":
    main()
