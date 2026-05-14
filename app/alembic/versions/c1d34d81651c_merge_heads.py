"""merge heads

Revision ID: c1d34d81651c
Revises: 91f5f0953431, a5b8c9d0e1f2
Create Date: 2026-05-14 12:18:52.918463

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'c1d34d81651c'
down_revision = ('91f5f0953431', 'a5b8c9d0e1f2')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
