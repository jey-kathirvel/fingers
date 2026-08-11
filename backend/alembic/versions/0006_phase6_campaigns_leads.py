"""phase 6 campaigns and leads

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("objective", sa.String(100)),
        sa.Column("platforms", sa.String(255)),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("start_date", sa.DateTime(timezone=True)),
        sa.Column("end_date", sa.DateTime(timezone=True)),
        sa.Column("kpi_targets", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_campaigns_organization_id", "campaigns", ["organization_id"])
    op.create_index("ix_campaigns_brand_id", "campaigns", ["brand_id"])

    op.create_table(
        "campaign_contents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "content_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("campaign_id", "content_item_id", name="uq_campaign_content"),
    )
    op.create_index("ix_campaign_contents_campaign_id", "campaign_contents", ["campaign_id"])
    op.create_index("ix_campaign_contents_content_item_id", "campaign_contents", ["content_item_id"])

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_platform", sa.String(32)),
        sa.Column("social_account_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "interaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("social_interactions.id", ondelete="SET NULL"),
        ),
        sa.Column("content_item_id", postgresql.UUID(as_uuid=True)),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="SET NULL")),
        sa.Column("intent", sa.String(64)),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="new"),
        sa.Column("product_interest", sa.String(255)),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True)),
        sa.Column("follow_up_at", sa.DateTime(timezone=True)),
        sa.Column("source_message", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("status_history", sa.Text()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_leads_organization_id", "leads", ["organization_id"])
    op.create_index("ix_leads_brand_id", "leads", ["brand_id"])
    op.create_index("ix_leads_status", "leads", ["status"])
    op.create_index("ix_leads_interaction_id", "leads", ["interaction_id"])


def downgrade() -> None:
    op.drop_table("leads")
    op.drop_table("campaign_contents")
    op.drop_table("campaigns")
