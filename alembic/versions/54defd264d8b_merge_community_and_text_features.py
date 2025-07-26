"""merge_community_and_text_features

Revision ID: 54defd264d8b
Revises: 001_community, 004
Create Date: 2025-07-26 23:56:00.877038

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '54defd264d8b'
down_revision = ('001_community', '004')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
