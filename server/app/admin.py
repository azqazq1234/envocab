from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.auth import (
    DB,
    LoginInput,
    OptionalUser,
    UserOut,
    require_mutation_header,
    serialize_user,
)
from app.models import LearningProgress, User


def require_config_admin(user: OptionalUser):
    if user is None or not user.is_admin:
        raise HTTPException(404, "Not found.")


router = APIRouter(
    prefix="/api/admin/users", dependencies=[Depends(require_config_admin)]
)
MUTATION = [Depends(require_mutation_header)]


class AdminUserOut(UserOut):
    created_at: datetime
    studied: int


class UserPage(BaseModel):
    items: list[AdminUserOut]
    total: int
    page: int
    total_pages: int


def serialize_users(db: DB, users: list[User]) -> list[AdminUserOut]:
    counts = (
        dict(
            db.execute(
                select(LearningProgress.user_id, func.count())
                .where(LearningProgress.user_id.in_([user.id for user in users]))
                .group_by(LearningProgress.user_id)
            ).all()
        )
        if users
        else {}
    )
    return [
        AdminUserOut(
            **serialize_user(user).model_dump(),
            created_at=user.created_at,
            studied=counts.get(user.id, 0),
        )
        for user in users
    ]


def find_user(db: DB, user_id: int, *, lock: bool = False) -> User:
    query = select(User).where(User.id == user_id)
    user = db.scalar(query.with_for_update() if lock else query)
    if user is None:
        raise HTTPException(404, "User not found.")
    return user


def commit_username(db: DB):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This username already exists.") from None


@router.get("", response_model=UserPage)
def list_users(
    db: DB,
    response: Response,
    q: str = Query("", max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    response.headers["Cache-Control"] = "no-store"
    query = select(User)
    search = q.strip().lower()
    if search:
        query = query.where(User.username.contains(search, autoescape=True))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, total_pages)
    users = list(
        db.scalars(
            query.order_by(User.id).offset((page - 1) * page_size).limit(page_size)
        )
    )
    return UserPage(
        items=serialize_users(db, users),
        total=total,
        page=page,
        total_pages=total_pages,
    )


@router.get("/{user_id}", response_model=AdminUserOut)
def get_user(user_id: int, db: DB, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return serialize_users(db, [find_user(db, user_id)])[0]


@router.post("", response_model=AdminUserOut, status_code=201, dependencies=MUTATION)
def create_user(data: LoginInput, db: DB):
    user = User(username=data.username)
    db.add(user)
    commit_username(db)
    return serialize_users(db, [user])[0]


@router.patch("/{user_id}", response_model=AdminUserOut, dependencies=MUTATION)
def edit_user(user_id: int, data: LoginInput, db: DB):
    user = find_user(db, user_id, lock=True)
    if user.is_admin and user.username != data.username:
        raise HTTPException(403, "The administrator username cannot be changed.")
    user.username = data.username
    commit_username(db)
    return serialize_users(db, [user])[0]


@router.delete("/{user_id}", status_code=204, dependencies=MUTATION)
def delete_user(user_id: int, db: DB):
    user = find_user(db, user_id, lock=True)
    if user.is_admin:
        raise HTTPException(403, "The administrator account cannot be deleted.")
    db.delete(user)
    db.commit()
    return Response(status_code=204)
