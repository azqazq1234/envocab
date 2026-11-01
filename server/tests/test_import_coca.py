from app.import_coca import github_meanings, parse_source
from app.vocabulary import WordInput


def test_coca_merge_preserves_excel_first_occurrences_then_github_only():
    source = parse_source(include_excluded=True)
    terms = list(source)
    assert len(terms) == len({t.casefold() for t in terms}) == 17673
    assert sum(len(rows) for rows in source.values()) == 25250
    assert [rows[0]["position"] for rows in source.values()] == list(range(1, 17674))
    assert all(rows[0]["list_code"] == "excel-lemmas" for rows in list(source.values())[:4380])
    assert all(rows[0]["list_code"] == "github" for rows in list(source.values())[4380:])
    assert terms[:8] == ["the", "be", "and", "a", "of", "to", "in", "I"]
    assert [r["source_rank"] for r in source["to"] if r["list_code"] == "excel-lemmas"] == [6, 12]
    assert {r["source_term"] for r in source["n't"]} == {"n't", "n''t"}
    assert {r["source_term"] for r in source["y'all"]} == {"y''all"}
    assert source["true"][0]["source_rank"] == 414
    assert source["false"][0]["source_rank"] == 2107


def test_coca_reimport_preserves_user_spelling_choices_and_remaining_order():
    original = parse_source(include_excluded=True)
    current = parse_source()
    excluded = {"behavior", "labor", "analyze", "ax", "mustache", "catalog", "fulfil", "instil", "judgment"}
    kept = {"behaviour", "labour", "analyse", "axe", "moustache", "catalogue", "fulfill", "instill", "judgement"}
    assert len(current) == 17664
    assert kept <= current.keys()
    assert not excluded & current.keys()
    assert current == {term: sources for term, sources in original.items() if term not in excluded}


def test_source_gloss_parser_preserves_explicit_parts_of_speech():
    meanings = github_meanings('n.["光泽","光泽"] vt.["擦亮","润色"]')
    assert [(m.part_of_speech, m.meaning) for m in meanings] == [("noun", "光泽"), ("verb", "擦亮；润色")]
    assert github_meanings("undefined") == []


def test_slash_headwords_are_valid_without_changing_their_spelling():
    for term in ["and/or", "his/her", "he/she"]:
        assert WordInput(term=term, meanings=[{"meaning": "测试"}]).term == term
