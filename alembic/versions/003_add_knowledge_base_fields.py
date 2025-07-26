"""add knowledge base record fields

Revision ID: 003
Revises: 002
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # 添加知识库记录相关字段
    op.add_column('contents', sa.Column('knowledge_title', sa.String(500), nullable=True))
    op.add_column('contents', sa.Column('knowledge_date', sa.String(20), nullable=True))
    op.add_column('contents', sa.Column('knowledge_preview', sa.Text, nullable=True))


def downgrade():
    # 删除知识库记录相关字段
    op.drop_column('contents', 'knowledge_preview')
    op.drop_column('contents', 'knowledge_date')
    op.drop_column('contents', 'knowledge_title')