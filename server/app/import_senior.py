"""Import the ordered Senior source file using the local Chinese dictionary.

Run with: uv run python -m app.import_senior [--apply]
All dictionary entries are resolved before writing; reruns reuse memberships.
"""

import argparse
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

from sqlalchemy import delete, exists, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database import engine
from app.dictionary import CASE_ENTRIES, lookup_word
from app.models import VocabularyGroup, Word, WordGroup, WordMeaning
from app.reviewed_vocabulary import canonical_term
from app.vocabulary import MeaningInput, WordInput, store_meanings

SOURCE = Path(__file__).resolve().parents[2] / "rawlist" / "senior.txt"
HEADER = re.compile(r"(core(?:list)?|extend|basic)(\d+)：(\d+) 个词条")
SUPPLEMENT = Path(__file__).with_name("senior_supplement.json")


@dataclass(frozen=True)
class SourceWord:
    source_term: str
    term: str
    list_code: str
    position: int


def parse_source(path: Path = SOURCE) -> list[SourceWord]:
    words = []
    groups = []
    expected = 0
    count = 0
    code = None
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        match = HEADER.fullmatch(line)
        if match:
            if code is not None and count != expected:
                raise ValueError(f"{code}: expected {expected} words, got {count}")
            kind = "core" if match[1].startswith("core") else match[1]
            code = f"{kind}{int(match[2]):02d}"
            groups.append(code)
            expected, count = int(match[3]), 0
            continue
        if code is None:
            raise ValueError("Word before first list heading")
        # Parentheses carry inflections/spelling variants, not part of the headword.
        term = re.sub(r"\s*\([^)]*\)$", "", line)
        term = re.sub(r"\s+(?:linking|modal)$", "", term)
        term = unicodedata.normalize("NFKD", term.replace("’", "'")).encode(
            "ascii", "ignore"
        ).decode()
        words.append(SourceWord(line, canonical_term(term), code, len(words) + 1))
        count += 1
    core_groups = [f"core{i:02d}" for i in range(1, 44)]
    extend_count = sum(code.startswith("extend") for code in groups)
    extend_groups = [f"extend{i:02d}" for i in range(1, extend_count + 1)]
    basic_count = sum(code.startswith("basic") for code in groups)
    basic_groups = [f"basic{i:02d}" for i in range(1, basic_count + 1)]
    if groups != core_groups + extend_groups + basic_groups or count != expected:
        raise ValueError("Expected consecutive core/extend/basic lists with matching word counts")
    return words


def resolve_words(words: list[SourceWord]) -> list[WordInput]:
    supplements = json.loads(SUPPLEMENT.read_text())
    resolved = []
    missing = []
    for word in words:
        entry = lookup_word(word.term)
        if entry is None and word.term == "sideroad":
            entry = lookup_word("side road")
        if entry is None:
            if word.term in supplements:
                resolved.append(WordInput(term=word.term, **supplements[word.term]["entry"]))
                continue
            missing.append(word.source_term)
            continue
        resolved.append(
            WordInput(
                term=word.term,
                phonetic=entry.phonetic,
                meanings=[MeaningInput(**m.model_dump()) for m in entry.meanings],
            )
        )
    if missing:
        raise ValueError(f"Missing dictionary entries: {', '.join(missing)}")
    return resolved


def import_words(db: Session, words: list[SourceWord], data: list[WordInput]) -> None:
    if len(words) != len(data):
        raise ValueError("Every source word must have a dictionary entry")
    group_id = db.scalar(
        select(VocabularyGroup.id).where(VocabularyGroup.slug == "senior")
    )
    if group_id is None:
        raise ValueError("Senior vocabulary group does not exist")
    occurrences: dict[str, list[dict]] = {}
    for source in words:
        occurrences.setdefault(source.term, []).append({
            key: value for key, value in asdict(source).items() if key != "term"
        })
    imported = set()
    for source, entry in zip(words, data, strict=True):
        if source.term in imported:
            continue
        imported.add(source.term)
        word_id = db.scalar(select(Word.id).where(Word.term == entry.term))
        if word_id is None:
            word_id = db.scalar(
                insert(Word)
                .values(term=entry.term, phonetic=entry.phonetic)
                .on_conflict_do_nothing(index_elements=[Word.term])
                .returning(Word.id)
            )
            if word_id is None:
                word_id = db.scalar(select(Word.id).where(Word.term == entry.term))
        store_meanings(db, word_id, entry.meanings)
        metadata = {
            "list_code": source.list_code,
            "position": source.position,
            "source_term": source.source_term,
            "source_entries": occurrences[source.term],
        }
        db.execute(
            insert(WordGroup)
            .values(word_id=word_id, group_id=group_id, **metadata)
            .on_conflict_do_update(
                index_elements=[WordGroup.word_id, WordGroup.group_id], set_=metadata
            )
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Commit the import")
    parser.add_argument("--sync-source", action="store_true", help="Reconcile imported Senior spellings with the source and split case-specific meanings")
    args = parser.parse_args()
    words = parse_source()
    data = resolve_words(words)
    print(f"Resolved {len(words)} words across {len({w.list_code for w in words})} lists.")
    if args.apply:
        with Session(engine) as db, db.begin():
            import_words(db, words, data)
            if args.sync_source:
                reconcile_source(db, words)
        print("Senior import committed.")


def reconcile_source(db: Session, words: list[SourceWord]) -> None:
    """Remove obsolete imported memberships; retain other groups and manual entries."""
    group_id = db.scalar(select(VocabularyGroup.id).where(VocabularyGroup.slug == "senior"))
    desired = {word.term for word in words}
    obsolete = list(db.scalars(
        select(WordGroup).join(Word, Word.id == WordGroup.word_id).where(
            WordGroup.group_id == group_id,
            WordGroup.source_entries.is_not(None),
            Word.term.not_in(desired),
        )
    ))
    for membership in obsolete:
        word_id = membership.word_id
        db.delete(membership)
        db.flush()
        if not db.scalar(select(exists().where(WordGroup.word_id == word_id))):
            db.delete(db.get(Word, word_id))
    # Replace previously mixed meanings for the explicitly reviewed case pairs.
    for term in CASE_ENTRIES:
        word = db.scalar(select(Word).where(Word.term == term))
        if word is None:
            continue
        entry = lookup_word(term)
        db.execute(delete(WordMeaning).where(WordMeaning.word_id == word.id))
        store_meanings(db, word.id, [MeaningInput(**m.model_dump()) for m in entry.meanings])
        word.phonetic = entry.phonetic


if __name__ == "__main__":
    main()
