import uuid
from dataclasses import dataclass
from enum import StrEnum

from fastapi import Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import User


class UserRole(StrEnum):
    learner = "learner"
    reviewer = "reviewer"
    admin = "admin"


@dataclass(slots=True)
class AuthContext:
    user: User


async def resolve_current_user(
    session: AsyncSession,
    x_user_email: str | None,
) -> User:
    settings = get_settings()
    email = x_user_email or settings.dev_default_user_email
    user = await session.scalar(select(User).options(selectinload(User.cohort)).where(User.email == email))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unknown user '{email}'. Seed data only supports configured demo accounts.",
        )
    return user


def require_role(user: User, *roles: UserRole) -> None:
    if user.role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role for this operation.")


def new_public_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"
