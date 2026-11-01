# Envocab

An English vocabulary project with a frontend layout and a FastAPI backend and a shared PostgreSQL vocabulary database.

- `ui/`: Next.js, React, TypeScript, Tailwind CSS, and shadcn/ui. Includes Dashboard and All, Junior, Senior, CET-4, CET-6, Postgraduate, and IELTS vocabulary groups. Every vocabulary group uses the same `/[group]` page; `/` redirects to `/all`.
- The fixed header displays the book icon and VOCAB title. The sidebar extends to the bottom of the viewport and can collapse to icons, with the toggle at the bottom. Main content adjusts to the sidebar width; there is no page footer.
- `server/`: Python 3.15 virtual environment (`.venv`), FastAPI, SQLAlchemy, and Psycopg. Provides dictionary lookup, vocabulary saving, and group-filtered listing APIs; Swagger, ReDoc, and OpenAPI endpoints remain disabled.
- PostgreSQL: the `envocab` database stores words, shared meanings, groups, and word-group associations.
- Alembic: migration configuration and an initial schema migration are included.
- Lockfiles: `ui/package-lock.json` and `server/uv.lock`.

## Run

From the project root:

```sh
make dev
```

Alternatively, run `make ui` and `make server` in separate terminals to view their logs independently.

The frontend listens on `0.0.0.0:3000`, accessible on the local network at `http://<chobitmac-lan-ip>:3000`. The backend listens on `127.0.0.1:8000`. Every vocabulary page shares Check and List tabs. Check displays random words; List supports English sorting, English/Chinese search, row selection, and adaptive pagination.

The development server allows client assets from hosts matching `192.168.*.*` and `100.*.*.*`, plus `chobitmac` and `chobitmac.local`. These patterns cover the current LAN and Tailscale IPv4 addresses without listing each IP individually. Through Tailscale, open `http://100.112.91.68:3000/all`; the browser sends API requests to the same host on port 3000, and Next.js proxies them to `127.0.0.1:8000` on the server. Only port 3000 needs to be reachable from the browser. If using a hostname or address outside these patterns, update `allowedDevOrigins` in `ui/next.config.ts`, then restart the frontend development server.

## Install and check

Requires Node.js 24+, npm, uv, Python 3.15, and PostgreSQL 18.

```sh
# Only run this if the database does not exist.
createdb envocab
# Install locked dependencies and copy missing environment files; database migrations are applied.
make setup
make check
```

The database connection is configured in `server/.env`, defaulting to `DATABASE_URL=postgresql+psycopg:///envocab`.
The frontend proxies `/api/*` requests to the backend, configured through `API_URL` in `ui/.env.local`.

After adding database models, generate and apply migrations:

```sh
cd server
# Import new models in migrations/env.py to register their metadata.
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

`make check` runs Python linting and API tests (including random word selection), frontend lookup scheduling, HTTP helper, shared request cancellation, pagination tests, and frontend linting, type checking, and production builds.

## Dependencies

Dependencies were refreshed against stable npm/PyPI releases on 2026-11-02. Lockfiles preserve reproducible versions. The TypeScript 7 compiler is installed through the `@typescript/native` alias; the `typescript` alias provides the official `@typescript/typescript6` API compatibility package for Next.js and ESLint.

```sh
cd ui
npm outdated
# After updates, run npm run lint, npm run typecheck, and npm run build.
cd ../server
uv lock --upgrade
uv sync --locked
```

Keep the TypeScript aliases until Next.js and ESLint fully support the TypeScript 7 API. Transitive dependencies follow upstream compatibility ranges and the lockfiles.

## Known upstream issues

On 2026-11-02, after the dependency refresh, `npm audit` reported 20 findings (2 low and 18 moderate; no high or critical findings). These come from `deepmerge` and `minimatch` in the ESLint and shadcn development-tool dependency trees. The compatible updates removed the previous `body-parser` high-severity finding. No compatible fixes are currently available for the remaining findings; `npm audit fix --force` proposes major tool downgrades and was not applied. Recheck after upstream updates.

ESLint 10 also triggers peer dependency warnings from some indirect Next.js plugins; linting has been verified to work. TypeScript aliases follow the [official compatibility guidance](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/#running-side-by-side-with-typescript-6.0). Frontend setup follows the [Next.js documentation](https://nextjs.org/docs/app/getting-started/installation) and [shadcn/ui documentation](https://ui.shadcn.com/docs/installation/next).

## Dictionary lookup

Every vocabulary group except All has an add icon that opens a dialog. Enter at least two English letters to query automatically. The centered green input uses bold 40px text and shows a thin arrow while empty. There is no visible title, input label, or lookup button. The close button has a transparent background and a pointer cursor. Results display Chinese meanings and their parts of speech; interface labels remain in English. Click the circular ADD button to save the word and its meanings to the current group; the list refreshes while the dialog stays open, clears the word and lookup results, and refocuses the input for the next word.

`GET /api/dictionary/lookup?term=book` returns `term`, `phonetic`, `meanings` (each with `part_of_speech` and `meaning`), and `source`. Both client and server require at least two English letters and allow periods in abbreviations such as `a.m.` and `p.m.`. Unknown words return 404, invalid input returns 422, and a missing dictionary index returns 503. A missing part-of-speech label is returned as null and shown as Unspecified rather than inferred.

The API uses [ECDICT](https://github.com/skywind3000/ECDICT), pinned to revision `bc015ed2e24a7abef49fc6dbbb7fe32c1dadaf8b`. Its MIT license is included in `server/licenses/ECDICT.txt`. The imported dictionary currently contains 768,739 entries. Entries may include older wording or specialist senses and should be reviewed before saving.

Reviewed Junior sense corrections live in `server/app/junior_meaning_corrections.json`. Rules match the exact spelling and original unclassified sense, provide explicit parts of speech and revised Chinese, and remove misattributed acronym senses. They apply to future dictionary lookups as well as the database cleanup (`cd server && uv run python -m app.correct_junior_meanings`, with `--apply` to commit after backing up affected definitions). Unknown senses are left unclassified. The completed cleanup covered 639 words and 652 unclassified sense records; Junior now has no missing parts of speech. `march` and `turkey` were explicitly excluded. Word IDs, group memberships, and order are unchanged; corrections to shared words also appear in Senior.

A subsequent full review refined 351 entries using `server/app/junior_learner_entries.json`: common senses were added, incorrect senses and POS labels corrected, and reviewed redundant/specialist senses trimmed. That review left Junior with 1994 words and 4300 meanings (4297 after the subsequent shared `run` correction). `grammer` → `grammar` and `destory` → `destroy` reuse the existing correctly spelled words while keeping Junior positions 72 and 112. Other Junior IDs and all positions remain unchanged. Exact lowercase spelling aliases are recognized by saving, duplicate checks, dictionary lookup, and search without lowercasing other inputs. `cd server && uv run python -m app.refine_junior` previews this cleanup; `--apply` saves a full database backup before committing. `march` and `turkey` remain protected, and a second preview reports zero changes. Shared meanings also update Senior; its membership order is unchanged.

Senior review corrections live in `server/app/senior_learner_entries.json`, loaded after Junior overrides. The completed cleanup updated 1408 stored words and supplies 1409 dictionary overrides, including 149 word-specific reviews. It resolves missing POS records, incorrect capitalization-dependent senses and translations, promotes useful common meanings, and prunes unclassified specialist/duplicate senses from the high-school learner definitions. Original definitions are retained in the full database backup and review snapshots. Senior remains 5209 words (2224 core, 1774 extend, 1211 basic), with 9044 meanings, no missing POS and no same-POS subset duplicate candidates. `Run` reuses existing `run` ID 2338 at Senior position 539; the original source annotation is preserved. The shared `run` definition also updates Junior, whose 1994 memberships and positions are unchanged. Four explicit case pairs stay distinct, and `march`/`turkey` remain protected. `Ms` dictionary lookup uses the existing abbreviation POS. `cd server && uv run python -m app.refine_senior` previews changes; `--apply` saves a complete vocabulary backup and commits atomically, rejecting stale previews and checking all group source metadata. A second preview reports zero changes. All 5209 resolved source meaning sets match the stored definitions. Completion details: `server/data/senior-refinement-completed.md`.

```sh
# Download the pinned snapshot and build/rebuild its local lookup index.
make dictionary
```

`make setup` imports the dictionary if its index is missing. The read-only reference index at `server/data/ecdict.sqlite3` is excluded from Git. It is separate from the PostgreSQL application database; reference dictionary imports do not add user words. The first import requires network access to GitHub; lookups run locally without API keys or network requests.

Lookup results preserve the entered spelling. The local ECDICT index provides a case-insensitive fallback for general vocabulary, while `server/app/dictionary_cases.json` supplies distinct reviewed meanings for the four case pairs above and reviewed capitalized titles, abbreviations, and proper nouns. Frontend dictionary caching and duplicate checks use exact case.

Automatic lookup waits for 500ms of idle typing and starts requests at least 800ms apart per dialog instance. Successful results are cached for the mounted dialog (up to 50 words). Changing input, closing the dialog, or navigating away cancels pending and active requests. Superseded responses cannot replace current results. Requests time out after 15 seconds.

`GET /api/words/exists?group=junior&term=book` checks case-sensitive word membership after trimming whitespace without writing data. The add dialog runs this check alongside dictionary lookup, including when dictionary results are cached. Words already in the current group retain their normal green text and dictionary meanings; the ADD button turns yellow and is disabled, and Enter does not save. Words in other groups remain available. A failed availability check also prevents saving until a successful recheck.

The dictionary endpoint reads a local index, has no third-party request quota, and currently has no server-side rate limiter. Client-side scheduling reduces requests but is not a server-enforced limit. Run `cd ui && npm test` for debounce, throttling, cancellation, minimum length, cache, stale response, and timeout regression tests.

## Shared vocabulary storage

The project-wide review on 2026-10-27 updated 1295 words, corrected mistranslations and missing common senses, classified all formerly unclassified meanings, and removed redundant same-POS senses. It normalized 22 explicitly reviewed spellings (including `waX` → `wax`) and merged 14 duplicate identities. The database now has 8242 distinct words and 14400 meanings; Junior 1994, Senior 5209, CET-4 2775, CET-6 2736, and IELTS 3540 memberships are unchanged. All source spellings, occurrence metadata, and group positions are preserved. Unlike earlier narrowly scoped reviews, this authorized full review also separates lowercase `march`/`turkey` from the meanings of `March`/`Turkey`; the capitalized forms are available for lookup without adding source-external group memberships.

Current shared corrections live in `server/app/project_learner_entries.json`, loaded after older Junior/Senior overrides. Exact spelling aliases live in `server/app/project_spelling_corrections.json`; meaningful case distinctions such as China/china, May/may, Miss/miss, US/us, and Catholic/catholic remain separate. Unknown future senses are not automatically classified. The inspected exact-sense decisions are recorded in `server/data/project-sense-review.json`. `cd server && uv run python -m app.refine_project` now previews zero changes; `--apply` is the backed-up, atomic replay command. Completion, all-word dictionary parity, API checks, and source invariants are recorded in `server/data/project-optimization-completed.md` and `server/data/project-optimization-verification.json`.

IELTS is imported from `rawlist/ielts.txt` with `cd server && uv run python -m app.import_ielts --apply` (omit `--apply` to preview). This source contains 3540 distinct words in list01–list50. The importer validates each declared list count, excludes heading lines, and preserves list codes, original spelling, and word order in membership metadata. Existing shared Chinese meanings are reused; new words use the local dictionary. A database snapshot is saved before committing. All 3540 words have Chinese meanings; verification of API pagination, source order, repeat imports, and existing data preservation is recorded in `server/data/ielts-import-verification.json`.

CET-6 is imported from `rawlist/cet6.txt` with `cd server && uv run python -m app.import_cet6 --apply` (omit `--apply` to preview). Its 2740 source lines produce 2736 distinct memberships after merging repeated expert, carbohydrate, substance, and grin entries. All source occurrences, spelling, and order are preserved. Existing shared Chinese meanings are reused; new words use the local dictionary and the existing welcome home supplement. The importer backs up the database before committing and supports repeat imports without duplicates. All API pages and Chinese meaning coverage were checked; results are recorded in `server/data/cet6-import-verification.json`.

CET-4 is imported from `rawlist/cet4.txt` with `cd server && uv run python -m app.import_cet4 --split-coverage-lettering --apply` (omit `--apply` to preview dictionary resolution). Its 2775 source lines produce 2775 distinct memberships: the repeated `radical` is merged, and the ambiguous source line `coverage lettering` is explicitly split into two words. Source spelling, order, and all occurrence positions are retained in membership metadata. Existing shared Chinese meanings are reused; new words use the local dictionary, with `welcome home` supplemented as 欢迎回家. The importer backs up the database before committing and can be rerun without duplicating words or meanings. Verification is recorded in `server/data/cet4-import-verification.json`.

The application has four business tables: `words`, `word_meanings`, `vocabulary_groups`, and `word_groups`. Six destination groups are seeded by the schema migration; All is a combined view rather than a stored group.

Senior source lists are stored on `word_groups` using `list_code` (`core01`–`core43`, `extend01`–`extend14`, and `basic01`–`basic10`), `position` (one-based file order), and `source_term` (the original spelling and annotations). These fields remain internal and are not table columns in the UI. Group listings use source order by default, with manually added words following the imported words; English/Chinese sorting remains available. All retains its shared word creation order. Junior also stores an explicit membership position for every word; `Ms` (女士) follows `website`, and `Miss` (小姐) follows `giraffe`; the obsolete lowercase `ms` membership was removed. Junior currently contains 1994 words. I, AI, English, Jew, Christmas, Olympic, Mars, PE, Mrs, Mr, and Chinese use their corrected capitalization and reviewed meanings.

Senior's table includes a Types column before Actions. The API derives `senior_types` (`core`, `extend`, and/or `basic`) from the Senior membership's source lists; `senior_type` retains the first type for compatibility; the UI uses deep green rounded tags. Manually added words without a source list display a dash. Detailed list numbers remain internal.

The Types header offers the same checkbox dropdown as Groups, with core, extend, basic, and All types. Multiple selections include any selected type; All types removes the filter, including words without a source type. The API accepts `senior_types=core,extend,basic`, applying the filter before pagination and search location. Search suggestions share the selected types, and changing types returns to page 1 while preserving sort and page size.

`senior.txt` contains 5209 case-sensitive entries in 67 lists: 2224 core, 1774 extend, and 1211 basic entries. Senior stores 5209 distinct words. `China/china`, `Miss/miss`, `May/may`, and `US/us` are separate words with separate Chinese meanings, memberships, and source positions. All source occurrences (list code, original term, and position) are preserved in `word_groups.source_entries`; scalar source fields and default ordering refer to the first occurrence. Preview dictionary resolution with `cd server && uv run python -m app.import_senior`; add `--apply` to commit all resolved entries in one transaction. Reruns reuse words, meanings, and memberships. Inflection/spelling parentheses and trailing `linking`/`modal` labels are removed for dictionary lookup while the original source text is preserved. All source entries have been imported with Chinese meanings and their original positions. Typographic apostrophes and accents are normalized for application headwords (`o’clock` → `o'clock`, `café` → `cafe`) while preserving original source text; `sideroad` uses its reviewed learner entry, falling back to `side road` only when no direct entry is available. The source headword `Run` is canonicalized to `run` without changing its original annotation or position. Eight entries missing from ECDICT use reviewed Chinese glosses in `server/app/senior_supplement.json`, which also records each reference URL. The source spelling `memor` was corrected to `memory` (core01, position 28). For case reconciliation, `uv run python -m app.import_senior --apply --sync-source` updates imported Senior memberships to match the source, removes obsolete imported spellings while preserving other groups and manual memberships, and replaces the eight previously mixed case-pair meanings. A database snapshot was saved under `server/data/before-case-sensitive-*.json` before the first reconciliation.

`POST /api/groups/{slug}/words` accepts `term`, `phonetic`, and a nonempty `meanings` array. Words are trimmed while preserving case; uppercase and lowercase spellings are distinct identities. PostgreSQL upserts and case-sensitive unique constraints reuse exact spellings, deduplicate matching part-of-speech/meaning pairs, and prevent duplicate membership. Adding a word already in the destination group returns 409 and rolls back without changing its phonetic, meanings, or memberships. Adding it to another group is allowed and reuses the shared word; any new meanings are appended and shared by every associated group. The entire save runs in one transaction. A SHA-256 fingerprint is used for the meaning uniqueness index so long definitions do not exceed PostgreSQL's index-entry size limit.

`GET /api/words?group=junior&page=1&page_size=20` returns `items`, `total`, `page`, `page_size`, and `total_pages`. Use `group=all` for the deduplicated combined list. Words are listed in ascending order of their first creation. After ADD, the UI refreshes and displays the last page without resetting the chosen page size, so new words appear at the end and overflow automatically advances to the next page. The table shows selection checkboxes, Score, English, Chinese, and Actions columns, plus Groups tags in All; multiple meanings appear inline with abbreviated parts of speech such as n., v., and adj. Phonetics are not displayed in the English column. Integration tests use PostgreSQL savepoints and roll back their test words.

All's Groups column provides a dropdown to filter by Junior, Senior, CET-4, CET-6, Postgraduate, IELTS, or COCA; select Groups to show every group again. Tags use J, S, 4, 6, P, I, and C. The menu supports multiple groups and stays open while selecting. Matching any selected group includes the word, with shared words shown once; All groups clears the selection. Filtering applies before counting and pagination, resets the list to page 1 while retaining sort and page size, and scopes search suggestions. The API accepts comma-separated memberships such as `member_of=junior,senior` alongside `group=all` while retaining All's shared word creation order; when groups are selected, each row displays only the selected group tags it belongs to; clearing the filter restores all its group tags.

## Editing, deletion, and selection

Each row has Edit and Delete icon buttons. Edit supports the English word and multiple meaning/part-of-speech pairs, and updates the shared word across every associated group. Renaming to an existing word returns 409 without merging or overwriting another word. `PATCH /api/words/{id}` validates and replaces the complete meaning list in one transaction.

Delete opens a confirmation dialog. `DELETE /api/words/{id}?group=junior` removes only that membership, preserving other groups. Removing the last membership also removes the word and its meanings. `group=all` removes the word and every association. The group parameter is required to prevent an omitted filter from becoming a global deletion.

Checkboxes support selecting individual or multiple rows. The header checkbox selects or clears the current page and shows a mixed state for partial selection. Selected IDs persist across pagination within the current list; a count appears in the footer. Selection does not trigger editing or deletion automatically.

## Pagination

`GET /api/words` defaults to `page=1&page_size=20`. `page` must be a positive integer; `page_size` accepts integers from 1 to 100. Filtering by group happens before counting and pagination. The response includes the effective page, page size, total word count, and total pages. An empty result has page 1 of 1; a page beyond the end is clamped to the last available page.

The table footer shows the group word count on the left, numbered page buttons in the center, and a page-size selector on the right. First, Previous, Next, and Last icon buttons navigate between pages; long page ranges use ellipses. The available page sizes are 10, 20, 50, and 100 rows. Before its first list request, the UI measures an invisible row with the real cell padding and action-control height, then chooses a page size from the viewport capacity. Inactive vocabulary tab panels leave the layout immediately so their temporary height cannot trigger an undersized request. There is no preliminary 10-row fetch. Automatic sizing continues to use these thresholds: more than 11 rows of capacity selects 20, more than 21 selects 50, and more than 51 selects 100. A manual selection overrides automatic sizing and returns to page 1. Selection persists across page changes within the current list.


## Learning and Dashboard

Check initially hides pronunciation and meanings. YES loads the next word; NO and NOT SURE reveal the answer and a Next button. Repeated clicks on the active Check tab also advance. `GET /api/words/random?group=junior&exclude_id=123` returns a random `word` and the group's `total` in one request; `exclude_id` is optional and excludes the previous word when more than one word is available. Empty groups return a null word. Check and the progress indicator share this response.

Concurrent identical GET requests share one in-flight request. Each caller can cancel independently; the network request is canceled after all callers leave, with a one-turn grace period for React's development cleanup/setup cycle. Completed responses are not retained in this shared pool. Writes invalidate pending read reuse before and after the request so subsequent refreshes do not join a read from before the write. Add, Edit, and confirmation submissions have synchronous guards against repeated clicks; selecting the current pagination page does not reload it. Explicit retries and refreshes after mutations remain available.

Example learning scores and progress have been removed. All words are initially unstudied with score 0; group progress, studied counts, dashboard rings, and completion charts start at zero. Vocabulary totals still come from the database. Persistent review records and scheduling are not yet implemented.

Dashboard uses `GET /api/groups` to load all group word counts in one aggregate query. Cards and the area chart share that response. Groups with no words are included with a count of zero.

`GET /api/words` supports `q` for case-sensitive English and Chinese substring matching and `locate_id` to return the page containing a word under the requested group, sort order and page size. Selecting a search suggestion opens List, clears the input, scrolls to the row, and flashes its background twice.

Delete uses `ConfirmationDialog`; Add and Edit share `WordInput`, including the custom green caret and input styling.

## Postgraduate vocabulary import

`rawlist/postgraduate.txt` contains 3228 distinct entries across list01–list50. All have been imported into Postgraduate with Chinese meanings in source order: 2958 existing shared words were reused and 270 new words were added. Existing definitions and other group memberships were preserved. Twenty annotated spelling variants are mapped to standard headwords; original source text, list codes, and positions remain in membership metadata.

Run `cd server && uv run python -m app.import_postgraduate` to preview; add `--apply` to back up the vocabulary database and import atomically. Repeated imports reuse existing words and memberships. Verification details are saved in `server/data/postgraduate-import-verification.json`.

The 2026-10-29 Postgraduate review refined 352 entries after reading all 3228 words and their Chinese meanings. It corrected mistranslations, added common senses, consolidated duplicate/specialist records, and resolved all 111 words with missing POS. Postgraduate now has 5632 meaning records. Word identities, phonetics, memberships, source annotations, and order are unchanged. Shared meanings also update the same words in other groups. Reviewed lookup overrides live in `server/app/postgraduate_learner_entries.json` and feed the existing project/Junior/Senior review views. `cd server && uv run python -m app.refine_postgraduate` previews this review; `--apply` backs up and commits, rejecting edits made since the reviewed snapshot. The completed review is idempotent. See `server/data/postgraduate-review-completed.md` for the full before/after list, evidence, and review limits.

## COCA merged group

COCA currently contains 17664 words, deduplicated by spelling ignoring case. Its initial 17673-word import was reduced by nine user-selected spelling removals; the active exclusions in `rawlist/coca/spelling-preferences.json` also apply to future imports. It starts with 4380 distinct words from the supplied `wordFrequency.xlsx` lemma sheet, followed by 13293 GitHub-only words in source order. All 25250 original source occurrences and their ranks remain in membership metadata. Existing shared meanings are preserved; 10019 new words received Chinese definitions. The sidebar, Dashboard, All group tags and group filter include COCA (C). The All Groups column is 160px wide, with pale green tags displayed in a single row.

Sources, independent deduplicated lists and the merged order live in `rawlist/coca/`; see its README for provenance, normalization rules and source attribution. Run `cd server && uv run python -m app.import_coca` to preview, or add `--apply` to back up and import atomically. Alembic migration `c0ca20261030` seeds the group for new setups. Slash-containing headwords such as `and/or`, `his/her` and `he/she` are supported by saving and dictionary queries. Completion checks are saved in `server/data/coca-import-verification.json`.
