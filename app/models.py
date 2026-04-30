from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Cohort(Base):
    __tablename__ = "cohorts"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rubric_version: Mapped[str] = mapped_column(String(64))

    users: Mapped[list[User]] = relationship(back_populates="cohort")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(32), index=True)
    cohort_id: Mapped[int | None] = mapped_column(ForeignKey("cohorts.id"))
    dify_workspace_id: Mapped[str | None] = mapped_column(String(100))

    cohort: Mapped[Cohort | None] = relationship(back_populates="users")
    attempts: Mapped[list[Attempt]] = relationship(back_populates="user")


class LearningPath(Base):
    __tablename__ = "learning_paths"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    active_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    levels: Mapped[list[Level]] = relationship(back_populates="path")


class Level(Base):
    __tablename__ = "levels"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    path_id: Mapped[int] = mapped_column(ForeignKey("learning_paths.id"))
    ordinal: Mapped[int] = mapped_column(Integer, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    capability: Mapped[str] = mapped_column(String(200))
    course_anchor: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text)

    path: Mapped[LearningPath] = relationship(back_populates="levels")
    assessments: Mapped[list[Assessment]] = relationship(back_populates="level")


class Assessment(Base):
    __tablename__ = "assessments"
    __table_args__ = (UniqueConstraint("level_id", "version", name="uq_assessments_level_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id"))
    version: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(200))
    active_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    spec: Mapped[dict] = mapped_column(JSON)
    rubric_version: Mapped[str] = mapped_column(String(64))

    level: Mapped[Level] = relationship(back_populates="assessments")
    attempts: Mapped[list[Attempt]] = relationship(back_populates="assessment")


class Attempt(Base):
    __tablename__ = "attempts"
    __table_args__ = (UniqueConstraint("user_id", "assessment_id", "attempt_no", name="uq_attempt_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id"))
    attempt_no: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(32), default="in_progress")
    rubric_version: Mapped[str] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="attempts")
    assessment: Mapped[Assessment] = relationship(back_populates="attempts")
    submission: Mapped[Submission | None] = relationship(back_populates="attempt", uselist=False)


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.id"), unique=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    app_url: Mapped[str | None] = mapped_column(String(500))
    dify_app_id: Mapped[str | None] = mapped_column(String(100))
    encrypted_api_key: Mapped[str | None] = mapped_column(Text)
    evaluation_summary: Mapped[dict | None] = mapped_column(JSON)

    attempt: Mapped[Attempt] = relationship(back_populates="submission")
    artifacts: Mapped[list[Artifact]] = relationship(back_populates="submission")
    automated_run: Mapped[AutomatedRun | None] = relationship(back_populates="submission", uselist=False)
    judge_runs: Mapped[list[JudgeRun]] = relationship(back_populates="submission")
    reviews: Mapped[list[HumanReview]] = relationship(back_populates="submission")
    verdict: Mapped[Verdict | None] = relationship(back_populates="submission", uselist=False)


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"))
    role: Mapped[str] = mapped_column(String(64))
    filename: Mapped[str] = mapped_column(String(255))
    object_key: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    checksum: Mapped[str] = mapped_column(String(128))

    submission: Mapped[Submission] = relationship(back_populates="artifacts")


class AutomatedRun(Base):
    __tablename__ = "automated_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), unique=True)
    checks: Mapped[dict] = mapped_column(JSON)
    verdict: Mapped[str] = mapped_column(String(32))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    submission: Mapped[Submission] = relationship(back_populates="automated_run")


class JudgeRun(Base):
    __tablename__ = "judge_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"))
    run_no: Mapped[int] = mapped_column(Integer)
    scores: Mapped[dict] = mapped_column(JSON)
    rationale: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)

    submission: Mapped[Submission] = relationship(back_populates="judge_runs")


class HumanReview(Base):
    __tablename__ = "human_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"))
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    scores: Mapped[dict] = mapped_column(JSON)
    notes: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String(32))
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    submission: Mapped[Submission] = relationship(back_populates="reviews")


class Verdict(Base):
    __tablename__ = "verdicts"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), unique=True)
    state: Mapped[str] = mapped_column(String(32))
    weighted_score: Mapped[float] = mapped_column(Float)
    dimension_scores: Mapped[dict] = mapped_column(JSON)
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reason: Mapped[str] = mapped_column(Text)

    submission: Mapped[Submission] = relationship(back_populates="verdict")


class Appeal(Base):
    __tablename__ = "appeals"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"))
    opened_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="open")
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UploadGrant(Base):
    __tablename__ = "upload_grants"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    attempt_public_id: Mapped[str] = mapped_column(String(32), index=True)
    object_key: Mapped[str] = mapped_column(String(500), unique=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    uploaded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_public_id: Mapped[str | None] = mapped_column(String(32))
    entity_ref: Mapped[str] = mapped_column(String(128), index=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
