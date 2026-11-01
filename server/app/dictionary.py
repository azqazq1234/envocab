"""Read-only English-Chinese dictionary, separate from user vocabulary data."""

import json
import re
import sqlite3
from pathlib import Path

from pydantic import BaseModel

from app.meaning_corrections import correct_meanings
from app.reviewed_vocabulary import LEARNER_ENTRIES, canonical_term

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "ecdict.sqlite3"
SOURCE_REVISION = "bc015ed2e24a7abef49fc6dbbb7fe32c1dadaf8b"
SOURCE_URL = f"https://raw.githubusercontent.com/skywind3000/ECDICT/{SOURCE_REVISION}"
POS_NAMES = {
    "n": "noun",
    "v": "verb",
    "vt": "verb",
    "vi": "verb",
    "a": "adjective",
    "adj": "adjective",
    "ad": "adverb",
    "adv": "adverb",
    "pron": "pronoun",
    "prep": "preposition",
    "conj": "conjunction",
    "int": "interjection",
    "interj": "interjection",
    "num": "numeral",
    "art": "article",
    "det": "determiner",
    "aux": "auxiliary verb",
    "abbr": "abbreviation",
    "phr": "phrase",
    "pl": "plural noun",
}
CASE_ENTRIES = json.loads(Path(__file__).with_name("dictionary_cases.json").read_text())
POS_PREFIX = re.compile(
    rf"^({'|'.join(re.escape(pos) for pos in POS_NAMES)})\.\s*",
    re.IGNORECASE,
)


class Meaning(BaseModel):
    part_of_speech: str | None
    meaning: str


class DictionaryEntry(BaseModel):
    term: str
    phonetic: str
    meanings: list[Meaning]
    source: str = "ECDICT"


def parse_meanings(translation: str) -> list[Meaning]:
    meanings = []
    seen = set()
    for line in translation.replace("\\n", "\n").splitlines():
        line = line.strip()
        if not line:
            continue
        match = POS_PREFIX.match(line)
        pos = POS_NAMES[match[1].lower()] if match else None
        text = line[match.end() :].strip() if match else line
        if text and (pos, text) not in seen:
            meanings.append(Meaning(part_of_speech=pos, meaning=text))
            seen.add((pos, text))
    return meanings


def lookup_word(term: str, path: Path = DATA_PATH) -> DictionaryEntry | None:
    term = canonical_term(term)
    if path == DATA_PATH and term in LEARNER_ENTRIES:
        return DictionaryEntry(term=term, source="Reviewed learner meanings", **LEARNER_ENTRIES[term])
    if term in CASE_ENTRIES:
        return DictionaryEntry(term=term, source="Reviewed case-specific meanings", **CASE_ENTRIES[term])
    if not path.is_file():
        raise FileNotFoundError(
            "Dictionary unavailable. Run make dictionary on the server."
        )
    with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) as connection:
        row = connection.execute(
            "SELECT term, phonetic, translation FROM dictionary WHERE term = ? COLLATE NOCASE",
            (term.strip(),),
        ).fetchone()
    if row is None:
        return None
    meanings = [Meaning(**item) for item in correct_meanings(
        term, [meaning.model_dump() for meaning in parse_meanings(row[2])]
    )]
    if not meanings:
        return None
    return DictionaryEntry(term=term, phonetic=row[1], meanings=meanings)
