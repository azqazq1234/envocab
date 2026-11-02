"""Fetch word audio from Youdao without exposing an arbitrary proxy URL."""

from functools import lru_cache
from urllib.parse import urlencode
from urllib.request import urlopen

from fastapi import APIRouter, HTTPException, Query, Response

router = APIRouter(prefix="/api/pronunciation", tags=["pronunciation"])
MAX_AUDIO_BYTES = 512 * 1024


@lru_cache(maxsize=128)
def fetch_pronunciation(term: str) -> bytes:
    query = urlencode({"audio": term, "type": "2"})
    with urlopen(f"https://dict.youdao.com/dictvoice?{query}", timeout=8) as response:
        if response.headers.get_content_type() != "audio/mpeg":
            raise ValueError("Pronunciation provider returned non-audio content.")
        audio = response.read(MAX_AUDIO_BYTES + 1)
    if not audio or len(audio) > MAX_AUDIO_BYTES:
        raise ValueError("Pronunciation provider returned invalid audio.")
    return audio


@router.get("")
def pronunciation(
    term: str = Query(
        min_length=1, max_length=100, pattern=r"^[A-Za-z][A-Za-z .'/\-]*$"
    ),
):
    try:
        audio = fetch_pronunciation(term.strip())
    except (OSError, ValueError):
        raise HTTPException(
            status_code=502, detail="Pronunciation unavailable. Please try again."
        ) from None
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )
