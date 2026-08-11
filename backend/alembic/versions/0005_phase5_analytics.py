"""phase 5 analytics metrics

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "account_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "social_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("social_accounts.id", ondelete="SET NULL"),
        ),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("metric_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("followers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reach", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("profile_visits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("website_clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("likes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("shares", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("saves", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("video_views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leads", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "organization_id",
            "brand_id",
            "platform",
            "social_account_id",
            "metric_date",
            name="uq_account_metric_day",
        ),
    )
    op.create_index("ix_account_metrics_organization_id", "account_metrics", ["organization_id"])
    op.create_index("ix_account_metrics_brand_id", "account_metrics", ["brand_id"])
    op.create_index("ix_account_metrics_metric_date", "account_metrics", ["metric_date"])

    op.create_table(
        "post_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "content_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_items.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "scheduled_post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scheduled_posts.id", ondelete="SET NULL"),
        ),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reach", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("likes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("shares", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("saves", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("video_views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("engagement_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "scheduled_post_id", name="uq_post_metric_scheduled"),
    )
    op.create_index("ix_post_metrics_organization_id", "post_metrics", ["organization_id"])
    op.create_index("ix_post_metrics_brand_id", "post_metrics", ["brand_id"])
    op.create_index("ix_post_metrics_measured_at", "post_metrics", ["measured_at"])


def downgrade() -> None:
    op.drop_table("post_metrics")
    op.drop_table("account_metrics")
