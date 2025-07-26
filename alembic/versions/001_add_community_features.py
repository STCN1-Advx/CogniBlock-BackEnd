"""Add community features

Revision ID: 001_community
Revises: 
Create Date: 2024-01-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_community'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tags table
    op.create_table('tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tags_id'), 'tags', ['id'], unique=False)
    op.create_index(op.f('ix_tags_name'), 'tags', ['name'], unique=True)

    # Create content_tags table
    op.create_table('content_tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['content_id'], ['contents.id'], ),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('content_id', 'tag_id', name='uq_content_tag')
    )
    op.create_index(op.f('ix_content_tags_id'), 'content_tags', ['id'], unique=False)

    # Add community-related columns to contents table
    op.add_column('contents', sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('contents', sa.Column('public_title', sa.String(length=255), nullable=True))
    op.add_column('contents', sa.Column('public_description', sa.Text(), nullable=True))
    op.add_column('contents', sa.Column('published_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove columns from contents table
    op.drop_column('contents', 'published_at')
    op.drop_column('contents', 'public_description')
    op.drop_column('contents', 'public_title')
    op.drop_column('contents', 'is_public')

    # Drop content_tags table
    op.drop_index(op.f('ix_content_tags_id'), table_name='content_tags')
    op.drop_table('content_tags')

    # Drop tags table
    op.drop_index(op.f('ix_tags_name'), table_name='tags')
    op.drop_index(op.f('ix_tags_id'), table_name='tags')
    op.drop_table('tags')
