"""phase 4 engagement inbox

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "social_interactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "social_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("social_accounts.id", ondelete="SET NULL"),
        ),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("interaction_type", sa.String(32), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("author_name", sa.String(255)),
        sa.Column("author_handle", sa.String(255)),
        sa.Column("author_external_id", sa.String(255)),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("permalink", sa.String(1000)),
        sa.Column("sentiment", sa.String(32), nullable=False, server_default="neutral"),
        sa.Column("intent", sa.String(64), nullable=False, server_default="other"),
        sa.Column("priority", sa.String(32), nullable=False, server_default="medium"),
        sa.Column("lead_probability", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="new"),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True)),
        sa.Column("content_item_id", postgresql.UUID(as_uuid=True)),
        sa.Column("scheduled_post_id", postgresql.UUID(as_uuid=True)),
        sa.Column("parent_external_id", sa.String(255)),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True)),
        sa.Column("metadata_json", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "platform", "external_id", name="uq_interaction_external"),
    )
    op.create_index("ix_social_interactions_organization_id", "social_interactions", ["organization_id"])
    op.create_index("ix_social_interactions_brand_id", "social_interactions", ["brand_id"])
    op.create_index("ix_social_interactions_status", "social_interactions", ["status"])
    op.create_index("ix_social_interactions_received_at", "social_interactions", ["received_at"])

    op.create_table(
        "ai_reply_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "interaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("social_interactions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("tone", sa.String(64)),
        sa.Column("provider", sa.String(64), nullable=False, server_default="local"),
        sa.Column("status", sa.String(32), nullable=False, server_default="suggested"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True)),
        sa.Column("external_reply_id", sa.String(255)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_ai_reply_drafts_organization_id", "ai_reply_drafts", ["organization_id"])
    op.create_index("ix_ai_reply_drafts_interaction_id", "ai_reply_drafts", ["interaction_id"])


def downgrade() -> None:
    op.drop_table("ai_reply_drafts")
    op.drop_table("social_interactions")
