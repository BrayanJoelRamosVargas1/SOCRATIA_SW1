"""p3c voice utterance fields

Revision ID: 20260905_0012
Revises: 20260904_0011
Create Date: 2026-09-05 13:59:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260905_0012"
down_revision = "20260904_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "voice_utterances",
        sa.Column("stt_fallback_used", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column("voice_utterances", sa.Column("raw_transcript", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("voice_utterances", "raw_transcript")
    op.drop_column("voice_utterances", "stt_fallback_used")
