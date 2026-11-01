"""Merge COCA sources without repeated spellings: Excel lemmas first, GitHub next."""

import argparse
import json
import re
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.database import engine
from app.dictionary import POS_NAMES, lookup_word
from app.import_cet4 import import_words
from app.models import VocabularyGroup, Word, WordGroup, WordMeaning
from app.refine_project import snapshot
from app.reviewed_vocabulary import canonical_term
from app.vocabulary import MeaningInput, WordInput

SOURCE = Path(__file__).resolve().parents[2] / "rawlist" / "coca"
DATA = Path(__file__).resolve().parents[1] / "data"
SPELLING_FIXES = {"n''t": "n't", "o''clock": "o'clock", "y''all": "y'all", "saut��": "saute"}


def parse_source(source=SOURCE, *, include_excluded=False):
    excel = json.loads((source / "excel-lemmas.json").read_text())["entries"]
    github = json.loads((source / "github-entries.json").read_text())["entries"]
    headwords = json.loads((source / "headwords.json").read_text())
    occurrences = {}
    for name, rows, expected in [("excel-lemmas", excel, 5050), ("github", github, 20200)]:
        if [r["rank"] for r in rows] != list(range(1, expected + 1)):
            raise ValueError(f"Unexpected {name} ranks")
        for row in rows:
            term = canonical_term(SPELLING_FIXES.get(row["term"], row["term"]))
            headword = headwords[term.casefold()]
            validated = WordInput(term=headword, meanings=[MeaningInput(meaning="校验")])
            if validated.term != headword:
                raise ValueError(f"Headword mapping is stale: {headword}")
            if headword not in occurrences:
                occurrences[headword] = []
            entries = occurrences[headword]
            entries.append({
                "position": entries[0]["position"] if entries else len(occurrences),
                "source_term": row["term"], "source_rank": row["rank"],
                "list_code": name,
                **({"source_pos": row["pos"], "frequency": row["frequency"]} if name == "excel-lemmas"
                   else {"source_file": row["file"]}),
            })
    if len(occurrences) != len({t.casefold() for t in occurrences}):
        raise ValueError("Case-insensitive duplicate headwords")
    preferences = json.loads((source / "spelling-preferences.json").read_text())
    if not set(preferences.values()) <= occurrences.keys():
        raise ValueError("A preferred COCA spelling is missing from the source")
    if not include_excluded:
        # Retain existing positions and metadata; these are removals, not merges.
        occurrences = {term: entries for term, entries in occurrences.items() if term not in preferences}
    return occurrences


def github_meanings(gloss):
    """Read explicitly labelled source glosses; do not guess unknown POS."""
    meanings = []
    for match in re.finditer(r"([A-Za-z]+)\.\s*(\[)", gloss):
        try:
            values, _ = json.JSONDecoder().raw_decode(gloss[match.start(2):])
        except json.JSONDecodeError:
            continue
        pos = POS_NAMES.get(match[1].lower())
        if pos and isinstance(values, list):
            chinese = [s.strip() for s in values if isinstance(s, str) and re.search(r"[\u4e00-\u9fff]", s)]
            if chinese:
                meanings.append(MeaningInput(part_of_speech=pos, meaning="；".join(dict.fromkeys(chinese))))
    return meanings


def resolve_words(db, occurrences):
    supplements_path = Path(__file__).with_name("coca_supplement.json")
    supplements = json.loads(supplements_path.read_text()) if supplements_path.exists() else {}
    github = json.loads((SOURCE / "github-entries.json").read_text())["entries"]
    github_by_rank = {r["rank"]: r for r in github}
    existing = {w.term: w for w in db.scalars(select(Word))}
    saved_meanings = {}
    for m in db.scalars(select(WordMeaning).order_by(WordMeaning.id)):
        saved_meanings.setdefault(m.word_id, []).append(
            MeaningInput(part_of_speech=m.part_of_speech or None, meaning=m.meaning))
    resolved, missing, methods = {}, [], {}
    for term, sources in occurrences.items():
        word = existing.get(term)
        stored = saved_meanings.get(word.id, []) if word else []
        if any(re.search(r"[\u4e00-\u9fff]", m.meaning) for m in stored):
            resolved[term] = WordInput(term=term, phonetic=word.phonetic, meanings=stored)
            methods[term] = "existing"
            continue
        if term in supplements:
            resolved[term] = WordInput(term=term, **supplements[term])
            methods[term] = "supplement"
            continue
        entry = lookup_word(term)
        if entry and any(re.search(r"[\u4e00-\u9fff]", m.meaning) for m in entry.meanings):
            resolved[term] = WordInput(term=term, phonetic=entry.phonetic,
                                       meanings=[MeaningInput(**m.model_dump()) for m in entry.meanings])
            methods[term] = "dictionary"
            continue
        for source in sources:
            if source["list_code"] != "github":
                continue
            row = github_by_rank[source["source_rank"]]
            meanings = github_meanings(row["gloss"])
            if meanings:
                phonetic = re.search(r"\[([^\]]+)\]", row["phonetic"])
                resolved[term] = WordInput(term=term, phonetic=phonetic[1] if phonetic else "", meanings=meanings)
                methods[term] = "github"
                break
        else:
            missing.append(term)
    return resolved, missing, methods


def import_coca_words(db, occurrences, resolved):
    group = db.scalar(select(VocabularyGroup).where(VocabularyGroup.slug == "coca"))
    if group is None:
        group = VocabularyGroup(slug="coca", name="COCA")
        db.add(group)
        db.flush()
    stats = import_words(db, occurrences, resolved, group_slug="coca")
    word_ids = dict(db.execute(select(Word.term, Word.id).where(Word.term.in_(occurrences))).all())
    for code in {sources[0]["list_code"] for sources in occurrences.values()}:
        ids = [word_ids[term] for term, sources in occurrences.items() if sources[0]["list_code"] == code]
        db.execute(update(WordGroup).where(WordGroup.group_id == group.id, WordGroup.word_id.in_(ids))
                   .values(list_code=code).execution_options(synchronize_session=False))
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    occurrences = parse_source()
    with Session(engine) as db, db.begin():
        if args.apply:
            db.execute(text("LOCK TABLE words, word_meanings, word_groups, vocabulary_groups IN SHARE ROW EXCLUSIVE MODE"))
        resolved, missing, methods = resolve_words(db, occurrences)
        report = {"words": len(occurrences), "resolved": len(resolved), "missing": missing,
                  "excel_prefix": sum(s[0]["list_code"] == "excel-lemmas" for s in occurrences.values()),
                  "github_appended": sum(s[0]["list_code"] == "github" for s in occurrences.values()),
                  "resolution_counts": {name: list(methods.values()).count(name) for name in set(methods.values())}}
        (DATA / "coca-import-preview.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(report, ensure_ascii=False))
        if missing:
            raise ValueError("Resolve all missing Chinese meanings before importing")
        if not args.apply:
            return
        backup = DATA / f"before-coca-import-{uuid4().hex[:10]}.json"
        with backup.open("x") as file:
            json.dump({"snapshot": snapshot(db)}, file, ensure_ascii=False, default=str)
        report["backup"] = str(backup)
        report["stats"] = import_coca_words(db, occurrences, resolved)
    report["committed"] = True
    (DATA / "coca-import-result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
