from collections.abc import AsyncIterator

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import UserRole, require_role, resolve_current_user
from app.db.session import get_db_session
from app.models import User


async def db_session() -> AsyncIterator[AsyncSession]:
    async for session in get_db_session():
        yield session


async def current_user(
    session: AsyncSession = Depends(db_session),
    x_user_email: str | None = Header(default=None),
) -> User:
    return await resolve_current_user(session, x_user_email)


async def learner_user(user: User = Depends(current_user)) -> User:
    require_role(user, UserRole.learner, UserRole.reviewer, UserRole.admin)
    return user


async def reviewer_user(user: User = Depends(current_user)) -> User:
    require_role(user, UserRole.reviewer, UserRole.admin)
    return user


async def admin_user(user: User = Depends(current_user)) -> User:
    require_role(user, UserRole.admin)
    return user
