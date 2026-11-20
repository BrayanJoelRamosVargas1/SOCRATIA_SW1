"""Opt-in native Android push registrations."""
from alembic import op
import sqlalchemy as sa

revision = "20261120_0016"
down_revision = "20261119_0015"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("native_push_devices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("token", sa.Text(), nullable=False))
    op.create_index("ix_native_push_devices_user_id", "native_push_devices", ["user_id"])


def downgrade():
    op.drop_table("native_push_devices")
