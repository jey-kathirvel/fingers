"""phase 3 publishing

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "social_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("account_name", sa.String(255), nullable=False),
        sa.Column("external_account_id", sa.String(255)),
        sa.Column("status", sa.String(32), nullable=False, server_default="connected"),
        sa.Column("connection_mode", sa.String(32), nullable=False, server_default="simulation"),
        sa.Column("access_token", sa.Text()),
        sa.Column("refresh_token", sa.Text()),
        sa.Column("token_expires_at", sa.DateTime(timezone=True)),
        sa.Column("metadata_json", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_social_accounts_organization_id", "social_accounts", ["organization_id"])
    op.create_index("ix_social_accounts_brand_id", "social_accounts", ["brand_id"])

    op.create_table(
        "scheduled_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("social_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("social_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="scheduled"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("last_error", sa.Text()),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("external_post_id", sa.String(255)),
        sa.Column("created_by", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("idempotency_key", name="uq_scheduled_posts_idempotency_key"),
    )
    op.create_index("ix_scheduled_posts_organization_id", "scheduled_posts", ["organization_id"])
    op.create_index("ix_scheduled_posts_brand_id", "scheduled_posts", ["brand_id"])
    op.create_index("ix_scheduled_posts_content_item_id", "scheduled_posts", ["content_item_id"])
    op.create_index("ix_scheduled_posts_scheduled_for", "scheduled_posts", ["scheduled_for"])

    op.create_table(
        "publishing_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduled_post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scheduled_posts.id", ondelete="SET NULL")),
        sa.Column("content_item_id", postgresql.UUID(as_uuid=True)),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("message", sa.Text()),
        sa.Column("external_post_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_publishing_logs_organization_id", "publishing_logs", ["organization_id"])
    op.create_index("ix_publishing_logs_scheduled_post_id", "publishing_logs", ["scheduled_post_id"])


def downgrade() -> None:
    op.drop_table("publishing_logs")
    op.drop_table("scheduled_posts")
    op.drop_table("social_accounts")
