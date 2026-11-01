# COCA merged vocabulary

Current COCA total: **17664 words**. On 2026-10-30 the user selected `behaviour`, `labour`, `analyse`, `axe`, `moustache`, `catalogue`, `fulfill`, `instill` and `judgement`. Their nine alternate spellings were removed from COCA; other groups and retained source positions were preserved. `spelling-preferences.json` records the exclusions, and default imports filter them out so they cannot be restored accidentally. `merged.txt` reflects the active list. The independent source-deduplicated files and raw source JSON remain unchanged.

The application COCA group combines two supplied sources. It is a merged learning list, not a claim that both sources share one edition or one official frequency ranking.

1. `wordFrequency.xlsx`, sheet `1 lemmas`: 5050 ranked lemma/POS records from the supplied free COCA sample. The workbook identifies https://www.wordfrequency.info/ and the one-billion-word COCA corpus as its source. The extracted records retain the original rank, POS, frequency and capitalization measures. `true` and `false` Excel booleans were restored to word strings. The other workbook sheets are supporting frequency views and are not appended as extra vocabulary.
2. https://github.com/llt22/coca-vocabulary-20000, pinned at `cee58af112e7469261bd52ce5a44d75986ac757b`: all 20200 numbered Markdown records, including their original annotations. The repository license is retained in `GITHUB-LICENSE.txt`.

Both lists are deduplicated by spelling ignoring case. Different parts of speech share one word; inflections and different British/American spellings stay separate. Keep the first occurrence in Excel order, then append GitHub-only entries in their first-occurrence order. Original Excel data and the GitHub checkout were not edited.

The initial import contained **17673 words**: **4380** from Excel followed by **13293** additional GitHub words. The independently deduplicated GitHub list has **17634** entries. `excel-deduplicated.txt`, `github-deduplicated.txt` and `merged.txt` preserve their respective orders.

`headwords.json` pins display spellings, reusing existing case-sensitive application identities when suitable. Three double-apostrophe transcription forms (`n''t`, `o''clock`, `y''all`) are normalized to single apostrophes; the corrupted source headword `saut��` is mapped to `saute`. Raw source terms are preserved. These normalization collisions are counted before producing the merged list.

At initial import, every one of the 25250 source occurrences was retained in membership `source_entries`, with a source list, original rank, raw term, and Excel POS/frequency or GitHub filename. The membership position is the merged order, not the original source rank.

Existing shared Chinese meanings are preserved. New words resolve against the reviewed local dictionary; `server/app/coca_supplement.json` provides explicit Chinese meanings for 110 compounds, source-only forms and exceptions. This import does not constitute a full semantic audit of all newly imported dictionary senses.

Supplement references for specific uncertain entries:
- `underly` is marked as a nonstandard spelling of `underlie`: https://en.wiktionary.org/wiki/underly and https://www.oxfordlearnersdictionaries.com/us/definition/english/underlie
- `Likert-type`: https://www2.gov.bc.ca/gov/content/data/statistics/surveys/understanding-the-engagement-model/survey-response-scale

Run from `server`: `uv run python -m app.import_coca` previews resolution. Add `--apply` to save a full vocabulary backup and import in one transaction. Repeat imports reuse words, meanings and memberships. Final checks are in `server/data/coca-import-verification.json`.
