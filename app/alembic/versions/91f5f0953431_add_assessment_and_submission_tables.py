"""add assessment and submission tables

Revision ID: 91f5f0953431
Revises: fe56fa70289e
Create Date: 2026-05-07 16:26:37.267412

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "91f5f0953431"
down_revision = "fe56fa70289e"
branch_labels = None
depends_on = None


submission_status_enum = sa.Enum(
    "PENDING",
    "PASSED",
    "REJECTED",
    name="submissionstatus",
)

submission_status_column_enum = postgresql.ENUM(
    "PENDING",
    "PASSED",
    "REJECTED",
    name="submissionstatus",
    create_type=False,
)


def upgrade():
    submission_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "assessment",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("problem_statement", sa.Text(), nullable=False),
        sa.Column("deliverables", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("attachment_object_name", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "submission",
        sa.Column("assessment_id", sa.String(length=255), nullable=False),
        sa.Column("automated_check", submission_status_column_enum, nullable=False),
        sa.Column("llm_judge", submission_status_column_enum, nullable=False),
        sa.Column("human_reviewer", submission_status_column_enum, nullable=False),
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessment.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_submission_assessment_id"),
        "submission",
        ["assessment_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_submission_assessment_id"), table_name="submission")
    op.drop_table("submission")
    op.drop_table("assessment")
    submission_status_enum.drop(op.get_bind(), checkfirst=True)
