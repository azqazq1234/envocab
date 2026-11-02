from typing import Annotated

from fastapi import FastAPI, HTTPException, Query

from app.admin import router as admin_router
from app.auth import router as auth_router
from app.dictionary import DictionaryEntry, lookup_word
from app.vocabulary import router as vocabulary_router

app = FastAPI(
    title="Envocab",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(vocabulary_router)


@app.get("/api/dictionary/lookup", response_model=DictionaryEntry)
def dictionary_lookup(
    term: Annotated[
        str,
        Query(min_length=1, max_length=100, pattern=r"^[A-Za-z][A-Za-z .'/\-]*$"),
    ],
):
    try:
        entry = lookup_word(term)
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    if entry is None:
        raise HTTPException(
            status_code=404, detail="No dictionary entry found for this word."
        )
    return entry
