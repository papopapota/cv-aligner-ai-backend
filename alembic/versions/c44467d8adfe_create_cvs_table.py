"""create cvs table

Revision ID: c44467d8adfe
Revises: 23fc72b0257e
Create Date: 2026-11-10 20:31:25.641164

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c44467d8adfe'
down_revision: Union[str, Sequence[str], None] = '23fc72b0257e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'cvs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('s3_key', sa.String(length=512), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column(
            'status',
            sa.String(length=20),
            server_default='UPLOADED',
            nullable=False,
        ),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('structured_json', sa.JSON(), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_cvs_user_id'), 'cvs', ['user_id'], unique=False
    )
    op.create_index(
        op.f('ix_cvs_s3_key'), 'cvs', ['s3_key'], unique=True
    )
    op.create_index(
        op.f('ix_cvs_status'), 'cvs', ['status'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_cvs_status'), table_name='cvs')
    op.drop_index(op.f('ix_cvs_s3_key'), table_name='cvs')
    op.drop_index(op.f('ix_cvs_user_id'), table_name='cvs')
    op.drop_table('cvs')
