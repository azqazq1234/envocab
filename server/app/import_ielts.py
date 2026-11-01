"""Import the 50 numbered lists in rawlist/ielts.txt with Chinese meanings."""

import argparse
import json
import re
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.database import engine
from app.import_cet4 import import_words, resolve_words
from app.models import VocabularyGroup, Word, WordGroup, WordMeaning
from app.vocabulary import MeaningInput, WordInput

SOURCE = Path(__file__).resolve().parents[2] / "rawlist" / "ielts.txt"


def parse_source(path=SOURCE):
    occurrences = {}
    lists = []
    code = None
    expected = None
    count = 0
    position = 0

    def check_count():
        if code is not None and (expected is None or count != expected):
            raise ValueError(f"{code}: expected {expected}, found {count}")

    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("组名："):
            check_count()
            code = line.removeprefix("组名：").strip()
            if not re.fullmatch(r"list\d{2}", code):
                raise ValueError(f"Invalid list heading: {line}")
            lists.append(code)
            expected, count = None, 0
        elif line.startswith("单词数量："):
            if code is None or expected is not None or count:
                raise ValueError(f"Unexpected count heading: {line}")
            expected = int(line.removeprefix("单词数量："))
        else:
            if code is None or expected is None:
                raise ValueError(f"Word before list headings: {line}")
            entry = WordInput(term=line, meanings=[MeaningInput(meaning="校验")])
            count += 1
            position += 1
            occurrences.setdefault(entry.term, []).append({
                "source_term": line, "position": position, "list_code": code,
            })
    check_count()
    if lists != [f"list{i:02d}" for i in range(1, 51)]:
        raise ValueError("Expected consecutive list01–list50 headings")
    return occurrences


def import_ielts_words(db, occurrences, resolved):
    stats = import_words(db, occurrences, resolved, group_slug="ielts")
    group_id = db.scalar(select(VocabularyGroup.id).where(VocabularyGroup.slug == "ielts"))
    word_ids = dict(db.execute(select(Word.term, Word.id).where(Word.term.in_(occurrences))).all())
    for term, sources in occurrences.items():
        db.execute(update(WordGroup).where(
            WordGroup.group_id == group_id, WordGroup.word_id == word_ids[term],
        ).values(list_code=sources[0]["list_code"]))
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    occurrences = parse_source()
    resolved = resolve_words(occurrences)
    print(f"Resolved {len(resolved)} distinct words across 50 IELTS lists.")
    if not args.apply:
        return
    with Session(engine) as db, db.begin():
        list(db.scalars(select(VocabularyGroup).order_by(VocabularyGroup.id).with_for_update()))
        list(db.scalars(select(Word).order_by(Word.id).with_for_update()))
        backup = Path(__file__).resolve().parents[1] / "data" / f"before-ielts-import-{uuid4().hex[:10]}.json"
        snapshot = {model.__tablename__: [dict(row) for row in db.execute(select(model.__table__)).mappings()]
                    for model in [Word, WordMeaning, WordGroup, VocabularyGroup]}
        with backup.open("x") as file:
            json.dump({"snapshot": snapshot}, file, ensure_ascii=False, default=str)
        print(f"Backup: {backup}")
        print(json.dumps(import_ielts_words(db, occurrences, resolved)))
    print("IELTS import committed.")


if __name__ == "__main__":
    main()
