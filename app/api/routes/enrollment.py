from typing import Any

from fastapi import APIRouter, HTTPException, status

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import Assessment, User, UserPublic

router = APIRouter(prefix="/users", tags=["enrollment"])


def _require_admin(current_user: User) -> None:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )


def _get_user_by_username_or_404(session: SessionDep, username: str) -> User:
    user = crud.get_user_by_username(session=session, username=username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/{username}/enrollments", response_model=list[str])
def list_enrollments(
    username: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    if not current_user.is_superuser and current_user.username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    user = _get_user_by_username_or_404(session, username)
    return user.enrolled_assessments


@router.post(
    "/{username}/enrollments/{assessment_id}",
    response_model=UserPublic,
    status_code=status.HTTP_200_OK,
)
def enroll_user(
    username: str,
    assessment_id: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    _require_admin(current_user)

    user = _get_user_by_username_or_404(session, username)

    assessment = session.get(Assessment, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if assessment_id in user.enrolled_assessments:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already enrolled in this assessment",
        )

    user.enrolled_assessments = [*user.enrolled_assessments, assessment_id]
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.delete(
    "/{username}/enrollments/{assessment_id}",
    response_model=UserPublic,
)
def unenroll_user(
    username: str,
    assessment_id: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    _require_admin(current_user)

    user = _get_user_by_username_or_404(session, username)

    if assessment_id not in user.enrolled_assessments:
        raise HTTPException(
            status_code=404,
            detail="User is not enrolled in this assessment",
        )

    user.enrolled_assessments = [
        a for a in user.enrolled_assessments if a != assessment_id
    ]
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
