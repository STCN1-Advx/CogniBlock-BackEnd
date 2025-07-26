"""add text mode and missing fields

Revision ID: 004
Revises: 003
Create Date: 2024-12-19 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # 添加缺失的字段
    op.add_column('contents', sa.Column('filename', sa.String(255), nullable=True))
    op.add_column('contents', sa.Column('summary_title', sa.String(255), nullable=True))
    op.add_column('contents', sa.Column('original_text', sa.Text, nullable=True))


def downgrade():
    # 删除添加的字段
    op.drop_column('contents', 'original_text')
    op.drop_column('contents', 'summary_title')
    op.drop_column('contents', 'filename')