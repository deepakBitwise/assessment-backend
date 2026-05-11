import uuid
from typing import Any

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import Item, ItemCreate, User, UserCreate, UserUpdate, UserSession


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create,
        update={"hashed_password": get_password_hash(user_create.password)},
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}

    if "password" in user_data:
        password = user_data["password"]
        extra_data["hashed_password"] = get_password_hash(password)

    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    return session.exec(statement).first()


def get_user_by_id(*, session: Session, user_id: uuid.UUID) -> User | None:
    return session.get(User, user_id)


DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$MjQyZWE1MzBjYjJlZTI0Yw$YTU4NGM5ZTZmYjE2NzZlZjY0ZWY3ZGRkY2U2OWFjNjk"


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)

    if not db_user:
        verify_password(password, DUMMY_HASH)
        return None

    verified, updated_password_hash = verify_password(
        password,
        db_user.hashed_password,
    )

    if not verified:
        return None

    if updated_password_hash:
        db_user.hashed_password = updated_password_hash
        session.add(db_user)
        session.commit()
        session.refresh(db_user)

    return db_user


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


# -----------------------------
# Session Management
# -----------------------------

def create_user_session(
    *,
    session: Session,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    refresh_token_hash: str,
    expires_at: Any,
    device_name: str | None = None,
    device_type: str | None = None,
    ip_address: str | None = None,
) -> UserSession:
    db_session = UserSession(
        id=session_id,
        user_id=user_id,
        refresh_token_hash=refresh_token_hash,
        expires_at=expires_at,
        device_name=device_name,
        device_type=device_type,
        ip_address=ip_address,
    )

    session.add(db_session)
    session.commit()
    session.refresh(db_session)
    return db_session


def get_user_session(*, session: Session, session_id: uuid.UUID) -> UserSession | None:
    return session.get(UserSession, session_id)


def get_user_sessions(
    *,
    session: Session,
    user_id: uuid.UUID,
    active_only: bool = True,
) -> list[UserSession]:
    statement = select(UserSession).where(UserSession.user_id == user_id)

    if active_only:
        statement = statement.where(UserSession.is_active == True)

    return session.exec(statement).all()


def update_user_session_activity(
    *,
    session: Session,
    session_id: uuid.UUID,
) -> UserSession | None:
    db_session = session.get(UserSession, session_id)

    if db_session:
        from datetime import datetime, timezone

        db_session.last_accessed = datetime.now(timezone.utc)
        session.add(db_session)
        session.commit()
        session.refresh(db_session)

    return db_session


def invalidate_user_session(
    *,
    session: Session,
    session_id: uuid.UUID,
) -> UserSession | None:
    db_session = session.get(UserSession, session_id)

    if db_session:
        db_session.is_active = False
        session.add(db_session)
        session.commit()
        session.refresh(db_session)

    return db_session


def invalidate_all_user_sessions(
    *,
    session: Session,
    user_id: uuid.UUID,
) -> int:
    statement = (
        select(UserSession)
        .where(UserSession.user_id == user_id)
        .where(UserSession.is_active == True)
    )

    sessions = session.exec(statement).all()

    for db_session in sessions:
        db_session.is_active = False
        session.add(db_session)

    session.commit()
    return len(sessions)