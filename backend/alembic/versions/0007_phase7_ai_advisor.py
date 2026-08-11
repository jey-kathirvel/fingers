"""phase 7 ai advisor recommendations

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE")),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text()),
        sa.Column("priority", sa.String(32), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("evidence_json", sa.Text()),
        sa.Column("provider", sa.String(64), nullable=False, server_default="rules"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_ai_recommendations_organization_id", "ai_recommendations", ["organization_id"])
    op.create_index("ix_ai_recommendations_brand_id", "ai_recommendations", ["brand_id"])
    op.create_index("ix_ai_recommendations_status", "ai_recommendations", ["status"])


def downgrade() -> None:
    op.drop_table("ai_recommendations")
