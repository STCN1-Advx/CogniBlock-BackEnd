"""Add OCR fields to content table

Revision ID: 003_add_ocr_fields
Revises: 002
Create Date: 2024-12-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_add_ocr_fields'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Add OCR related fields
    op.add_column('contents', sa.Column('ocr_result', sa.Text(), nullable=True))
    op.add_column('contents', sa.Column('ocr_status', sa.String(length=20), nullable=True))
    op.add_column('contents', sa.Column('summary_status', sa.String(length=20), nullable=True))
    op.add_column('contents', sa.Column('filename', sa.String(length=255), nullable=True))
    op.add_column('contents', sa.Column('file_size', sa.Integer(), nullable=True))


def downgrade():
    # Remove OCR related fields
    op.drop_column('contents', 'file_size')
    op.drop_column('contents', 'filename')
    op.drop_column('contents', 'summary_status')
    op.drop_column('contents', 'ocr_status')
    op.drop_column('contents', 'ocr_result')