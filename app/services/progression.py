from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Assessment, Attempt, Level, Submission, User, Verdict


async def list_progress_for_user(session: AsyncSession, user: User) -> list[dict]:
    levels = (
        await session.scalars(
            select(Level)
            .options(selectinload(Level.assessments))
            .order_by(Level.ordinal.asc())
        )
    ).all()
    attempts = (
        await session.scalars(
            select(Attempt)
            .where(Attempt.user_id == user.id)
            .options(selectinload(Attempt.assessment), selectinload(Attempt.submission).selectinload(Submission.verdict))
        )
    ).all()

    by_level: dict[int, list[Attempt]] = {}
    for attempt in attempts:
        level_id = attempt.assessment.level_id
        by_level.setdefault(level_id, []).append(attempt)

    progress: list[dict] = []
    previous_passed = True
    now = datetime.now(timezone.utc)
    for level in levels:
        level_attempts = sorted(by_level.get(level.id, []), key=lambda item: item.attempt_no)
        latest = level_attempts[-1] if level_attempts else None
        passed = bool(latest and latest.submission and latest.submission.verdict and latest.submission.verdict.state == "passed")

        if level.ordinal == 1:
            state = "available"
        elif previous_passed:
            state = "available"
        else:
            state = "locked"

        if latest:
            if latest.submission is None:
                state = "in_progress"
            elif latest.submission.verdict is None:
                state = "under_review"
            elif latest.submission.verdict.state == "passed":
                state = "passed"
            else:
                state = "cooldown" if latest.cooldown_until and latest.cooldown_until > now else "available"

        progress.append(
            {
                "level_id": level.public_id,
                "ordinal": level.ordinal,
                "slug": level.slug,
                "title": level.title,
                "state": state,
                "attempts_used": len(level_attempts),
                "latest_attempt_id": latest.public_id if latest else None,
                "latest_submission_id": latest.submission.public_id if latest and latest.submission else None,
                "latest_score": latest.submission.verdict.weighted_score if latest and latest.submission and latest.submission.verdict else None,
            }
        )
        previous_passed = passed
    return progress


def can_start_level(progress: list[dict], assessment: Assessment) -> bool:
    for item in progress:
        if item["level_id"] == assessment.level.public_id:
            return item["state"] in {"available", "in_progress"}
    return False
