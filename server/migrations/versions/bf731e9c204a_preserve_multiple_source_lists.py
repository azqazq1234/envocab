"""Preserve every source occurrence for words in multiple Senior lists."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "bf731e9c204a"
down_revision = "a917dd2830cf"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("word_groups", sa.Column("source_entries", JSONB(), nullable=True))
    op.execute("""
        UPDATE word_groups
        SET source_entries = jsonb_build_array(jsonb_build_object(
            'list_code', list_code, 'position', position, 'source_term', source_term
        ))
        WHERE list_code IS NOT NULL
    """)


def downgrade():
    op.drop_column("word_groups", "source_entries")
