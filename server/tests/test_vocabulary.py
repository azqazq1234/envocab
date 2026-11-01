from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import engine, get_session
from app.main import app
from app.models import Word, WordGroup, WordMeaning


@pytest.fixture
def client():
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(
            bind=connection, join_transaction_mode="create_savepoint"
        ) as session:
            app.dependency_overrides[get_session] = lambda: session
            try:
                with TestClient(app) as test_client:
                    yield test_client, session
            finally:
                app.dependency_overrides.clear()
                transaction.rollback()


def payload():
    return {
        "term": "test-"
        + uuid4().hex.translate(str.maketrans("0123456789", "ghijklmnop")),
        "phonetic": "test",
        "meanings": [{"part_of_speech": "noun", "meaning": "\u4e66"}],
    }


@pytest.mark.parametrize("misspelled,correct", [("grammer", "grammar"), ("destory", "destroy")])
def test_spelling_aliases_share_saved_identity_and_search(client, misspelled, correct):
    from app.models import VocabularyGroup

    api, db = client
    slug = "spelling-" + uuid4().hex[:10]
    db.add(VocabularyGroup(slug=slug, name="Spelling test"))
    db.flush()
    data = {**payload(), "term": misspelled}
    saved = api.post(f"/api/groups/{slug}/words", json=data).json()
    assert saved["term"] == correct
    assert api.post(f"/api/groups/{slug}/words", json={**data, "term": correct}).status_code == 409
    assert api.get("/api/words/exists", params={"group": slug, "term": misspelled}).json() == {"exists": True}
    found = api.get("/api/words", params={"group": slug, "q": misspelled}).json()
    assert [word["id"] for word in found["items"]] == [saved["id"]]


@pytest.mark.parametrize("keep_other_group", [False, True])
def test_reviewed_refinement_reuses_target_and_preserves_order(client, monkeypatch, keep_other_group):
    from app import refine_junior
    from app.models import VocabularyGroup

    api, db = client
    old_data, new_data = payload(), payload()
    old = api.post("/api/groups/junior/words", json=old_data).json()
    target = api.post("/api/groups/senior/words", json=new_data).json()
    if keep_other_group:
        api.post("/api/groups/cet4/words", json=old_data)
    group_id = db.scalar(select(VocabularyGroup.id).where(VocabularyGroup.slug == "junior"))
    membership = db.get(WordGroup, (old["id"], group_id))
    membership.position = 99999
    membership.source_term = old_data["term"]
    membership.source_entries = [{"source_term": old_data["term"], "position": 99999}]
    db.flush()
    reviewed = {"phonetic": "reviewed", "meanings": [{"part_of_speech": "noun", "meaning": "修正释义"}]}
    monkeypatch.setattr(refine_junior, "SPELLING_CORRECTIONS", {old_data["term"]: new_data["term"]})
    monkeypatch.setattr(refine_junior, "LEARNER_ENTRIES", {new_data["term"]: reviewed})
    plan = refine_junior.plan_refinement(db)
    assert len(plan["renames"]) == len(plan["replacements"]) == 1
    refine_junior.apply_refinement(db, plan)
    db.expire_all()
    saved = db.get(WordGroup, (target["id"], group_id))
    assert saved.position == 99999
    assert saved.source_term == old_data["term"]
    assert saved.source_entries == [{"source_term": old_data["term"], "position": 99999}]
    assert db.get(WordGroup, (old["id"], group_id)) is None
    assert (db.get(Word, old["id"]) is not None) == keep_other_group
    assert refine_junior.meaning_rows(db, target["id"]) == reviewed["meanings"]
    assert refine_junior.plan_refinement(db) == {"renames": [], "replacements": []}


@pytest.mark.parametrize("keep_other_group", [False, True])
def test_senior_refinement_keeps_all_memberships_metadata_and_is_idempotent(client, monkeypatch, keep_other_group):
    from app import refine_senior
    from app.models import VocabularyGroup

    api, db = client
    old_data, target_data = payload(), payload()
    old = api.post("/api/groups/senior/words", json=old_data).json()
    target = api.post("/api/groups/junior/words", json=target_data).json()
    if keep_other_group:
        api.post("/api/groups/cet4/words", json=old_data)
    group_id = db.scalar(select(VocabularyGroup.id).where(VocabularyGroup.slug == "senior"))
    membership = db.get(WordGroup, (old['id'], group_id))
    membership.position = 99999
    membership.list_code = "extend14"
    membership.source_term = old_data['term'] + ' (annotation)'
    membership.source_entries = [{"source_term": membership.source_term, "position": 99999,
                                   "list_code": "extend14"},
                                  {"source_term": old_data['term'], "position": 100000,
                                   "list_code": "basic10"}]
    db.flush()
    before = refine_senior.membership_state(db)
    protected = {w.id: refine_senior.meaning_rows(db, w.id)
                 for w in db.scalars(select(Word).where(Word.term.in_(['march', 'turkey'])))}
    reviewed = {"phonetic": "reviewed", "meanings": [{"part_of_speech": "noun", "meaning": "修正释义"}]}
    monkeypatch.setattr(refine_senior, "SENIOR_CORRECTIONS", {old_data['term']: target_data['term']})
    monkeypatch.setattr(refine_senior, "SENIOR_LEARNER_ENTRIES", {target_data['term']: reviewed})
    plan = refine_senior.plan_refinement(db)
    refine_senior.apply_refinement(db, plan)
    db.expire_all()
    expected = {((gid, target['id']) if gid == group_id and wid == old['id'] else (gid, wid)): data
                for (gid, wid), data in before.items()}
    assert refine_senior.membership_state(db) == expected
    assert (db.get(Word, old['id']) is not None) == keep_other_group
    assert refine_senior.meaning_rows(db, target['id']) == reviewed['meanings']
    assert all(refine_senior.meaning_rows(db, word_id) == meanings for word_id, meanings in protected.items())
    assert refine_senior.plan_refinement(db) == {"renames": [], "replacements": []}
    refine_senior.apply_refinement(db, {"renames": [], "replacements": []})


def test_senior_refinement_rejects_a_stale_preview_before_writing(client, monkeypatch):
    from app import refine_senior

    api, db = client
    data = payload()
    saved = api.post('/api/groups/senior/words', json=data).json()
    reviewed = {"phonetic": "reviewed", "meanings": [{"part_of_speech": "noun", "meaning": "修正释义"}]}
    monkeypatch.setattr(refine_senior, "SENIOR_CORRECTIONS", {})
    monkeypatch.setattr(refine_senior, "SENIOR_LEARNER_ENTRIES", {data['term']: reviewed})
    plan = refine_senior.plan_refinement(db)
    word = db.get(Word, saved['id'])
    word.phonetic = 'newer user edit'
    db.flush()
    before = refine_senior.meaning_rows(db, word.id)
    with pytest.raises(ValueError, match='changed since the preview'):
        refine_senior.apply_refinement(db, plan)
    assert word.phonetic == 'newer user edit'
    assert refine_senior.meaning_rows(db, word.id) == before


def test_case_sensitive_save_duplicate_check_search_and_edit(client):
    api, _ = client
    lower = payload()
    upper = {**lower, "term": lower["term"].upper(), "meanings": [{"meaning": "大写词义"}]}
    first = api.post("/api/groups/senior/words", json=lower).json()
    assert api.get("/api/words/exists", params={"group": "senior", "term": upper["term"]}).json() == {"exists": False}
    second = api.post("/api/groups/senior/words", json=upper).json()
    assert first["id"] != second["id"]
    assert second["term"] == upper["term"]
    for data, word in [(lower, first), (upper, second)]:
        assert api.post("/api/groups/senior/words", json=data).status_code == 409
        found = api.get("/api/words", params={"group": "senior", "q": data["term"]}).json()
        assert [w["id"] for w in found["items"]] == [word["id"]]
        assert api.get("/api/words/exists", params={"group": "senior", "term": data["term"]}).json() == {"exists": True}
    assert api.patch(f"/api/words/{first['id']}", json=upper).status_code == 409
    assert api.patch(f"/api/words/{second['id']}", json=upper).json()["meanings"] == [{"part_of_speech": None, "meaning": "大写词义"}]


def test_case_reconciliation_preserves_other_groups_and_manual_words(client):
    from app.import_senior import (
        SourceWord,
        import_words,
        parse_source,
        reconcile_source,
    )
    from app.models import VocabularyGroup
    from app.vocabulary import WordInput

    api, db = client
    old = payload()
    old_word = api.post("/api/groups/junior/words", json=old).json()
    api.post("/api/groups/senior/words", json=old)
    manual = api.post("/api/groups/senior/words", json=payload()).json()
    group_id = db.scalar(select(VocabularyGroup.id).where(VocabularyGroup.slug == "senior"))
    membership = db.get(WordGroup, (old_word["id"], group_id))
    membership.source_entries = [{"list_code": "basic02", "source_term": old["term"].upper(), "position": 99999}]
    upper = {**old, "term": old["term"].upper()}
    source = SourceWord(upper["term"], upper["term"], "basic02", 99999)
    import_words(db, [source], [WordInput(**upper)])
    reconcile_source(db, parse_source() + [source])
    db.flush()
    db.expire_all()
    assert db.get(WordGroup, (old_word["id"], group_id)) is None
    assert db.get(Word, old_word["id"]) is not None
    assert db.get(WordGroup, (manual["id"], group_id)) is not None
    new_id = db.scalar(select(Word.id).where(Word.term == upper["term"]))
    assert db.get(WordGroup, (new_id, group_id)).position == 99999


def test_all_membership_filter_preserves_creation_order_and_pagination(client):
    from app.models import VocabularyGroup

    api, db = client
    slug = "filter-" + uuid4().hex[:10]
    group = VocabularyGroup(slug=slug, name="Filter test")
    db.add(group)
    db.flush()
    records = []
    for prefix in ["c", "a", "b"]:
        data = payload()
        data["term"] = prefix + data["term"]
        saved = api.post(f"/api/groups/{slug}/words", json=data).json()
        records.append(saved)
        # A different source order must not affect All's creation order.
        db.get(WordGroup, (saved["id"], group.id)).position = 3 - len(records)
    db.flush()
    params = {"group": "all", "member_of": slug, "page_size": 2}
    first = api.get("/api/words", params=params).json()
    assert (first["total"], first["total_pages"]) == (3, 2)
    assert [w["id"] for w in first["items"]] == [r["id"] for r in records[:2]]
    last = api.get("/api/words", params={**params, "page": 2}).json()
    assert [w["id"] for w in last["items"]] == [records[2]["id"]]
    located = api.get(
        "/api/words", params={**params, "locate_id": records[2]["id"]}
    ).json()
    assert located["page"] == 2
    alphabetical = api.get(
        "/api/words", params={**params, "sort_by": "english", "page_size": 100}
    ).json()
    assert [w["term"] for w in alphabetical["items"]] == sorted(
        r["term"] for r in records
    )
    searched = api.get(
        "/api/words", params={**params, "q": records[1]["term"]}
    ).json()
    assert searched["total"] == 1
    assert searched["items"][0]["id"] == records[1]["id"]
    assert api.get(
        "/api/words", params={**params, "member_of": "unknown-group"}
    ).status_code == 404


def test_multiple_membership_filters_use_union_without_duplicate_words(client):
    from app.models import VocabularyGroup

    api, db = client
    slugs = ["multi-" + uuid4().hex[:10] for _ in range(2)]
    for slug in slugs:
        db.add(VocabularyGroup(slug=slug, name="Multi filter test"))
    db.flush()
    shared = payload()
    first = api.post(f"/api/groups/{slugs[0]}/words", json=shared).json()
    api.post(f"/api/groups/{slugs[1]}/words", json=shared)
    second = api.post(f"/api/groups/{slugs[1]}/words", json=payload()).json()
    params = {"group": "all", "member_of": ",".join(slugs), "page_size": 1}
    page_one = api.get("/api/words", params=params).json()
    page_two = api.get("/api/words", params={**params, "page": 2}).json()
    assert page_one["total"] == 2
    assert [page_one["items"][0]["id"], page_two["items"][0]["id"]] == [
        first["id"], second["id"]
    ]
    assert len(page_one["items"][0]["groups"]) == 2
    invalid = api.get(
        "/api/words", params={**params, "member_of": slugs[0] + ",unknown-group"}
    )
    assert invalid.status_code == 404


def test_source_import_order_metadata_and_rerun(client):
    from app.import_senior import SourceWord, import_words
    from app.models import VocabularyGroup
    from app.vocabulary import WordInput

    api, db = client
    first_data, second_data, last_data = payload(), payload(), payload()
    first = api.post("/api/groups/junior/words", json=first_data).json()
    second = api.post("/api/groups/junior/words", json=second_data).json()
    sources = [
        SourceWord(second_data["term"], second_data["term"], "core01", 1),
        SourceWord(first_data["term"], first_data["term"], "core02", 2),
    ]
    data = [WordInput(**second_data), WordInput(**first_data)]
    import_words(db, sources, data)
    import_words(db, sources, data)
    db.commit()
    last = api.post("/api/groups/senior/words", json=last_data).json()
    ids = {first["id"], second["id"], last["id"]}
    # Filter to the unique test prefix so real imported vocabulary is excluded.
    query = "/api/words?group=senior&q=test-&page_size=100"
    listed = api.get(query).json()["items"]
    assert [w["id"] for w in listed if w["id"] in ids] == [
        second["id"], first["id"], last["id"]
    ]
    descending = api.get(query + "&sort_order=desc").json()["items"]
    assert [w["id"] for w in descending if w["id"] in ids] == [
        first["id"], second["id"], last["id"]
    ]
    located = api.get(
        query.replace("page_size=100", "page_size=1")
        + f"&locate_id={first['id']}"
    ).json()
    assert located["items"][0]["id"] == first["id"]
    group_id = db.scalar(
        select(VocabularyGroup.id).where(VocabularyGroup.slug == "senior")
    )
    membership = db.get(WordGroup, (first["id"], group_id))
    assert (membership.list_code, membership.position) == ("core02", 2)
    assert "list_code" not in listed[0]


@pytest.mark.parametrize("list_code,expected", [
    ("core01", "core"), ("extend14", "extend"), ("basic10", "basic"), (None, None),
])
def test_senior_type_comes_from_its_membership(client, list_code, expected):
    from app.models import VocabularyGroup

    api, db = client
    data = payload()
    word = api.post("/api/groups/senior/words", json=data).json()
    group_id = db.scalar(
        select(VocabularyGroup.id).where(VocabularyGroup.slug == "senior")
    )
    db.get(WordGroup, (word["id"], group_id)).list_code = list_code
    db.flush()
    params = {"group": "senior", "q": data["term"]}
    listed = api.get("/api/words", params=params).json()["items"]
    assert listed[0]["senior_type"] == expected
    for types in ["core", "extend", "basic", "core,extend,basic"]:
        filtered = api.get(
            "/api/words", params={**params, "senior_types": types, "page_size": 1}
        ).json()
        matches = expected is not None and expected in types.split(",")
        assert filtered["total"] == int(matches)
        assert [w["id"] for w in filtered["items"]] == ([word["id"]] if matches else [])
    assert api.get(
        "/api/words", params={**params, "senior_types": "invalid"}
    ).status_code == 422
    edited = api.patch(f"/api/words/{word['id']}", json=data).json()
    assert edited["senior_type"] == expected


def test_import_keeps_multiple_source_lists_and_types(client):
    from app.import_senior import SourceWord, import_words
    from app.models import VocabularyGroup
    from app.vocabulary import WordInput

    api, db = client
    data = payload()
    sources = [
        SourceWord(data["term"], data["term"], "core08", 1),
        SourceWord(data["term"], data["term"], "basic02", 2),
        SourceWord(data["term"], data["term"], "basic08", 3),
    ]
    entries = [WordInput(**data)] * len(sources)
    import_words(db, sources, entries)
    import_words(db, sources, entries)
    db.commit()
    for types in ["core", "basic", "core,basic"]:
        result = api.get("/api/words", params={
            "group": "senior", "q": data["term"], "senior_types": types
        }).json()
        assert result["total"] == 1
        assert result["items"][0]["senior_types"] == ["core", "basic"]
    word_id = result["items"][0]["id"]
    group_id = db.scalar(select(VocabularyGroup.id).where(VocabularyGroup.slug == "senior"))
    membership = db.get(WordGroup, (word_id, group_id))
    assert (membership.list_code, membership.position) == ("core08", 1)
    assert [item["list_code"] for item in membership.source_entries] == [
        "core08", "basic02", "basic08"
    ]


def test_abbreviation_can_be_saved_and_edited(client):
    api, _ = client
    data = payload()
    data["term"] += ".a.m."
    response = api.post("/api/groups/junior/words", json=data)
    assert response.status_code == 200
    assert response.json()["term"] == data["term"]
    word_id = response.json()["id"]
    data["term"] += ".p.m."
    response = api.patch(f"/api/words/{word_id}", json=data)
    assert response.status_code == 200
    assert response.json()["term"] == data["term"]


def test_repeated_word_shares_meanings_across_groups(client):
    api, db = client
    data = payload()
    first = api.post("/api/groups/junior/words", json=data)
    assert first.status_code == 200
    word_id = first.json()["id"]
    data["term"] = f" {data['term']} "
    second = api.post("/api/groups/senior/words", json=data)
    assert second.status_code == 200
    assert second.json()["id"] == word_id
    assert {group["slug"] for group in second.json()["groups"]} == {"junior", "senior"}
    assert (
        db.scalar(
            select(func.count())
            .select_from(WordMeaning)
            .where(WordMeaning.word_id == word_id)
        )
        == 1
    )
    assert (
        db.scalar(
            select(func.count())
            .select_from(WordGroup)
            .where(WordGroup.word_id == word_id)
        )
        == 2
    )
    assert api.post("/api/groups/junior/words", json=data).status_code == 409
    assert (
        db.scalar(
            select(func.count())
            .select_from(WordGroup)
            .where(WordGroup.word_id == word_id)
        )
        == 2
    )
    data["meanings"].append({"part_of_speech": "verb", "meaning": "\u9884\u8ba2"})
    data["phonetic"] = "changed"
    assert api.post("/api/groups/senior/words", json=data).status_code == 409
    db.expire_all()
    assert db.get(Word, word_id).phonetic == "test"
    assert (
        db.scalar(
            select(func.count())
            .select_from(WordMeaning)
            .where(WordMeaning.word_id == word_id)
        )
        == 1
    )
    added = api.post("/api/groups/cet6/words", json=data)
    assert added.status_code == 200
    for group in ["junior", "senior", "cet6", "all"]:
        listing = api.get(
            "/api/words", params={"group": group, "page_size": 100, "locate_id": word_id}
        ).json()
        words = [word for word in listing["items"] if word["id"] == word_id]
        assert len(words) == 1
        assert len(words[0]["meanings"]) == 2
    other = api.get("/api/words?group=cet4").json()
    assert all(word["id"] != word_id for word in other["items"])


def test_duplicate_check_is_scoped_normalized_and_read_only(client):
    api, db = client
    data = payload()
    params = {"term": f" {data['term']} ", "group": "junior"}
    assert api.get("/api/words/exists", params=params).json() == {"exists": False}
    word = api.post("/api/groups/junior/words", json=data).json()
    assert api.get("/api/words/exists", params=params).json() == {"exists": True}
    params["group"] = "senior"
    assert api.get("/api/words/exists", params=params).json() == {"exists": False}
    params["group"] = "all"
    assert api.get("/api/words/exists", params=params).json() == {"exists": True}
    params["group"] = "missing"
    assert api.get("/api/words/exists", params=params).status_code == 404
    assert (
        db.scalar(
            select(func.count())
            .select_from(WordGroup)
            .where(WordGroup.word_id == word["id"])
        )
        == 1
    )


def test_duplicate_meanings_and_missing_pos(client):
    api, db = client
    data = payload()
    data["meanings"] *= 2
    data["meanings"].append({"part_of_speech": None, "meaning": "domain sense"})
    saved = api.post("/api/groups/junior/words", json=data).json()
    assert len(saved["meanings"]) == 2
    assert saved["meanings"][1]["part_of_speech"] is None
    assert (
        db.scalar(
            select(func.count())
            .select_from(WordMeaning)
            .where(WordMeaning.word_id == saved["id"])
        )
        == 2
    )


@pytest.mark.parametrize("slug", ["all", "unknown"])
def test_invalid_destination_does_not_create_word(client, slug):
    api, db = client
    data = payload()
    assert api.post(f"/api/groups/{slug}/words", json=data).status_code == 404
    assert db.scalar(select(Word.id).where(Word.term == data["term"])) is None


@pytest.mark.parametrize(
    "meanings", [[], [{"meaning": " "}], [{"part_of_speech": "n" * 41, "meaning": "x"}]]
)
def test_invalid_meanings(client, meanings):
    api, _ = client
    data = payload()
    data["meanings"] = meanings
    assert api.post("/api/groups/junior/words", json=data).status_code == 422


def test_pagination_and_unknown_group(client):
    api, _ = client
    baseline = api.get("/api/words?group=ielts").json()["total"]
    for _ in range(2):
        assert api.post("/api/groups/ielts/words", json=payload()).status_code == 200
    first = api.get("/api/words?group=ielts&page_size=1").json()
    second = api.get("/api/words?group=ielts&page_size=1&page=2").json()
    assert first["total"] == baseline + 2
    assert first["items"][0]["id"] != second["items"][0]["id"]
    assert api.get("/api/words?group=unknown").status_code == 404


def test_edit_updates_shared_meanings_and_preserves_memberships(client):
    api, _ = client
    data = payload()
    word = api.post("/api/groups/junior/words", json=data).json()
    api.post("/api/groups/senior/words", json=data)
    data["meanings"] = [{"part_of_speech": "adjective", "meaning": "revised sense"}] * 2
    response = api.patch(f"/api/words/{word['id']}", json=data)
    assert response.status_code == 200
    assert response.json()["meanings"] == [
        {"part_of_speech": "adjective", "meaning": "revised sense"}
    ]
    assert len(response.json()["groups"]) == 2
    for group in ["junior", "senior", "all"]:
        listed = api.get(
            f"/api/words?group={group}&page_size=100&locate_id={word['id']}"
        ).json()["items"]
        saved = next(item for item in listed if item["id"] == word["id"])
        assert saved["meanings"] == response.json()["meanings"]


def test_edit_term_conflict_rolls_back(client):
    api, _ = client
    first_data, second_data = payload(), payload()
    first = api.post("/api/groups/junior/words", json=first_data).json()
    second = api.post("/api/groups/senior/words", json=second_data).json()
    first_data["term"] = second["term"]
    assert api.patch(f"/api/words/{first['id']}", json=first_data).status_code == 409
    listed = api.get(
        f"/api/words?group=junior&page_size=100&locate_id={first['id']}"
    ).json()["items"]
    assert (
        next(item for item in listed if item["id"] == first["id"])["term"]
        == first["term"]
    )


def test_delete_from_group_preserves_other_group_and_cleans_last_group(client):
    api, db = client
    data = payload()
    word = api.post("/api/groups/junior/words", json=data).json()
    word_id = word["id"]
    api.post("/api/groups/senior/words", json=data)
    assert api.delete(f"/api/words/{word_id}?group=junior").status_code == 204
    assert db.get(Word, word_id) is not None
    listed = api.get(
        f"/api/words?group=senior&page_size=100&locate_id={word_id}"
    ).json()["items"]
    saved = next(item for item in listed if item["id"] == word_id)
    assert [group["slug"] for group in saved["groups"]] == ["senior"]
    assert api.delete(f"/api/words/{word_id}?group=senior").status_code == 204
    assert db.get(Word, word_id) is None
    for model in [WordMeaning, WordGroup]:
        assert (
            db.scalar(
                select(func.count()).select_from(model).where(model.word_id == word_id)
            )
            == 0
        )


def test_delete_all_removes_word_and_every_association(client):
    api, db = client
    data = payload()
    word_id = api.post("/api/groups/junior/words", json=data).json()["id"]
    api.post("/api/groups/senior/words", json=data)
    assert api.delete(f"/api/words/{word_id}?group=all").status_code == 204
    assert db.get(Word, word_id) is None
    assert (
        db.scalar(
            select(func.count())
            .select_from(WordGroup)
            .where(WordGroup.word_id == word_id)
        )
        == 0
    )


def test_delete_requires_explicit_existing_group_and_edit_validates(client):
    api, db = client
    word = api.post("/api/groups/junior/words", json=payload()).json()
    word_id = word["id"]
    assert api.delete(f"/api/words/{word_id}").status_code == 422
    assert api.delete(f"/api/words/{word_id}?group=senior").status_code == 404
    assert db.get(Word, word_id) is not None
    assert (
        api.patch(
            f"/api/words/{word_id}", json={"term": word["term"], "meanings": []}
        ).status_code
        == 422
    )
    assert api.patch("/api/words/0", json=payload()).status_code == 404
    assert api.delete("/api/words/0?group=all").status_code == 404


def test_default_page_size_custom_size_jump_and_last_page_clamp(client):
    from app.models import VocabularyGroup

    api, db = client
    slug = "paging-" + uuid4().hex[:10]
    db.add(VocabularyGroup(slug=slug, name="Pagination test"))
    db.flush()
    added_ids = []
    for _ in range(21):
        response = api.post(f"/api/groups/{slug}/words", json=payload())
        assert response.status_code == 200
        added_ids.append(response.json()["id"])
    first = api.get("/api/words", params={"group": slug}).json()
    assert first["page"] == 1
    assert first["page_size"] == 20
    assert first["total"] == 21
    assert first["total_pages"] == 2
    assert len(first["items"]) == 20
    assert [word["id"] for word in first["items"]] == added_ids[:20]
    second = api.get("/api/words", params={"group": slug, "page": 2}).json()
    assert len(second["items"]) == 1
    assert second["items"][0]["id"] == added_ids[-1]
    assert second["items"][0]["id"] not in {word["id"] for word in first["items"]}
    jumped = api.get(
        "/api/words", params={"group": slug, "page_size": 8, "page": 3}
    ).json()
    assert jumped["page_size"] == 8 and jumped["total_pages"] == 3
    assert jumped["page"] == 3 and len(jumped["items"]) == 5
    clamped = api.get(
        "/api/words", params={"group": slug, "page_size": 8, "page": 9007199254740991}
    ).json()
    assert clamped == jumped
    assert (
        api.delete(f"/api/words/{second['items'][0]['id']}?group={slug}").status_code
        == 204
    )
    after_delete = api.get("/api/words", params={"group": slug, "page": 2}).json()
    assert after_delete["page"] == 1 and after_delete["total_pages"] == 1
    assert len(after_delete["items"]) == 20


@pytest.mark.parametrize("sort_by", ["english", "chinese"])
@pytest.mark.parametrize("sort_order", ["asc", "desc"])
def test_sort_words_before_pagination(client, sort_by, sort_order):
    from app.models import VocabularyGroup

    api, db = client
    slug = "sorting-" + uuid4().hex[:10]
    db.add(VocabularyGroup(slug=slug, name="Sorting test"))
    db.flush()
    suffix = payload()["term"]
    # Reverse English and Chinese order; equal meanings must stay stable.
    records = []
    for term, meaning in [("c", "一"), ("a", "三"), ("b", "二"), ("d", "二")]:
        data = payload()
        data["term"] = term + suffix
        data["meanings"] = [
            {"meaning": meaning},
            {"meaning": "另一个释义"},
        ]
        response = api.post(f"/api/groups/{slug}/words", json=data)
        assert response.status_code == 200
        records.append(response.json())
    field = (
        (lambda word: word["term"])
        if sort_by == "english"
        else (lambda word: word["meanings"][0]["meaning"])
    )
    expected = sorted(records, key=field, reverse=sort_order == "desc")
    actual = []
    for page in [1, 2]:
        response = api.get(
            "/api/words",
            params={
                "group": slug,
                "page": page,
                "page_size": 2,
                "sort_by": sort_by,
                "sort_order": sort_order,
            },
        )
        assert response.status_code == 200
        actual.extend(response.json()["items"])
    assert [word["id"] for word in actual] == [word["id"] for word in expected]
    located = api.get(
        "/api/words",
        params={
            "group": slug,
            "page_size": 2,
            "page": 1,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "locate_id": expected[-1]["id"],
        },
    )
    assert located.status_code == 200
    assert located.json()["page"] == 2
    assert [word["id"] for word in located.json()["items"]] == [
        word["id"] for word in expected[2:]
    ]


def test_invalid_sort_parameters(client):
    api, _ = client
    assert api.get("/api/words?sort_by=invalid").status_code == 422
    assert api.get("/api/words?sort_order=invalid").status_code == 422


def test_search_matches_english_and_chinese_within_group(client):
    from app.models import VocabularyGroup

    api, db = client
    slug = "search-" + uuid4().hex[:10]
    other_slug = "other-" + uuid4().hex[:10]
    db.add_all(
        [
            VocabularyGroup(slug=slug, name="Search test"),
            VocabularyGroup(slug=other_slug, name="Other group"),
        ]
    )
    db.flush()
    first = payload()
    first["term"] = "alphabet-" + first["term"]
    first["meanings"] = [{"meaning": "测试中文释义"}, {"meaning": "另一个中文释义"}]
    response = api.post(f"/api/groups/{slug}/words", json=first)
    assert response.status_code == 200
    word_id = response.json()["id"]
    assert (
        api.get(
            "/api/words", params={"group": other_slug, "locate_id": word_id}
        ).status_code
        == 404
    )
    other = payload()
    other["term"] = "alphabet-" + other["term"]
    other["meanings"] = first["meanings"]
    assert api.post(f"/api/groups/{other_slug}/words", json=other).status_code == 200
    for search in ["phab", "中文", " 测试中文 "]:
        response = api.get(
            "/api/words", params={"group": slug, "q": search, "page_size": 1}
        )
        assert response.status_code == 200
        page = response.json()
        assert page["total"] == 1
        assert [word["id"] for word in page["items"]] == [word_id]
    for search in ["PHAB", "missing-word", "%", "_"]:
        response = api.get("/api/words", params={"group": slug, "q": search})
        assert response.status_code == 200
        assert response.json()["total"] == 0


def test_group_summaries_include_empty_groups_and_shared_memberships(client):
    from app.models import VocabularyGroup

    api, db = client
    slugs = ["stats-" + uuid4().hex[:10] for _ in range(3)]
    db.add_all([VocabularyGroup(slug=slug, name=slug) for slug in slugs])
    db.flush()
    shared = payload()
    for slug in slugs[:2]:
        assert api.post(f"/api/groups/{slug}/words", json=shared).status_code == 200
    assert api.post(f"/api/groups/{slugs[0]}/words", json=payload()).status_code == 200
    response = api.get("/api/groups")
    assert response.status_code == 200
    groups = {group["slug"]: group for group in response.json()}
    assert [groups[slug]["total"] for slug in slugs] == [2, 1, 0]
    assert groups[slugs[0]]["name"] == slugs[0]


def test_empty_pagination(client):
    from app.models import VocabularyGroup

    api, db = client
    slug = "empty-" + uuid4().hex[:10]
    db.add(VocabularyGroup(slug=slug, name="Empty test"))
    db.flush()
    page = api.get("/api/words", params={"group": slug, "page": 10}).json()
    assert page == {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 20,
        "total_pages": 1,
    }


def test_random_word_handles_empty_single_and_excluded_words(client):
    from app.models import VocabularyGroup

    api, db = client
    slug = "random-" + uuid4().hex[:10]
    db.add(VocabularyGroup(slug=slug, name="Random test"))
    db.flush()
    response = api.get("/api/words/random", params={"group": slug})
    assert response.status_code == 200
    assert response.json() == {"word": None, "total": 0}
    first = api.post(f"/api/groups/{slug}/words", json=payload()).json()
    single = api.get(
        "/api/words/random", params={"group": slug, "exclude_id": first["id"]}
    ).json()
    assert single == {"word": first, "total": 1}
    second = api.post(f"/api/groups/{slug}/words", json=payload()).json()
    for previous, expected in [(first, second), (second, first)]:
        response = api.get(
            "/api/words/random", params={"group": slug, "exclude_id": previous["id"]}
        )
        assert response.status_code == 200
        assert response.json() == {"word": expected, "total": 2}
    invalid_exclusion = api.get(
        "/api/words/random", params={"group": slug, "exclude_id": 999999999}
    ).json()
    assert invalid_exclusion["word"]["id"] in {first["id"], second["id"]}
    assert invalid_exclusion["total"] == 2
    assert api.get("/api/words/random?group=missing").status_code == 404
    assert api.get("/api/words/random?exclude_id=0").status_code == 422


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page": -1},
        {"page": 1.5},
        {"page_size": 0},
        {"page_size": 101},
        {"page_size": 1.5},
    ],
)
def test_invalid_pagination(client, params):
    api, _ = client
    assert api.get("/api/words", params=params).status_code == 422
