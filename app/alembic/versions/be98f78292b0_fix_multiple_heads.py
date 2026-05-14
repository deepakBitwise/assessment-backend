"""fix multiple heads

Revision ID: be98f78292b0
Revises: 91f5f0953431, a5b8c9d0e1f2
Create Date: 2026-05-14 13:29:38.687985

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'be98f78292b0'
down_revision = ('91f5f0953431', 'a5b8c9d0e1f2')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
