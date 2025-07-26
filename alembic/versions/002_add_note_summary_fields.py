"""add note summary fields to content table

Revision ID: 002
Revises: 001
Create Date: 2025-01-26 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """添加笔记总结相关字段到contents表"""
    
    # 添加总结相关字段
    op.add_column('contents', sa.Column('summary_title', sa.String(500), nullable=True))
    op.add_column('contents', sa.Column('summary_topic', sa.String(200), nullable=True))
    op.add_column('contents', sa.Column('summary_content', sa.Text(), nullable=True))
    op.add_column('contents', sa.Column('content_hash', sa.String(64), nullable=True))
    
    # 为content_hash字段添加索引，用于缓存查询优化
    op.create_index('idx_contents_content_hash', 'contents', ['content_hash'])


def downgrade() -> None:
    """移除笔记总结相关字段"""
    
    # 移除索引
    op.drop_index('idx_contents_content_hash', table_name='contents')
    
    # 移除字段
    op.drop_column('contents', 'content_hash')
    op.drop_column('contents', 'summary_content')
    op.drop_column('contents', 'summary_topic')
    op.drop_column('contents', 'summary_title')