"""Preview or apply reviewed Junior sense corrections: --apply to commit."""

import argparse
import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import engine
from app.meaning_corrections import EXCLUDED_TERMS, RULES, correct_meanings
from app.models import VocabularyGroup, Word, WordGroup, WordMeaning
from app.vocabulary import MeaningInput, store_meanings


def plan_corrections(db: Session) -> list[dict]:
    words = db.scalars(
        select(Word).join(WordGroup).join(VocabularyGroup)
        .where(VocabularyGroup.slug == "junior").order_by(Word.id)
    ).all()
    plans = []
    for word in words:
        if word.term in EXCLUDED_TERMS:
            continue
        rows = list(db.scalars(
            select(WordMeaning).where(WordMeaning.word_id == word.id).order_by(WordMeaning.id)
        ))
        if not any(not row.part_of_speech for row in rows):
            continue
        before = [{"id": row.id, "part_of_speech": row.part_of_speech, "meaning": row.meaning} for row in rows]
        corrected = correct_meanings(word.term, before)
        if not corrected or any(not item.get("part_of_speech") for item in corrected):
            raise ValueError(f"Unreviewed or empty senses remain for {word.term}")
        rules = {rule["original"]: rule["replacement"] for rule in RULES.get(word.term, [])}
        changed = [row for row in rows if not row.part_of_speech and row.meaning in rules]
        replacement = [MeaningInput(**item) for row in changed for item in rules[row.meaning]]
        plans.append({
            "word_id": word.id, "term": word.term, "before": before,
            "remove_ids": [row.id for row in changed],
            "replacement": [item.model_dump() for item in replacement],
        })
    return plans


def apply_corrections(db: Session, plans: list[dict]) -> None:
    for plan in plans:
        db.execute(delete(WordMeaning).where(WordMeaning.id.in_(plan["remove_ids"])))
        store_meanings(db, plan["word_id"], [MeaningInput(**item) for item in plan["replacement"]])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with Session(engine) as db, db.begin():
        plans = plan_corrections(db)
        print(f"Reviewed {len(plans)} words / {sum(len(p['remove_ids']) for p in plans)} unclassified senses.")
        if args.apply and plans:
            backup = Path(__file__).resolve().parents[1] / "data" / f"before-junior-meaning-fix-{uuid4().hex[:10]}.json"
            with backup.open("x") as file:
                json.dump(plans, file, ensure_ascii=False, indent=2)
            apply_corrections(db, plans)
            if plan_corrections(db):
                raise ValueError("Corrections did not clear all reviewed missing parts of speech")
            print(f"Backup: {backup}")
    if args.apply:
        print("Committed; march and turkey were excluded.")


if __name__ == "__main__":
    main()
