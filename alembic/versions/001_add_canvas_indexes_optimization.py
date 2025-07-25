"""add canvas indexes optimization

Revision ID: 001
Revises: 
Create Date: 2025-01-26 14:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """添加索引优化查询性能"""
    
    # 为cards表添加索引
    op.create_index('idx_cards_canvas_id', 'cards', ['canvas_id'])
    op.create_index('idx_cards_content_id', 'cards', ['content_id'])
    
    # 为user_contents表添加索引
    op.create_index('idx_user_contents_user_id', 'user_contents', ['user_id'])
    op.create_index('idx_user_contents_content_id', 'user_contents', ['content_id'])
    
    # 为canvases表添加索引
    op.create_index('idx_canvases_owner_id', 'canvases', ['owner_id'])
    
    # 为contents表添加索引（按类型查询优化）
    op.create_index('idx_contents_content_type', 'contents', ['content_type'])
    
    # 复合索引优化常见查询
    op.create_index('idx_user_contents_user_content', 'user_contents', ['user_id', 'content_id'])
    op.create_index('idx_cards_canvas_position', 'cards', ['canvas_id', 'position_x', 'position_y'])


def downgrade() -> None:
    """移除索引"""
    
    # 移除复合索引
    op.drop_index('idx_cards_canvas_position', table_name='cards')
    op.drop_index('idx_user_contents_user_content', table_name='user_contents')
    
    # 移除单列索引
    op.drop_index('idx_contents_content_type', table_name='contents')
    op.drop_index('idx_canvases_owner_id', table_name='canvases')
    op.drop_index('idx_user_contents_content_id', table_name='user_contents')
    op.drop_index('idx_user_contents_user_id', table_name='user_contents')
    op.drop_index('idx_cards_content_id', table_name='cards')
    op.drop_index('idx_cards_canvas_id', table_name='cards')