"""Add username to user

Revision ID: 8c7e75bd3a10
Revises: f3e4d9f8c2a1
Create Date: 2026-05-14 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "8c7e75bd3a10"
down_revision = "f3e4d9f8c2a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("user", sa.Column("username", sa.String(length=64), nullable=True))
    op.execute('UPDATE "user" SET username = email WHERE username IS NULL')
    op.alter_column("user", "username", nullable=False)
    op.create_index(op.f("ix_user_username"), "user", ["username"], unique=True)


def downgrade():
    op.drop_index(op.f("ix_user_username"), table_name="user")
    op.drop_column("user", "username")
