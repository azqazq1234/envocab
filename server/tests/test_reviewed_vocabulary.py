import pytest

from app.dictionary import lookup_word
from app.reviewed_vocabulary import canonical_term
from app.vocabulary import WordInput


@pytest.mark.parametrize("original,expected", [
    (" grammer ", "grammar"), ("destory", "destroy"),
    ("Grammer", "Grammer"), ("China", "China"), ("china", "china"),
    ("Run", "run"), ("RUN", "RUN"),
])
def test_spelling_corrections_are_explicit_and_case_sensitive(original, expected):
    assert canonical_term(original) == expected
    assert WordInput(term=original, meanings=[{"meaning": "测试"}]).term == expected


def test_reviewed_lookup_uses_correct_headword_and_learner_meanings():
    entry = lookup_word("grammer")
    assert entry.term == "grammar"
    assert any("语法" in meaning.meaning for meaning in entry.meanings)
    assert lookup_word("unfriendly").meanings[0].part_of_speech == "adjective"
    assert any("公寓" in meaning.meaning for meaning in lookup_word("flat").meanings)


@pytest.mark.parametrize("term,present,absent", [
    ("polish", "润色", "波兰"),
    ("pole", "极点", "波兰"),
    ("August", "八月", "威严"),
    ("Pacific", "太平洋", "和平"),
    ("Catholic", "天主教", "宽宏"),
    ("AD", "公元", "广告"),
    ("CE", "公元", "铈"),
    ("VCD", "视频光盘", "二极"),
    ("NASA", "美国国家航空航天局", "国际航空"),
    ("ethical", "道德", "民族"),
    ("techno", "电子舞曲", "[计]"),
    ("make-up", "化妆品", "捏造"),
    ("peppercorn", "胡椒粒", "答礼"),
    ("paramedic", "急救", "伞降"),
    ("leopard", "豹", "美洲豹"),
    ("pence", "便士", "(美)"),
    ("drunk", "过去分词", "drink的过去式"),
    ("chacma baboon", "豚尾狒狒", "家族"),
])
def test_senior_lookup_prevents_case_contamination_and_old_mistranslations(term, present, absent):
    entry = lookup_word(term)
    text = ' '.join(m.meaning for m in entry.meanings)
    assert present in text and absent not in text
    assert all(m.part_of_speech for m in entry.meanings)
    assert entry.source == "Reviewed learner meanings"


def test_senior_source_resolves_without_reintroducing_unclassified_meanings():
    from app.import_senior import parse_source, resolve_words

    source = parse_source()
    resolved = resolve_words(source)
    assert len(source) == len(resolved) == 5209
    assert resolved[538].term == "run"
    assert source[538].source_term == "Run (ran,run,running)"
    assert all(m.part_of_speech for entry in resolved for m in entry.meanings)
    assert lookup_word("agenda").meanings[0].part_of_speech == "noun"
    assert lookup_word("regardless").meanings[0].part_of_speech == "adverb"


def test_reimported_titles_and_existing_mall_meanings_are_consistent():
    assert lookup_word('Ms').meanings[0].part_of_speech == 'abbreviation'
    assert any('购物中心' in m.meaning for m in lookup_word('mall').meanings)
