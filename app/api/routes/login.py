from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Header, status, Body
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm

from app import crud
from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
    get_refresh_token_payload,
    validate_user_session,
)
from app.core import security
from app.core.config import settings
from app.models import Message, NewPassword, Token, UserPublic, UserUpdate
from app.utils import (
    generate_password_reset_token,
    generate_reset_password_email,
    send_email,
    verify_password_reset_token,
)

router = APIRouter(tags=["login"])


def get_device_info_from_headers(
    user_agent: str | None = Header(None),
) -> dict[str, str | None]:
    device_type = "web"
    device_name = "Unknown Device"

    if user_agent:
        user_agent_lower = user_agent.lower()

        if "mobile" in user_agent_lower or "android" in user_agent_lower:
            device_type = "mobile"
        elif "ipad" in user_agent_lower or "tablet" in user_agent_lower:
            device_type = "tablet"

        if "chrome" in user_agent_lower:
            device_name = "Chrome"
        elif "firefox" in user_agent_lower:
            device_name = "Firefox"
        elif "safari" in user_agent_lower:
            device_name = "Safari"
        elif "edge" in user_agent_lower:
            device_name = "Edge"

    return {"device_type": device_type, "device_name": device_name}


@router.post("/login/access-token", response_model=Token)
def login_access_token(
    session: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_agent: str | None = Header(None),
    x_forwarded_for: str | None = Header(None),
) -> Token:
    user = crud.authenticate(
        session=session,
        email=form_data.username,
        password=form_data.password,
    )

    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    device_info = get_device_info_from_headers(user_agent)
    ip_address = x_forwarded_for.split(",")[0] if x_forwarded_for else None

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=30)

    refresh_token_expires_at = datetime.now(timezone.utc) + refresh_token_expires

    import uuid
    from app.core.security import get_password_hash

    # IMPORTANT: one session_id used everywhere
    session_id = uuid.uuid4()

    refresh_token = security.create_refresh_token(
        subject=user.id,
        session_id=session_id,
    )

    refresh_token_hash = get_password_hash(refresh_token)

    crud.create_user_session(
        session=session,
        session_id=session_id,
        user_id=user.id,
        refresh_token_hash=refresh_token_hash,
        expires_at=refresh_token_expires_at,
        device_name=device_info.get("device_name"),
        device_type=device_info.get("device_type"),
        ip_address=ip_address,
    )

    access_token = security.create_access_token(
        user.id,
        expires_delta=access_token_expires,
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
    )


@router.post("/login/refresh", response_model=Token)
def refresh_access_token(
    session: SessionDep,
    refresh_token: str = Body(..., embed=True),
    user_agent: str | None = Header(None),
) -> Token:
    token_data = get_refresh_token_payload(refresh_token)

    db_session = validate_user_session(
        session=session,
        user_id=token_data.sub,
        session_id=token_data.session_id,
    )

    # IMPORTANT: verify refresh token hash matches stored token hash
    from app.core.security import verify_password

    is_valid, _ = verify_password(
        refresh_token,
        db_session.refresh_token_hash,
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid refresh token",
        )

    if db_session.expires_at < datetime.now(timezone.utc):
        crud.invalidate_user_session(session=session, session_id=db_session.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Refresh token has expired. Please login again.",
        )

    user = crud.get_user_by_id(
        session=session,
        user_id=db_session.user_id,
    )

    if not user or not user.is_active:
        raise HTTPException(
            status_code=404,
            detail="User not found or inactive",
        )

    crud.update_user_session_activity(
        session=session,
        session_id=db_session.id,
    )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = security.create_access_token(
        user.id,
        expires_delta=access_token_expires,
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
    )


@router.post("/login/test-token", response_model=UserPublic)
def test_token(current_user: CurrentUser) -> Any:
    return current_user


@router.post("/logout")
def logout(
    session: SessionDep,
    current_user: CurrentUser,
    session_id: str | None = None,
) -> Message:
    if session_id:
        crud.invalidate_user_session(
            session=session,
            session_id=session_id,
        )
        return Message(message="Session ended successfully")

    count = crud.invalidate_all_user_sessions(
        session=session,
        user_id=current_user.id,
    )
    return Message(message=f"Logged out from {count} device(s)")


@router.get("/sessions", response_model=list)
def get_active_sessions(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    from app.models import UserSessionPublic

    sessions = crud.get_user_sessions(
        session=session,
        user_id=current_user.id,
        active_only=True,
    )

    return [UserSessionPublic.model_validate(s) for s in sessions]


@router.post("/password-recovery/{email}")
def recover_password(email: str, session: SessionDep) -> Message:
    user = crud.get_user_by_email(session=session, email=email)

    if user:
        password_reset_token = generate_password_reset_token(email=email)
        email_data = generate_reset_password_email(
            email_to=user.email,
            email=email,
            token=password_reset_token,
        )
        send_email(
            email_to=user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )

    return Message(
        message="If that email is registered, we sent a password recovery link"
    )


@router.post("/reset-password/")
def reset_password(session: SessionDep, body: NewPassword) -> Message:
    email = verify_password_reset_token(token=body.token)

    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")

    user = crud.get_user_by_email(session=session, email=email)

    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    user_in_update = UserUpdate(password=body.new_password)

    crud.update_user(
        session=session,
        db_user=user,
        user_in=user_in_update,
    )

    return Message(message="Password updated successfully")


@router.post(
    "/password-recovery-html-content/{email}",
    dependencies=[Depends(get_current_active_superuser)],
    response_class=HTMLResponse,
)
def recover_password_html_content(email: str, session: SessionDep) -> Any:
    user = crud.get_user_by_email(session=session, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )

    password_reset_token = generate_password_reset_token(email=email)

    email_data = generate_reset_password_email(
        email_to=user.email,
        email=email,
        token=password_reset_token,
    )

    return HTMLResponse(
        content=email_data.html_content,
        headers={"subject:": email_data.subject},
    )
