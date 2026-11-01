"""Reviewed, exact-sense corrections; unknown senses are never auto-classified."""

import json
from pathlib import Path

RULES = json.loads(Path(__file__).with_name("junior_meaning_corrections.json").read_text())
EXCLUDED_TERMS = {"march", "turkey"}
assert not EXCLUDED_TERMS.intersection(RULES)


def correct_meanings(term: str, meanings: list[dict]) -> list[dict]:
    rules = {rule["original"]: rule["replacement"] for rule in RULES.get(term, [])}
    result = []
    seen = set()
    for meaning in meanings:
        replacements = (
            rules.get(meaning["meaning"], [meaning])
            if not meaning.get("part_of_speech")
            else [meaning]
        )
        for item in replacements:
            key = (item.get("part_of_speech") or "", item["meaning"])
            if key not in seen:
                result.append(item)
                seen.add(key)
    return result
