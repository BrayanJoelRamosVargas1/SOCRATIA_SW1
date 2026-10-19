"""Durable single-worker preparation tasks.
Revision ID: 20261018_0013
Revises: 25940ab689a7
"""
from alembic import op
import sqlalchemy as sa
revision="20261018_0013"
down_revision="25940ab689a7"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("preparation_tasks",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("user_id",sa.String(36),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),
        sa.Column("document_id",sa.String(36),sa.ForeignKey("documents.id",ondelete="CASCADE"),nullable=False),
        sa.Column("kind",sa.String(20),nullable=False),sa.Column("status",sa.String(20),nullable=False),
        sa.Column("request_key",sa.String(36),nullable=False),
        sa.Column("duration_minutes",sa.Integer(),nullable=False),sa.Column("regenerate",sa.Integer(),nullable=False),
        sa.Column("error_code",sa.String(80)),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column("started_at",sa.DateTime(timezone=True)),sa.Column("finished_at",sa.DateTime(timezone=True)),
        sa.Column("elapsed_ms",sa.Integer()),
        sa.UniqueConstraint("user_id","request_key",name="uq_preparation_request"))
    for field in ("user_id","document_id","status"):op.create_index("ix_"+field,"preparation_tasks",[field])
    op.create_index("uq_preparation_active_document","preparation_tasks",["document_id"],unique=True,postgresql_where=sa.text("status IN ('QUEUED','RUNNING')"),sqlite_where=sa.text("status IN ('QUEUED','RUNNING')"))

def downgrade():op.drop_table("preparation_tasks")
