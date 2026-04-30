from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    email: str
    full_name: str
    role: str


class MeResponse(BaseModel):
    user: UserSummary
    cohort: dict[str, Any] | None
    progress: list[dict[str, Any]]


class AssessmentBrief(BaseModel):
    id: str
    level: int
    slug: str
    title: str
    capability: str
    course_anchor: str
    version: str
    rubric_version: str
    summary: str
    spec: dict[str, Any]


class AttemptCreateRequest(BaseModel):
    assessment_id: str


class AttemptResponse(BaseModel):
    attempt_id: str
    rubric_version: str
    state: str
    attempt_no: int


class UploadPresignRequest(BaseModel):
    attempt_id: str
    filename: str
    content_type: str


class UploadPresignResponse(BaseModel):
    upload_token: str
    upload_url: str
    object_key: str
    expires_in: int = 600


class ArtifactRef(BaseModel):
    object_key: str
    role: str


class LiveAppPayload(BaseModel):
    url: HttpUrl
    api_key_ciphertext: str | None = None
    dify_app_id: str | None = None


class SubmissionCreateRequest(BaseModel):
    artifacts: list[ArtifactRef]
    live_app: LiveAppPayload | None = None


class SubmissionResponse(BaseModel):
    submission_id: str
    status: str
    estimated_first_result_ms: int = 180000


class SubmissionDetail(BaseModel):
    submission_id: str
    attempt_id: str
    status: str
    submitted_at: datetime
    app_url: str | None
    artifacts: list[dict[str, Any]]
    automated_run: dict[str, Any] | None
    judge_runs: list[dict[str, Any]]
    reviews: list[dict[str, Any]]
    verdict: dict[str, Any] | None


class ReviewDecisionRequest(BaseModel):
    scores: dict[str, int]
    notes: str
    decision: str = Field(pattern="^(pass|fail|escalate)$")


class AppealCreateRequest(BaseModel):
    submission_id: str
    reason: str


class AssessmentPublishRequest(BaseModel):
    activate: bool = True


class HealthResponse(BaseModel):
    status: str
    environment: str
