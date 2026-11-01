"""Preserve source lists and ordering on vocabulary memberships."""

import sqlalchemy as sa
from alembic import op

revision = "a917dd2830cf"
down_revision = "60a84257c8bb"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("word_groups", sa.Column("list_code", sa.String(30), nullable=True))
    op.add_column("word_groups", sa.Column("position", sa.Integer(), nullable=True))
    op.add_column("word_groups", sa.Column("source_term", sa.String(200), nullable=True))


def downgrade():
    op.drop_column("word_groups", "source_term")
    op.drop_column("word_groups", "position")
    op.drop_column("word_groups", "list_code")
