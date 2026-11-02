from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import COOKIE, token_hash
from app.database import engine, get_session
from app.main import app
from app.models import LearningProgress, User, UserSession


@pytest.fixture
def client():
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            app.dependency_overrides[get_session] = lambda: session
            try:
                with TestClient(app, headers={"X-Envocab-Request": "1"}) as api:
                    yield api, session
            finally:
                app.dependency_overrides.clear()
                transaction.rollback()


def login(api, username):
    response = api.post("/api/auth/login", json={"username": username})
    assert response.status_code == 200
    return response.json()


def create_word(api):
    login(api, "harvey")
    suffix = uuid4().hex.translate(str.maketrans("0123456789", "ghijklmnop"))
    data = {"term": "auth-" + suffix, "meanings": [{"meaning": "测试"}]}
    response = api.post("/api/groups/junior/words", json=data)
    assert response.status_code == 200
    return response.json(), data


def test_login_normalizes_username_persists_and_revokes_session(client):
    api, db = client
    assert api.get("/api/auth/me").json() is None
    username = "learner_" + uuid4().hex
    user = login(api, f" {username.upper()} ")
    assert user["username"] == username
    assert user["is_admin"] is False
    token = api.cookies.get(COOKIE)
    stored = db.get(UserSession, token_hash(token))
    assert stored is not None and stored.token_hash != token
    assert api.get("/api/auth/me").json() == user
    cookie = api.post("/api/auth/login", json={"username": username}).headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert db.get(UserSession, token_hash(token)) is None
    revoked = api.cookies.get(COOKIE)
    assert api.post("/api/auth/logout").status_code == 204
    assert api.cookies.get(COOKIE) is None
    assert api.get("/api/auth/me").json() is None
    api.cookies.set(COOKIE, revoked)
    assert api.get("/api/auth/me").json() is None
    assert login(api, username) == user


@pytest.mark.parametrize("username", ["", " ", "a b", "x" * 41, "../admin", "张三"])
def test_invalid_usernames(client, username):
    api, _ = client
    assert api.post("/api/auth/login", json={"username": username}).status_code == 422


def test_permissions_are_enforced_on_server(client):
    api, _ = client
    word, data = create_word(api)
    word_id = word["id"]
    api.post("/api/auth/logout")
    for expected, username in [(401, None), (403, "learner_" + uuid4().hex)]:
        if username:
            login(api, username)
        assert api.post("/api/groups/senior/words", json=data).status_code == expected
        assert api.patch(f"/api/words/{word_id}", json=data).status_code == expected
        assert api.delete(f"/api/words/{word_id}?group=all").status_code == expected
        assert api.get("/api/words?group=junior").status_code == 200
    assert login(api, "HARVEY")["is_admin"] is True
    assert api.patch(f"/api/words/{word_id}", json=data).status_code == 200
    assert api.delete(f"/api/words/{word_id}?group=all").status_code == 204


def test_fsrs_progress_isolated_persistent_and_shared_across_groups(client):
    api, db = client
    word, data = create_word(api)
    word_id = word["id"]
    assert api.post("/api/groups/senior/words", json=data).status_code == 200
    username = "learner_" + uuid4().hex
    first = login(api, username)
    baseline = {g["slug"]: g for g in api.get("/api/groups?include_all=true").json()}
    for _ in range(7):
        response = api.post(f"/api/words/{word_id}/progress", json={"answer": "yes"})
        assert response.status_code == 200
    assert 1 <= response.json()["score"] < 5
    assert response.json()["studied"] is True
    assert api.post(f"/api/words/{word_id}/progress", json={"answer": "not_sure"}).status_code == 200
    assert api.post(f"/api/words/{word_id}/progress", json={"answer": "no"}).json()["score"] == 0
    for slug in ["junior", "senior", "all"]:
        listed = api.get("/api/words", params={"group": slug, "q": word["term"]}).json()["items"]
        assert len(listed) == 1 and listed[0]["score"] == 0
    groups = {g["slug"]: g for g in api.get("/api/groups?include_all=true").json()}
    for slug in ["junior", "senior", "all"]:
        assert groups[slug]["studied"] == baseline[slug]["studied"] + 1
        assert groups[slug]["score_counts"][0] == baseline[slug]["score_counts"][0]
        assert groups[slug]["completion"] == 0
    second = login(api, "other_" + uuid4().hex)
    assert second["id"] != first["id"]
    own = api.get("/api/words", params={"q": word["term"]}).json()["items"][0]
    assert own["score"] == 0 and own["studied"] is False
    api.post(f"/api/words/{word_id}/progress", json={"answer": "no"})
    assert db.get(LearningProgress, (second["id"], word_id)).score == 0
    assert login(api, username) == first
    assert api.get("/api/words", params={"q": word["term"]}).json()["items"][0]["score"] == 0
    assert db.get(LearningProgress, (first["id"], word_id)).attempts == 9
    login(api, "harvey")
    assert api.delete(f"/api/words/{word_id}?group=all").status_code == 204
    assert db.scalar(select(LearningProgress).where(LearningProgress.word_id == word_id)) is None


def test_expired_forged_and_logged_out_sessions_cannot_record_progress(client):
    api, db = client
    word, _ = create_word(api)
    token = api.cookies.get(COOKIE)
    stored = db.get(UserSession, token_hash(token))
    stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    assert api.get("/api/auth/me").json() is None
    assert api.post(f"/api/words/{word['id']}/progress", json={"answer": "yes"}).status_code == 401
    api.cookies.set(COOKIE, "forged")
    assert api.get("/api/auth/me").json() is None
    login(api, "learner_" + uuid4().hex)
    assert api.post("/api/words/0/progress", json={"answer": "yes"}).status_code == 404
    assert api.post(f"/api/words/{word['id']}/progress", json={"answer": "invalid"}).status_code == 422


def test_cross_origin_form_mutations_are_rejected(client):
    api, db = client
    api.headers.pop("X-Envocab-Request")
    assert api.post("/api/auth/login", json={"username": "csrf_" + uuid4().hex}).status_code == 403
    assert api.post("/api/auth/logout").status_code == 403
    assert db.scalar(select(User).where(User.username.like("csrf_%"))) is None


def test_delete_account_erases_only_own_data_and_revokes_all_sessions(client):
    from app.models import Word

    api, db = client
    word, _ = create_word(api)
    word_id = word["id"]
    other = login(api, "other_" + uuid4().hex)
    other_token = api.cookies.get(COOKIE)
    assert api.post(f"/api/words/{word_id}/progress", json={"answer": "yes"}).status_code == 200
    # Start an independent browser session so logging in does not rotate the other account.
    api.cookies.clear()
    username = "delete_" + uuid4().hex
    owner = login(api, username)
    owner_token = api.cookies.get(COOKIE)
    assert api.post(f"/api/words/{word_id}/progress", json={"answer": "yes"}).status_code == 200
    extra_token = uuid4().hex
    db.add(UserSession(
        token_hash=token_hash(extra_token), user_id=owner["id"],
        expires_at=datetime.now(UTC) + timedelta(days=1),
    ))
    db.commit()

    assert api.delete("/api/auth/me").status_code == 204
    assert api.cookies.get(COOKIE) is None
    db.expire_all()
    assert db.get(User, owner["id"]) is None
    assert db.scalar(select(LearningProgress).where(LearningProgress.user_id == owner["id"])) is None
    assert db.scalar(select(UserSession).where(UserSession.user_id == owner["id"])) is None
    assert db.get(User, other["id"]) is not None
    assert db.get(LearningProgress, (other["id"], word_id)).score == 1
    assert db.get(Word, word_id) is not None

    for token in [owner_token, extra_token]:
        api.cookies.clear()
        api.cookies.set(COOKIE, token)
        assert api.get("/api/auth/me").json() is None
    api.cookies.clear()
    api.cookies.set(COOKIE, other_token)
    assert api.get("/api/auth/me").json()["id"] == other["id"]
    recreated = login(api, username)
    assert recreated["id"] != owner["id"]
    saved = api.get("/api/words", params={"q": word["term"]}).json()["items"][0]
    assert saved["score"] == 0 and saved["studied"] is False


def test_delete_account_requires_valid_session_and_mutation_header(client):
    api, db = client
    assert api.delete("/api/auth/me").status_code == 401
    owner = login(api, "delete_" + uuid4().hex)
    api.headers.pop("X-Envocab-Request")
    assert api.delete("/api/auth/me").status_code == 403
    assert db.get(User, owner["id"]) is not None


def test_administrator_account_cannot_be_deleted(client):
    api, db = client
    admin = login(api, "harvey")
    token = api.cookies.get(COOKIE)
    assert api.delete("/api/auth/me").status_code == 403
    assert db.get(User, admin["id"]) is not None
    assert db.get(UserSession, token_hash(token)) is not None
    assert api.get("/api/auth/me").json() == admin



@pytest.mark.parametrize("username", [None, "admin", "harvey_test"])
def test_config_apis_are_hidden_from_non_administrators(client, username):
    api, _ = client
    if username:
        login(api, username)
    for response in [
        api.get("/api/admin/users"),
        api.get("/api/admin/users/1"),
        api.post("/api/admin/users", json={"username": "new_user"}),
        api.patch("/api/admin/users/1", json={"username": "renamed"}),
        api.delete("/api/admin/users/1"),
    ]:
        assert response.status_code == 404


def test_admin_user_crud_preserves_progress_then_cleans_deleted_user(client):
    api, db = client
    word, _ = create_word(api)
    username = "cfg_" + uuid4().hex
    owner = login(api, username)
    token = api.cookies.get(COOKIE)
    assert api.post(f"/api/words/{word['id']}/progress", json={"answer": "yes"}).status_code == 200
    api.cookies.clear()
    admin = login(api, "harvey")
    detail = api.get(f"/api/admin/users/{owner['id']}")
    assert detail.status_code == 200
    assert detail.json()["studied"] == 1
    assert detail.headers["cache-control"] == "no-store"

    added_name = "cfg_" + uuid4().hex
    created = api.post("/api/admin/users", json={"username": f" {added_name.upper()} "})
    assert created.status_code == 201
    assert created.json()["username"] == added_name
    assert created.json()["is_admin"] is False
    assert created.json()["studied"] == 0
    assert api.post("/api/admin/users", json={"username": added_name}).status_code == 409
    assert api.post("/api/admin/users", json={"username": "bad user"}).status_code == 422

    renamed = "edit_" + uuid4().hex
    response = api.patch(f"/api/admin/users/{owner['id']}", json={"username": renamed})
    assert response.status_code == 200
    assert response.json()["studied"] == 1
    assert response.json()["username"] == renamed
    assert api.patch(f"/api/admin/users/{owner['id']}", json={"username": added_name}).status_code == 409
    assert db.get(User, owner["id"]).username == renamed
    assert api.patch(f"/api/admin/users/{admin['id']}", json={"username": "different_admin"}).status_code == 403
    assert api.delete(f"/api/admin/users/{admin['id']}").status_code == 403

    assert api.delete(f"/api/admin/users/{owner['id']}").status_code == 204
    db.expire_all()
    assert db.get(User, owner["id"]) is None
    assert db.get(LearningProgress, (owner["id"], word["id"])) is None
    assert db.get(UserSession, token_hash(token)) is None
    assert db.get(User, admin["id"]) is not None
    assert api.get(f"/api/admin/users/{owner['id']}").status_code == 404
    assert api.patch(f"/api/admin/users/{owner['id']}", json={"username": "missing"}).status_code == 404
    assert api.delete(f"/api/admin/users/{owner['id']}").status_code == 404


def test_admin_user_list_search_pagination_and_mutation_guard(client):
    api, _ = client
    login(api, "harvey")
    prefix = "cfg_" + uuid4().hex[:12]
    ids = []
    for suffix in ["a", "b", "c"]:
        ids.append(api.post("/api/admin/users", json={"username": prefix + suffix}).json()["id"])
    first = api.get("/api/admin/users", params={"q": prefix, "page_size": 2}).json()
    assert first["total"] == 3 and first["total_pages"] == 2
    assert [user["id"] for user in first["items"]] == ids[:2]
    last = api.get("/api/admin/users", params={"q": prefix, "page_size": 2, "page": 999}).json()
    assert last["page"] == 2 and last["items"][0]["id"] == ids[2]
    assert api.get("/api/admin/users", params={"q": "%"}).json()["total"] == 0
    assert api.get("/api/admin/users", params={"page_size": 0}).status_code == 422
    api.headers.pop("X-Envocab-Request")
    assert api.post("/api/admin/users", json={"username": "guarded"}).status_code == 403
    assert api.patch(f"/api/admin/users/{ids[0]}", json={"username": "guarded"}).status_code == 403
    assert api.delete(f"/api/admin/users/{ids[0]}").status_code == 403
