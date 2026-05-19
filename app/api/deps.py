from collections.abc import Generator
from typing import Annotated
import logging

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models import TokenPayload, RefreshTokenPayload, User, UserSession
from app import crud

logger = logging.getLogger(__name__)

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    try:
        logger.debug(f"🔐 Validating token: {token[:50]}...")
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        logger.debug(f"🔐 Token decoded successfully: {payload}")
        token_data = TokenPayload(**payload)
        logger.debug(f"🔐 Token data extracted: sub={token_data.sub}")
    except (InvalidTokenError, ValidationError) as e:
        logger.error(f"❌ Token validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        logger.debug(f"🔐 Looking up user with ID: {token_data.sub}")
        user = session.get(User, token_data.sub)
        if not user:
            logger.error(f"❌ User not found in database: {token_data.sub}")
            raise HTTPException(status_code=404, detail="User not found")
        logger.debug(f"🔐 User found: {user.email}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Database error while looking up user: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error") from e
    
    if not user.is_active:
        logger.error(f"❌ User is inactive: {user.email}")
        raise HTTPException(status_code=400, detail="Inactive user")
    
    logger.info(f"✅ User authenticated successfully: {user.email}")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


def get_refresh_token_payload(token: str) -> RefreshTokenPayload:
    """Validate and decode refresh token"""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = RefreshTokenPayload(**payload)
        if not token_data.sub or not token_data.session_id:
            raise ValueError("Invalid token structure")
        return token_data
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def validate_user_session(
    session: Session, user_id: str, session_id: str
) -> UserSession:
    """Validate that user session exists and is active"""
    import uuid

    try:
        session_uuid = uuid.UUID(session_id)
        user_uuid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid session or user ID",
        )

    db_session = crud.get_user_session(session=session, session_id=session_uuid)
    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session not found",
        )
    if not db_session.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session is inactive",
        )
    if db_session.user_id != user_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session does not belong to user",
        )

    return db_session
