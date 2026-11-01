import pytest

from app.dictionary import lookup_word
from app.import_postgraduate import parse_source, resolve_words


@pytest.mark.parametrize("term,required,forbidden", [
    ("imagination", "想象力", "听觉"),
    ("imaginative", "富于想象力", "虚构的"),
    ("crucial", "至关重要", "严厉"),
    ("surgery", "外科手术", "换球"),
    ("dictate", "口述", "听写"),
    ("heroin", "海洛因", "海洛因, 吗啡"),
    ("normalisation", "正常化", "的变形"),
    ("approach", "方法", None),
    ("discipline", "学科", None),
    ("Venue", "举办地点", None),
    ("Stereo", "立体声", "铅版"),
    ("Bat", "蝙蝠", "成批"),
    ("Owl", "猫头鹰", "走私"),
    ("Sturdy", "结实", "羊"),
])
def test_postgraduate_lookup_does_not_restore_reviewed_errors(term, required, forbidden):
    entry = lookup_word(term)
    gloss = "；".join(m.meaning for m in entry.meanings)
    assert required in gloss
    if forbidden is not None:
        assert forbidden not in gloss
    assert all(m.part_of_speech for m in entry.meanings)


def test_postgraduate_source_resolves_all_chinese_and_pos_without_changing_order():
    source = parse_source()
    resolved = resolve_words(source)
    assert len(source) == len(resolved) == 3228
    assert [sources[0]["position"] for sources in source.values()] == list(range(1, 3229))
    assert list(resolved)[:5] == ["state", "paragraph", "author", "social", "according to"]
    assert list(resolved)[-1] == "crow"
    assert source["behavior"][0]["source_term"] == "behavio(u)r"
    assert source["resume"][0]["source_term"] == "résumé"
    assert all(m.part_of_speech for entry in resolved.values() for m in entry.meanings)
