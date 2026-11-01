from app.meaning_corrections import correct_meanings


def test_reviewed_senses_are_corrected_and_deduplicated_idempotently():
    original = [
        {"part_of_speech": None, "meaning": "冰淇淋"},
        {"part_of_speech": None, "meaning": "[化] 冰淇淋"},
    ]
    corrected = correct_meanings("ice cream", original)
    assert corrected == [{"part_of_speech": "noun", "meaning": "冰淇淋"}]
    assert correct_meanings("ice cream", corrected) == corrected


def test_unrelated_acronym_is_removed_without_losing_the_word_meaning():
    original = [
        {"part_of_speech": "noun", "meaning": "猫"},
        {"part_of_speech": None, "meaning": "[计] 计算机辅助教学, 计算机辅助翻译, 计算机辅助排字, 计算机辅助测试"},
    ]
    assert correct_meanings("cat", original) == original[:1]


def test_unknown_or_already_classified_senses_are_not_guessed_or_rewritten():
    original = [
        {"part_of_speech": None, "meaning": "未核对的专业释义"},
        {"part_of_speech": "noun", "meaning": "[计] 单击"},
    ]
    assert correct_meanings("click", original) == original


def test_march_and_turkey_are_unchanged():
    for term, meaning in [("march", "三月, 行军"), ("turkey", "火鸡, 土耳其")]:
        original = [{"part_of_speech": None, "meaning": meaning}]
        assert correct_meanings(term, original) == original
