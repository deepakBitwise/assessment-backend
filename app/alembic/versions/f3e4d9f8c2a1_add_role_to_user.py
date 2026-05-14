"""Add role to User model

Revision ID: f3e4d9f8c2a1
Revises: c1d34d81651c
Create Date: 2026-05-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.types import Enum


# revision identifiers, used by Alembic.
revision = 'f3e4d9f8c2a1'
down_revision = 'c1d34d81651c'
branch_labels = None
depends_on = None


def upgrade():
    # Create ENUM type for role
    op.execute("""
    CREATE TYPE userrole AS ENUM ('LEARNER', 'REVIEWER', 'ADMIN')
    """)
    # Add role column
    op.add_column('user', sa.Column('role', sa.Enum(name='userrole'), nullable=False, server_default='LEARNER'))


def downgrade():
    # Remove role column
    op.drop_column('user', 'role')
    # Drop ENUM type
    op.execute("DROP TYPE userrole")
