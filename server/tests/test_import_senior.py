from dataclasses import replace

import pytest

from app.import_senior import parse_source, resolve_words


def test_source_keeps_list_membership_and_normalizes_annotations():
    words = parse_source()
    assert len(words) == 5209
    assert words[0].list_code == "core01"
    assert words[2223].list_code == "core43"
    assert words[2224].list_code == "extend01"
    assert words[3997].list_code == "extend14"
    assert words[3998].list_code == "basic01"
    assert words[-1].list_code == "basic10"
    assert [w.position for w in words] == list(range(1, 5210))
    assert len({w.term for w in words}) == 5209
    by_source = {w.source_term: w.term for w in words}
    assert by_source["Run (ran,run,running)"] == "run"
    assert by_source["seem linking"] == "seem"
    assert by_source["can modal"] == "can"
    assert by_source["license(=licence)"] == "license"
    assert by_source["o’clock"] == "o'clock"
    assert by_source["café"] == "cafe"


def test_missing_dictionary_entry_stops_import():
    word = replace(parse_source()[0], term="missing-test-headword")
    with pytest.raises(ValueError, match="Missing dictionary entries"):
        resolve_words([word])


def test_supplement_resolves_missing_words_without_changing_headwords():
    source = parse_source()
    terms = {"cyberbully", "the media", "textspeak", "positronic", "biomimicry",
             "megadrought", "barreleye", "declutter"}
    words = [w for w in source if w.term in terms]
    resolved = resolve_words(words)
    assert {w.term for w in resolved} == terms
    assert all(w.meanings for w in resolved)
