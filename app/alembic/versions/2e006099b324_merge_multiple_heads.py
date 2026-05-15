"""merge multiple heads

Revision ID: 2e006099b324
Revises: be98f78292b0, f3e4d9f8c2a1
Create Date: 2026-05-15 09:46:45.132477

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '2e006099b324'
down_revision = ('be98f78292b0', 'f3e4d9f8c2a1')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
