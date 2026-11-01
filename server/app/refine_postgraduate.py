"""Apply the reviewed Postgraduate meanings, backing up and verifying shared data."""

import argparse
import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database import engine
from app.models import VocabularyGroup, Word, WordGroup
from app.refine_project import apply_refinement, plan_refinement, snapshot
from app.reviewed_vocabulary import POSTGRADUATE_LEARNER_ENTRIES

DATA = Path(__file__).resolve().parents[1] / "data"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with Session(engine) as db, db.begin():
        if args.apply:
            db.execute(text("LOCK TABLE words, word_meanings, word_groups, vocabulary_groups IN SHARE ROW EXCLUSIVE MODE"))
        entries = POSTGRADUATE_LEARNER_ENTRIES
        source = {w["term"]: w for w in json.loads((DATA / "postgraduate-review-input.json").read_text())}
        group_terms = set(db.scalars(select(Word.term).join(WordGroup).join(VocabularyGroup)
                                    .where(VocabularyGroup.slug == "postgraduate")))
        if not entries.keys() <= group_terms or not entries.keys() <= source.keys():
            raise ValueError("Reviewed entries must belong to the Postgraduate source snapshot")
        plan = plan_refinement(db, aliases={}, entries=entries)
        for change in plan["replacements"]:
            original = source[change["term"]]
            if (original["id"] != change["word_id"] or original["meanings"] != change["before"]
                    or original["phonetic"] != change["before_phonetic"]):
                raise ValueError(f"Word edited after review: {change['term']}")
        print(f"Meaning replacements: {len(plan['replacements'])}; renames: 0.")
        if not args.apply or not plan["replacements"]:
            return
        backup = DATA / f"before-postgraduate-review-{uuid4().hex[:10]}.json"
        with backup.open("x") as file:
            json.dump({"snapshot": snapshot(db), "plan": plan}, file, ensure_ascii=False, default=str)
        result = apply_refinement(db, plan, aliases={}, entries=entries)
        result["backup"] = str(backup)
        result["plan"] = plan
    result["committed"] = True
    (DATA / "postgraduate-refinement-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "plan"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
