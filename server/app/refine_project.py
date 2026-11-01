"""Apply the reviewed project vocabulary plan, with a full backup and invariants."""

import argparse
import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.database import engine
from app.models import VocabularyGroup, Word, WordGroup, WordMeaning
from app.reviewed_vocabulary import (
    PROJECT_LEARNER_ENTRIES,
    PROJECT_SPELLING_CORRECTIONS,
)
from app.vocabulary import MeaningInput, store_meanings

DATA = Path(__file__).resolve().parents[1] / "data"
MODELS = [Word, WordMeaning, WordGroup, VocabularyGroup]


def snapshot(db):
    return {m.__tablename__: [dict(row) for row in db.execute(select(m.__table__)).mappings()] for m in MODELS}


def meanings(db, word_id):
    return [{"part_of_speech": m.part_of_speech, "meaning": m.meaning}
            for m in db.scalars(select(WordMeaning).where(WordMeaning.word_id == word_id).order_by(WordMeaning.id))]


def plan_refinement(db, aliases=None, entries=None):
    aliases = PROJECT_SPELLING_CORRECTIONS if aliases is None else aliases
    entries = PROJECT_LEARNER_ENTRIES if entries is None else entries
    words = {w.term: w for w in db.scalars(select(Word))}
    renames = [{"old": old, "new": new, "old_id": words[old].id,
                "target_id": words[new].id if new in words else words[old].id}
               for old, new in aliases.items() if old in words]
    assert all(new not in aliases for new in aliases.values()), "Alias chains are not supported"
    desired = {aliases.get(term, term): word for term, word in words.items()}
    for term in list(desired):
        if term in words:
            desired[term] = words[term]
    replacements = []
    for term, word in desired.items():
        if term not in entries:
            continue
        entry = entries[term]
        validated = [MeaningInput(**m).model_dump() for m in entry["meanings"]]
        if not validated or any(not m["part_of_speech"] for m in validated):
            raise ValueError(f"Incomplete reviewed entry: {term}")
        before = meanings(db, word.id)
        if before != validated or word.phonetic != entry["phonetic"]:
            replacements.append({"term": term, "word_id": word.id, "before": before,
                                 "before_phonetic": word.phonetic, "after": validated,
                                 "phonetic": entry["phonetic"]})
    return {"renames": renames, "replacements": replacements}


def membership_metadata(m):
    return {"position": m.position, "list_code": m.list_code,
            "source_term": m.source_term, "source_entries": m.source_entries}


def combine_metadata(left, right):
    """Preserve every source occurrence if aliases happen to share a group."""
    first = min([left, right], key=lambda m: (m["position"] is None, m["position"] or 0))
    occurrences = list(left["source_entries"] or [])
    for entry in right["source_entries"] or []:
        if entry not in occurrences:
            occurrences.append(entry)
    occurrences.sort(key=lambda m: (m.get("position") is None, m.get("position") or 0))
    return {**first, "source_entries": occurrences or None}


def apply_refinement(db, plan, aliases=None, entries=None):
    aliases = PROJECT_SPELLING_CORRECTIONS if aliases is None else aliases
    entries = PROJECT_LEARNER_ENTRIES if entries is None else entries
    if plan != plan_refinement(db, aliases, entries):
        raise ValueError("Vocabulary changed since preview")
    before = snapshot(db)
    id_changes = {r["old_id"]: r["target_id"] for r in plan["renames"]}
    expected = {}
    for row in before["word_groups"]:
        key = (id_changes.get(row["word_id"], row["word_id"]), row["group_id"])
        metadata = {k: row[k] for k in ["position", "list_code", "source_term", "source_entries"]}
        expected[key] = combine_metadata(expected[key], metadata) if key in expected else metadata
    for rename in plan["renames"]:
        old = db.get(Word, rename["old_id"])
        if rename["old_id"] == rename["target_id"]:
            old.term = rename["new"]
            db.flush()
            continue
        for membership in list(db.scalars(select(WordGroup).where(WordGroup.word_id == old.id))):
            target = db.get(WordGroup, (rename["target_id"], membership.group_id))
            if target is None:
                membership.word_id = rename["target_id"]
            else:
                metadata = expected[(target.word_id, target.group_id)]
                for key, value in metadata.items():
                    setattr(target, key, value)
                db.delete(membership)
        db.flush()
        db.delete(old)
        db.flush()
    replaced = set()
    for change in plan["replacements"]:
        word = db.get(Word, change["word_id"])
        if word is None or word.term != change["term"]:
            raise ValueError("Replacement target changed")
        db.execute(delete(WordMeaning).where(WordMeaning.word_id == word.id))
        store_meanings(db, word.id, [MeaningInput(**m) for m in change["after"]])
        word.phonetic = change["phonetic"]
        replaced.add(word.id)
    db.flush()
    actual = {(m.word_id, m.group_id): membership_metadata(m) for m in db.scalars(select(WordGroup))}
    if actual != expected:
        raise ValueError("Unexpected membership or source metadata change")
    removed = {r["old_id"] for r in plan["renames"] if r["target_id"] != r["old_id"]}
    changed_ids = set(id_changes) | replaced
    current_words = {w.id: w for w in db.scalars(select(Word))}
    if len(current_words) != len(before["words"]) - len(removed):
        raise ValueError("Unexpected word count change")
    for row in before["words"]:
        if row["id"] not in changed_ids:
            word = current_words[row["id"]]
            if (word.term, word.phonetic) != (row["term"], row["phonetic"]):
                raise ValueError("Unrelated word changed")
    current_meanings = {m.id: m for m in db.scalars(select(WordMeaning))}
    for row in before["word_meanings"]:
        if row["word_id"] not in changed_ids:
            saved = current_meanings.get(row["id"])
            if saved is None or (saved.part_of_speech, saved.meaning, saved.meaning_hash) != (row["part_of_speech"], row["meaning"], row["meaning_hash"]):
                raise ValueError("Unrelated meaning changed")
    if plan_refinement(db, aliases, entries) != {"renames": [], "replacements": []}:
        raise ValueError("Project refinement is not idempotent")
    return {"before_words": len(before["words"]), "after_words": len(current_words),
            "renamed_or_merged": len(plan["renames"]), "merged_duplicates": len(removed),
            "meaning_replacements": len(replaced), "source_metadata_verified": True,
            "unrelated_data_preserved": True, "idempotent": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with Session(engine) as db, db.begin():
        if args.apply:
            db.execute(text("LOCK TABLE words, word_meanings, word_groups, vocabulary_groups IN SHARE ROW EXCLUSIVE MODE"))
            list(db.scalars(select(VocabularyGroup).order_by(VocabularyGroup.id).with_for_update()))
            list(db.scalars(select(Word).order_by(Word.id).with_for_update()))
            list(db.scalars(select(WordGroup).order_by(WordGroup.group_id, WordGroup.word_id).with_for_update()))
        plan = plan_refinement(db)
        print(f"Renames/merges: {len(plan['renames'])}; meaning replacements: {len(plan['replacements'])}.")
        if not args.apply or not (plan["renames"] or plan["replacements"]):
            return
        reviewed_before = {w["id"]: w for w in json.loads((DATA / "project-vocabulary-audit-input.json").read_text())}
        for change in plan["replacements"]:
            original = reviewed_before.get(change["word_id"])
            expected = [{"part_of_speech": m["part_of_speech"], "meaning": m["meaning"]}
                        for m in original["meanings"]] if original else None
            if expected != change["before"] or original["phonetic"] != change["before_phonetic"]:
                raise ValueError(f"Word edited after review: {change['term']}; review it before applying")
        backup = DATA / f"before-project-optimization-{uuid4().hex[:10]}.json"
        with backup.open("x") as file:
            json.dump({"snapshot": snapshot(db), "plan": plan}, file, ensure_ascii=False, default=str)
        result = apply_refinement(db, plan)
        result["backup"] = str(backup)
        result["plan"] = plan
    result["committed"] = True
    (DATA / "project-optimization-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "plan"}, ensure_ascii=False))
    print("Project vocabulary optimization committed.")


if __name__ == "__main__":
    main()
