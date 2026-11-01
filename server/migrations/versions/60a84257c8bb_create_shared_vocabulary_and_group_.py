"""Create shared vocabulary and group associations"""

import sqlalchemy as sa
from alembic import op

revision = "60a84257c8bb"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vocabulary_groups",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("slug", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "words",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("term", sa.String(length=100), nullable=False),
        sa.Column("phonetic", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("term"),
    )
    op.create_table(
        "word_groups",
        sa.Column("word_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"], ["vocabulary_groups.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["word_id"], ["words.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("word_id", "group_id"),
    )
    op.create_index(
        op.f("ix_word_groups_group_id"), "word_groups", ["group_id"], unique=False
    )
    op.create_table(
        "word_meanings",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("word_id", sa.BigInteger(), nullable=False),
        sa.Column("part_of_speech", sa.String(length=40), nullable=False),
        sa.Column("meaning", sa.Text(), nullable=False),
        sa.Column("meaning_hash", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["word_id"], ["words.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "word_id", "part_of_speech", "meaning_hash", name="uq_word_meaning"
        ),
    )
    op.create_index(
        op.f("ix_word_meanings_word_id"), "word_meanings", ["word_id"], unique=False
    )
    groups = sa.table(
        "vocabulary_groups", sa.column("slug", sa.String), sa.column("name", sa.String)
    )
    op.bulk_insert(
        groups,
        [
            {"slug": "junior", "name": "Junior"},
            {"slug": "senior", "name": "Senior"},
            {"slug": "cet4", "name": "CET-4"},
            {"slug": "cet6", "name": "CET-6"},
            {"slug": "postgraduate", "name": "Postgraduate"},
            {"slug": "ielts", "name": "IELTS"},
        ],
    )


def downgrade():
    op.drop_index(op.f("ix_word_meanings_word_id"), table_name="word_meanings")
    op.drop_table("word_meanings")
    op.drop_index(op.f("ix_word_groups_group_id"), table_name="word_groups")
    op.drop_table("word_groups")
    op.drop_table("words")
    op.drop_table("vocabulary_groups")
