import hashlib
import secrets
import unicodedata
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import User, UserSession

router = APIRouter(prefix="/api/auth")
DB = Annotated[Session, Depends(get_session)]
COOKIE = "envocab_session"
SESSION_DAYS = 30


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def require_mutation_header(
    marker: Annotated[str | None, Header(alias="X-Envocab-Request")] = None,
):
    # Cross-origin forms cannot set this header; no CORS origins are enabled.
    if marker != "1":
        raise HTTPException(403, "Invalid request origin.")


def optional_user(request: Request, db: DB) -> User | None:
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    return db.scalar(
        select(User)
        .join(UserSession, UserSession.user_id == User.id)
        .where(
            UserSession.token_hash == token_hash(token),
            UserSession.expires_at > datetime.now(UTC),
        )
    )


OptionalUser = Annotated[User | None, Depends(optional_user)]


def require_user(user: OptionalUser) -> User:
    if user is None:
        raise HTTPException(401, "Please log in first.")
    return user


CurrentUser = Annotated[User, Depends(require_user)]


def require_admin(user: CurrentUser):
    if not user.is_admin:
        raise HTTPException(403, "Only the administrator can manage vocabulary.")


class UserOut(BaseModel):
    id: int
    username: str
    is_admin: bool


def serialize_user(user: User) -> UserOut:
    return UserOut(id=user.id, username=user.username, is_admin=user.is_admin)


class LoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9_\-]+$")

    @field_validator("username", mode="before")
    @classmethod
    def normalize(cls, value):
        return (
            unicodedata.normalize("NFKC", value).strip().lower()
            if isinstance(value, str)
            else value
        )


@router.get("/me", response_model=UserOut | None)
def me(user: OptionalUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return serialize_user(user) if user else None


@router.post(
    "/login", response_model=UserOut, dependencies=[Depends(require_mutation_header)]
)
def login(data: LoginInput, request: Request, response: Response, db: DB):
    user_id = db.scalar(
        insert(User)
        .values(username=data.username)
        .on_conflict_do_update(
            index_elements=[User.username], set_={"username": data.username}
        )
        .returning(User.id)
    )
    previous = request.cookies.get(COOKIE)
    if previous:
        db.execute(
            delete(UserSession).where(UserSession.token_hash == token_hash(previous))
        )
    db.execute(delete(UserSession).where(UserSession.expires_at <= datetime.now(UTC)))
    token = secrets.token_urlsafe(32)
    db.add(
        UserSession(
            token_hash=token_hash(token),
            user_id=user_id,
            expires_at=datetime.now(UTC) + timedelta(days=SESSION_DAYS),
        )
    )
    db.commit()
    response.set_cookie(
        COOKIE,
        token,
        max_age=SESSION_DAYS * 86400,
        httponly=True,
        secure=request.headers.get("x-forwarded-proto", request.url.scheme) == "https",
        samesite="lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return serialize_user(db.get(User, user_id))


@router.post(
    "/logout", status_code=204, dependencies=[Depends(require_mutation_header)]
)
def logout(request: Request, db: DB):
    token = request.cookies.get(COOKIE)
    if token:
        db.execute(
            delete(UserSession).where(UserSession.token_hash == token_hash(token))
        )
        db.commit()
    response = Response(status_code=204)
    response.delete_cookie(COOKIE, path="/")
    return response


@router.delete("/me", status_code=204, dependencies=[Depends(require_mutation_header)])
def delete_account(user: CurrentUser, db: DB):
    if user.is_admin:
        raise HTTPException(403, "The administrator account cannot be deleted.")
    # Foreign keys cascade to this user's learning progress and every session.
    db.delete(user)
    db.commit()
    response = Response(status_code=204)
    response.delete_cookie(COOKIE, path="/")
    return response
