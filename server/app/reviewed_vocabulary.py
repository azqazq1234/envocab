"""Explicitly reviewed learner entries and case-sensitive spelling corrections."""

import json
from pathlib import Path

PROJECT_SPELLING_CORRECTIONS = json.loads(Path(__file__).with_name("project_spelling_corrections.json").read_text())
SPELLING_CORRECTIONS = {"grammer": "grammar", "destory": "destroy", "Run": "run", **PROJECT_SPELLING_CORRECTIONS}
JUNIOR_LEARNER_ENTRIES = json.loads(Path(__file__).with_name("junior_learner_entries.json").read_text())
SENIOR_LEARNER_ENTRIES = json.loads(Path(__file__).with_name("senior_learner_entries.json").read_text())
PROJECT_LEARNER_ENTRIES = json.loads(Path(__file__).with_name("project_learner_entries.json").read_text())
POSTGRADUATE_LEARNER_ENTRIES = json.loads(Path(__file__).with_name("postgraduate_learner_entries.json").read_text())
# Keep previous cleanup commands and future imports on the latest reviewed senses.
PROJECT_LEARNER_ENTRIES.update(POSTGRADUATE_LEARNER_ENTRIES)
COCA_LEARNER_ENTRIES = json.loads(Path(__file__).with_name("coca_supplement.json").read_text())
PROJECT_LEARNER_ENTRIES.update(COCA_LEARNER_ENTRIES)
# Effective historical views prevent old cleanup commands from restoring an
# earlier sense after the project-wide review. Only existing view keys change.
JUNIOR_LEARNER_ENTRIES.update({key: value for key, value in PROJECT_LEARNER_ENTRIES.items() if key in JUNIOR_LEARNER_ENTRIES})
SENIOR_LEARNER_ENTRIES.update({key: value for key, value in PROJECT_LEARNER_ENTRIES.items() if key in SENIOR_LEARNER_ENTRIES})
LEARNER_ENTRIES = {**JUNIOR_LEARNER_ENTRIES, **SENIOR_LEARNER_ENTRIES, **PROJECT_LEARNER_ENTRIES}


def canonical_term(term: str) -> str:
    stripped = term.strip()
    return SPELLING_CORRECTIONS.get(stripped, stripped)
