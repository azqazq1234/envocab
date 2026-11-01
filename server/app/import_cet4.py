"""Import rawlist/cet4.txt in source order, preserving existing shared meanings."""

import argparse
import json
import re
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database import engine
from app.dictionary import lookup_word
from app.models import VocabularyGroup, Word, WordGroup, WordMeaning
from app.vocabulary import MeaningInput, WordInput, store_meanings

SOURCE = Path(__file__).resolve().parents[2] / "rawlist" / "cet4.txt"


def parse_source(path=SOURCE, *, split_coverage_lettering=False):
    occurrences = {}
    for position, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        source_term = line.strip()
        if not source_term:
            continue
        terms = [source_term]
        if source_term == "coverage lettering":
            if not split_coverage_lettering:
                raise ValueError("Review 'coverage lettering'; use --split-coverage-lettering to split it")
            terms = ["coverage", "lettering"]
        for term in terms:
            # Validate without changing the case of source headwords.
            entry = WordInput(term=term, meanings=[MeaningInput(meaning="校验")])
            occurrences.setdefault(entry.term, []).append({
                "source_term": source_term, "position": position,
            })
    if not occurrences:
        raise ValueError("Empty source file")
    return occurrences


def resolve_words(occurrences):
    resolved = {}
    for term in occurrences:
        if term == "welcome home":
            resolved[term] = WordInput(term=term, meanings=[
                MeaningInput(part_of_speech="phrase", meaning="欢迎回家"),
            ])
            continue
        entry = lookup_word(term)
        if entry is None or not any(re.search(r"[\u4e00-\u9fff]", m.meaning) for m in entry.meanings):
            raise ValueError(f"Missing Chinese meanings: {term}")
        resolved[term] = WordInput(
            term=term, phonetic=entry.phonetic,
            meanings=[MeaningInput(**m.model_dump()) for m in entry.meanings],
        )
    return resolved


def import_words(db, occurrences, resolved, *, group_slug="cet4"):
    group = db.scalar(select(VocabularyGroup).where(VocabularyGroup.slug == group_slug))
    if group is None:
        raise ValueError(f"Vocabulary group does not exist: {group_slug}")
    stats = {"new_words": 0, "new_memberships": 0, "meanings_filled": 0}
    for term, sources in occurrences.items():
        entry = resolved[term]
        word = db.scalar(select(Word).where(Word.term == term))
        if word is None:
            word = Word(term=term, phonetic=entry.phonetic)
            db.add(word)
            db.flush()
            stats["new_words"] += 1
        meanings = list(db.scalars(select(WordMeaning).where(WordMeaning.word_id == word.id)))
        if not any(re.search(r"[\u4e00-\u9fff]", m.meaning) for m in meanings):
            store_meanings(db, word.id, entry.meanings)
            stats["meanings_filled"] += 1
        metadata = {
            "position": sources[0]["position"],
            "source_term": sources[0]["source_term"],
            "source_entries": sources,
        }
        if db.get(WordGroup, (word.id, group.id)) is None:
            stats["new_memberships"] += 1
        db.execute(insert(WordGroup).values(word_id=word.id, group_id=group.id, **metadata)
                   .on_conflict_do_update(index_elements=[WordGroup.word_id, WordGroup.group_id], set_=metadata))
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--split-coverage-lettering", action="store_true")
    args = parser.parse_args()
    occurrences = parse_source(split_coverage_lettering=args.split_coverage_lettering)
    resolved = resolve_words(occurrences)
    print(f"Resolved {len(resolved)} distinct words.")
    if not args.apply:
        return
    with Session(engine) as db, db.begin():
        list(db.scalars(select(VocabularyGroup).order_by(VocabularyGroup.id).with_for_update()))
        list(db.scalars(select(Word).order_by(Word.id).with_for_update()))
        backup = Path(__file__).resolve().parents[1] / "data" / f"before-cet4-import-{uuid4().hex[:10]}.json"
        snapshot = {model.__tablename__: [dict(row) for row in db.execute(select(model.__table__)).mappings()]
                    for model in [Word, WordMeaning, WordGroup, VocabularyGroup]}
        with backup.open("x") as file:
            json.dump({"snapshot": snapshot}, file, ensure_ascii=False, default=str)
        print(f"Backup: {backup}")
        print(json.dumps(import_words(db, occurrences, resolved)))
    print("CET-4 import committed.")


if __name__ == "__main__":
    main()
