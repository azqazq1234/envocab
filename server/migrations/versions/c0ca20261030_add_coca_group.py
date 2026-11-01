"""Add the COCA vocabulary group without changing other groups."""

from alembic import op

revision = "c0ca20261030"
down_revision = "bf731e9c204a"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("INSERT INTO vocabulary_groups (slug, name) VALUES ('coca', 'COCA') ON CONFLICT (slug) DO NOTHING")


def downgrade():
    # Keep populated groups intact; source imports are separate from schema setup.
    op.execute("DELETE FROM vocabulary_groups WHERE slug = 'coca' AND NOT EXISTS "
               "(SELECT 1 FROM word_groups WHERE group_id = vocabulary_groups.id)")
