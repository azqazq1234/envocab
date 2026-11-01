import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.dictionary import lookup_word, parse_meanings
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    path = tmp_path / "dictionary.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE dictionary (term TEXT PRIMARY KEY COLLATE NOCASE, phonetic TEXT, translation TEXT)"
        )
        connection.execute(
            "INSERT INTO dictionary VALUES (?, ?, ?)",
            ("book", "buk", "n. \u4e66\\nvt. \u9884\u8ba2"),
        )
        connection.executemany(
            "INSERT INTO dictionary VALUES (?, ?, ?)",
            [
                ("a.m.", "", "上午, 午前"),
                ("p.m.", "", "下午, 午后"),
                ("a", "", "art. 一个"),
                ("I", "ai", "pron. 我"),
            ],
        )
    monkeypatch.setattr("app.main.lookup_word", lambda term: lookup_word(term, path))
    with TestClient(app) as test_client:
        yield test_client


def test_lookup_multiple_meanings(client):
    response = client.get("/api/dictionary/lookup", params={"term": "BOOK"})
    assert response.status_code == 200
    entry = response.json()
    assert entry["term"] == "BOOK"
    assert entry["meanings"] == [
        {"part_of_speech": "noun", "meaning": "\u4e66"},
        {"part_of_speech": "verb", "meaning": "\u9884\u8ba2"},
    ]
    assert entry["source"] == "ECDICT"


@pytest.mark.parametrize("term", ["a.m.", "p.m.", "A.M."])
def test_lookup_abbreviation(client, term):
    response = client.get("/api/dictionary/lookup", params={"term": term})
    assert response.status_code == 200
    assert response.json()["term"] == term


def test_unknown_word(client):
    response = client.get("/api/dictionary/lookup", params={"term": "not-a-real-word"})
    assert response.status_code == 404
    assert "No dictionary entry" in response.json()["detail"]


@pytest.mark.parametrize("upper,lower,upper_text,lower_text", [
    ("China", "china", "中国", "瓷"),
    ("Miss", "miss", "小姐", "错过"),
    ("May", "may", "五月", "可能"),
    ("US", "us", "美国", "我们"),
])
def test_case_pairs_have_distinct_dictionary_meanings(client, upper, lower, upper_text, lower_text):
    upper_entry = client.get("/api/dictionary/lookup", params={"term": upper}).json()
    lower_entry = client.get("/api/dictionary/lookup", params={"term": lower}).json()
    assert upper_entry["term"] == upper
    assert lower_entry["term"] == lower
    upper_meanings = " ".join(m["meaning"] for m in upper_entry["meanings"])
    lower_meanings = " ".join(m["meaning"] for m in lower_entry["meanings"])
    assert upper_text in upper_meanings and lower_text not in upper_meanings
    assert lower_text in lower_meanings and upper_text not in lower_meanings


def test_ms_title_has_its_own_meaning(client):
    entry = client.get("/api/dictionary/lookup", params={"term": "Ms"}).json()
    assert entry["term"] == "Ms"
    assert entry["meanings"] == [
        {"part_of_speech": "abbreviation", "meaning": "女士（用于女性姓氏前，不说明婚姻状况）"}
    ]


@pytest.mark.parametrize("term", ["a", "A", "i", "I"])
def test_lookup_single_letter(client, term):
    response = client.get("/api/dictionary/lookup", params={"term": term})
    assert response.status_code == 200
    assert response.json()["term"].lower() == term.lower()
    assert response.json()["meanings"]


@pytest.mark.parametrize("term", ["b", "a-", "a'", "a."])
def test_valid_short_unknown_word(client, term):
    assert client.get("/api/dictionary/lookup", params={"term": term}).status_code == 404


@pytest.mark.parametrize("term", ["", ".", "123", "word?", "x" * 101])
def test_invalid_query(client, term):
    assert (
        client.get("/api/dictionary/lookup", params={"term": term}).status_code == 422
    )


def test_missing_dictionary(client, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.main.lookup_word",
        lambda term: lookup_word(term, tmp_path / "missing.sqlite3"),
    )
    response = client.get("/api/dictionary/lookup", params={"term": "book"})
    assert response.status_code == 503
    assert "make dictionary" in response.json()["detail"]


def test_unknown_pos_and_duplicate_lines():
    meanings = parse_meanings("n. first\\nn. first\n[domain] second\n\n")
    assert len(meanings) == 2
    assert meanings[0].part_of_speech == "noun"
    assert meanings[1].part_of_speech is None
    assert meanings[1].meaning == "[domain] second"


@pytest.mark.parametrize(
    ("prefix", "expected"),
    [
        ("v", "verb"),
        ("vt", "verb"),
        ("vi", "verb"),
        ("a", "adjective"),
        ("adj", "adjective"),
        ("ad", "adverb"),
        ("adv", "adverb"),
        ("int", "interjection"),
        ("interj", "interjection"),
    ],
)
def test_pos_aliases_with_overlapping_prefixes(prefix, expected):
    meanings = parse_meanings(f"{prefix.upper()}. example")
    assert len(meanings) == 1
    assert meanings[0].part_of_speech == expected
    assert meanings[0].meaning == "example"
