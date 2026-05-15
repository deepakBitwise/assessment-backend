"""fix multiple heads

Revision ID: 5c17998686ed
Revises: be98f78292b0, f3e4d9f8c2a1
Create Date: 2026-05-14 18:27:02.991066

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '5c17998686ed'
down_revision = ('be98f78292b0', 'f3e4d9f8c2a1')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
