"""create applications table

Revision ID: 23fc72b0257e
Revises: 2ff2ca09380f
Create Date: 2026-11-02 10:29:14.673196

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '23fc72b0257e'
down_revision: Union[str, Sequence[str], None] = '2ff2ca09380f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('applications',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('company', sa.String(length=255), nullable=False),
    sa.Column('job_title', sa.String(length=255), nullable=False),
    sa.Column('status', sa.String(length=50), server_default='pending', nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_applications_user_id'), 'applications', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_applications_user_id'), table_name='applications')
    op.drop_table('applications')
