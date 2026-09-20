"""add original_file to resumes

Revision ID: a1b2c3d4e5f6
Revises: dc6497afbb97
Create Date: 2026-09-20 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'dc6497afbb97'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add original_file BYTEA column for storing original DOCX bytes."""
    op.add_column('resumes', sa.Column('original_file', sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    """Remove original_file column."""
    op.drop_column('resumes', 'original_file')
