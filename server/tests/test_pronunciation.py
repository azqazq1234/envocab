from email.message import Message
from io import BytesIO
from urllib.error import URLError
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.pronunciation import MAX_AUDIO_BYTES, fetch_pronunciation


@pytest.fixture(autouse=True)
def clear_audio_cache():
    fetch_pronunciation.cache_clear()
    yield
    fetch_pronunciation.cache_clear()


def mock_audio(monkeypatch, body=b"ID3audio", content_type="audio/mpeg"):
    calls = []

    def open_audio(url, timeout):
        calls.append((url, timeout))
        response = BytesIO(body)
        response.headers = Message()
        response.headers["Content-Type"] = content_type
        return response

    monkeypatch.setattr("app.pronunciation.urlopen", open_audio)
    return calls


def test_audio_proxy_encodes_term_and_caches_success(monkeypatch):
    calls = mock_audio(monkeypatch)
    with TestClient(app) as client:
        for _ in range(2):
            response = client.get("/api/pronunciation", params={"term": "mother-in-law's book"})
            assert response.status_code == 200
            assert response.content == b"ID3audio"
            assert response.headers["content-type"] == "audio/mpeg"
            assert response.headers["cache-control"] == "public, max-age=86400"
    assert len(calls) == 1
    url, timeout = calls[0]
    assert urlsplit(url).netloc == "dict.youdao.com"
    assert parse_qs(urlsplit(url).query) == {"audio": ["mother-in-law's book"], "type": ["2"]}
    assert timeout == 8


@pytest.mark.parametrize("term", ["", " ", "123", "https://example.com", "book?x=1", "a" * 101])
def test_invalid_term_does_not_call_provider(monkeypatch, term):
    calls = mock_audio(monkeypatch)
    with TestClient(app) as client:
        assert client.get("/api/pronunciation", params={"term": term}).status_code == 422
    assert not calls


@pytest.mark.parametrize("error", [URLError("unavailable"), TimeoutError("timeout")])
def test_provider_failure_is_retryable(monkeypatch, error):
    def unavailable(*args, **kwargs):
        raise error

    monkeypatch.setattr("app.pronunciation.urlopen", unavailable)
    with TestClient(app) as client:
        response = client.get("/api/pronunciation", params={"term": "hello"})
        assert response.status_code == 502
        assert "cache-control" not in response.headers
        mock_audio(monkeypatch)
        assert client.get("/api/pronunciation", params={"term": "hello"}).status_code == 200


@pytest.mark.parametrize("body,content_type", [(b"<html>error</html>", "text/html"), (b"", "audio/mpeg"), (b"x" * (MAX_AUDIO_BYTES + 1), "audio/mpeg")])
def test_invalid_provider_response(monkeypatch, body, content_type):
    mock_audio(monkeypatch, body, content_type)
    with TestClient(app) as client:
        assert client.get("/api/pronunciation", params={"term": "hello"}).status_code == 502
