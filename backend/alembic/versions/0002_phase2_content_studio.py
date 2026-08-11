"""phase 2 content studio

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "content_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True)),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("objective", sa.String(100)),
        sa.Column("topic", sa.Text()),
        sa.Column("master_concept", sa.Text()),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_content_items_organization_id", "content_items", ["organization_id"])
    op.create_index("ix_content_items_brand_id", "content_items", ["brand_id"])

    op.create_table(
        "content_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("content_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("format", sa.String(64)),
        sa.Column("headline", sa.String(500)),
        sa.Column("body", sa.Text()),
        sa.Column("hashtags", sa.Text()),
        sa.Column("cta", sa.Text()),
        sa.Column("image_prompt", sa.Text()),
        sa.Column("video_script", sa.Text()),
        sa.Column("score_clarity", sa.Integer()),
        sa.Column("score_brand_fit", sa.Integer()),
        sa.Column("score_cta", sa.Integer()),
        sa.Column("score_platform_fit", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_content_versions_content_item_id", "content_versions", ["content_item_id"])

    op.create_table(
        "content_ideas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("format", sa.String(64)),
        sa.Column("goal", sa.String(100)),
        sa.Column("platforms", sa.String(255)),
        sa.Column("confidence", sa.String(32)),
        sa.Column("rationale", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_content_ideas_organization_id", "content_ideas", ["organization_id"])
    op.create_index("ix_content_ideas_brand_id", "content_ideas", ["brand_id"])

    op.create_table(
        "media_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True)),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("asset_type", sa.String(64), nullable=False, server_default="image"),
        sa.Column("url_or_path", sa.String(1000), nullable=False),
        sa.Column("prompt", sa.Text()),
        sa.Column("tags", sa.Text()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_media_assets_organization_id", "media_assets", ["organization_id"])
    op.create_index("ix_media_assets_brand_id", "media_assets", ["brand_id"])


def downgrade() -> None:
    op.drop_table("media_assets")
    op.drop_table("content_ideas")
    op.drop_table("content_versions")
    op.drop_table("content_items")
