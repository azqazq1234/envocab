"""Import rawlist/cet6.txt with Chinese meanings; preview unless --apply is set."""

import argparse
import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine
from app.import_cet4 import import_words, parse_source, resolve_words
from app.models import VocabularyGroup, Word, WordGroup, WordMeaning

SOURCE = Path(__file__).resolve().parents[2] / "rawlist" / "cet6.txt"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    occurrences = parse_source(SOURCE)
    resolved = resolve_words(occurrences)
    print(f"Resolved {len(resolved)} distinct words.")
    if not args.apply:
        return
    with Session(engine) as db, db.begin():
        list(db.scalars(select(VocabularyGroup).order_by(VocabularyGroup.id).with_for_update()))
        list(db.scalars(select(Word).order_by(Word.id).with_for_update()))
        backup = Path(__file__).resolve().parents[1] / "data" / f"before-cet6-import-{uuid4().hex[:10]}.json"
        snapshot = {model.__tablename__: [dict(row) for row in db.execute(select(model.__table__)).mappings()]
                    for model in [Word, WordMeaning, WordGroup, VocabularyGroup]}
        with backup.open("x") as file:
            json.dump({"snapshot": snapshot}, file, ensure_ascii=False, default=str)
        print(f"Backup: {backup}")
        print(json.dumps(import_words(db, occurrences, resolved, group_slug="cet6")))
    print("CET-6 import committed.")


if __name__ == "__main__":
    main()
