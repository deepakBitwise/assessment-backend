import uuid
from datetime import datetime, timezone
from enum import Enum 

from pydantic import EmailStr
from sqlalchemy import Column, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, Enum):
    LEARNER = "LEARNER"
    REVIEWER = "REVIEWER"
    ADMIN = "ADMIN"


class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)
    role: UserRole = UserRole.LEARNER


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )

    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)
    sessions: list["UserSession"] = Relationship(
        back_populates="user",
        cascade_delete=True,
    )


class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


class ItemCreate(ItemBase):
    pass


class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)


class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )

    owner_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        ondelete="CASCADE",
    )

    owner: User | None = Relationship(back_populates="items")


class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


class Message(SQLModel):
    message: str


class Token(SQLModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(SQLModel):
    sub: str | None = None


class RefreshTokenPayload(SQLModel):
    sub: str | None = None
    session_id: str | None = None


class UserSessionBase(SQLModel):
    device_name: str | None = Field(default=None, max_length=255)
    device_type: str | None = Field(default=None, max_length=50)
    ip_address: str | None = Field(default=None, max_length=45)


class UserSession(UserSessionBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    user_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        ondelete="CASCADE",
    )

    user: User = Relationship(back_populates="sessions")

    refresh_token_hash: str
    is_active: bool = True

    last_accessed: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )

    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )

    expires_at: datetime = Field(
        sa_type=DateTime(timezone=True),
    )


class UserSessionPublic(UserSessionBase):
    id: uuid.UUID
    is_active: bool
    last_accessed: datetime
    created_at: datetime
    expires_at: datetime


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class SubmissionStatus(str, Enum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    REJECTED = "REJECTED"


DEFAULT_ASSESSMENT_ID = "assessment-1"
DEFAULT_SUBMISSION_ID = "submission-1"


class AssessmentBase(SQLModel):
    problem_statement: str = Field(min_length=1)
    deliverables: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, default=list),
    )
    attachment_object_name: str | None = Field(default=None, max_length=512)


class Assessment(SQLModel, table=True):
    id: str = Field(default=DEFAULT_ASSESSMENT_ID, primary_key=True, max_length=255)
    problem_statement: str = Field(min_length=1)
    deliverables: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, default=list),
    )
    attachment_object_name: str | None = Field(default=None, max_length=512)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class AssessmentCreate(AssessmentBase):
    pass


class AssessmentUpdate(SQLModel):
    problem_statement: str = Field(min_length=1)
    deliverables: list[str] = Field(default_factory=list)


class AssessmentAttachmentUpdate(SQLModel):
    attachment_object_name: str = Field(min_length=1, max_length=512)


class AssessmentPublic(AssessmentBase):
    id: str
    created_at: datetime
    updated_at: datetime


class AssessmentsPublic(SQLModel):
    data: list[AssessmentPublic]
    count: int


class SubmissionBase(SQLModel):
    assessment_id: str = Field(
        foreign_key="assessment.id", nullable=False, index=True, max_length=255
    )
    automated_check: SubmissionStatus = Field(
        default=SubmissionStatus.PENDING,
        sa_type=SAEnum(SubmissionStatus, name="submissionstatus"),
    )
    llm_judge: SubmissionStatus = Field(
        default=SubmissionStatus.PENDING,
        sa_type=SAEnum(SubmissionStatus, name="submissionstatus"),
    )
    human_reviewer: SubmissionStatus = Field(
        default=SubmissionStatus.PENDING,
        sa_type=SAEnum(SubmissionStatus, name="submissionstatus"),
    )


class Submission(SubmissionBase, table=True):
    id: str = Field(default=DEFAULT_SUBMISSION_ID, primary_key=True, max_length=255)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class SubmissionCreate(SQLModel):
    assessment_id: str = Field(min_length=1, max_length=255)


class SubmissionStatusUpdate(SQLModel):
    automated_check: SubmissionStatus | None = None
    llm_judge: SubmissionStatus | None = None
    human_reviewer: SubmissionStatus | None = None


class SubmissionPublic(SubmissionBase):
    id: str
    created_at: datetime
    updated_at: datetime


class SubmissionTriggerResponse(SQLModel):
    submission_id: str
    assessment_id: str
    status_code: int
    response: dict | list | str | None = None

