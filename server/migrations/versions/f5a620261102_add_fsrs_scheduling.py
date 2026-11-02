"""Store FSRS state and review history without fabricating historical answers."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f5a620261102"
down_revision = "d12a20261102"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("learning_progress", sa.Column("fsrs_card", postgresql.JSONB(), nullable=True))
    op.add_column("learning_progress", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_learning_progress_user_due", "learning_progress", ["user_id", "due_at"])
    op.create_table(
        "word_reviews",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("word_id", sa.BigInteger(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("card_before", postgresql.JSONB(), nullable=False),
        sa.Column("card_after", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id", "word_id"],
            ["learning_progress.user_id", "learning_progress.word_id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("rating BETWEEN 1 AND 4", name="ck_word_review_rating"),
    )
    op.create_index("ix_word_reviews_user_word", "word_reviews", ["user_id", "word_id"])


def downgrade():
    op.drop_table("word_reviews")
    op.drop_index("ix_learning_progress_user_due", table_name="learning_progress")
    op.drop_column("learning_progress", "due_at")
    op.drop_column("learning_progress", "fsrs_card")
