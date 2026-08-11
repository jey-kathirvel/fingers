"""phase 8 automation rules, runs, listening terms and mentions

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "automation_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("trigger_type", sa.String(64), nullable=False),
        sa.Column("trigger_config_json", sa.Text()),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("action_config_json", sa.Text()),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_automation_rules_organization_id", "automation_rules", ["organization_id"])
    op.create_index("ix_automation_rules_brand_id", "automation_rules", ["brand_id"])
    op.create_index("ix_automation_rules_enabled", "automation_rules", ["enabled"])

    op.create_table(
        "automation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "rule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("automation_rules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="success"),
        sa.Column("trigger_entity_type", sa.String(64)),
        sa.Column("trigger_entity_id", sa.String(100)),
        sa.Column("result_json", sa.Text()),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_automation_runs_organization_id", "automation_runs", ["organization_id"])
    op.create_index("ix_automation_runs_rule_id", "automation_runs", ["rule_id"])

    op.create_table(
        "listening_terms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "brand_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("brands.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("term", sa.String(255), nullable=False),
        sa.Column("term_type", sa.String(32), nullable=False, server_default="custom"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "brand_id", "term", name="uq_listening_term"),
    )
    op.create_index("ix_listening_terms_organization_id", "listening_terms", ["organization_id"])
    op.create_index("ix_listening_terms_brand_id", "listening_terms", ["brand_id"])

    op.create_table(
        "social_mentions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "brand_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("brands.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "term_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("listening_terms.id", ondelete="SET NULL"),
        ),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("author_name", sa.String(255)),
        sa.Column("author_handle", sa.String(255)),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("permalink", sa.String(1000)),
        sa.Column("sentiment", sa.String(32), nullable=False, server_default="neutral"),
        sa.Column("share_weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("source", sa.String(32), nullable=False, server_default="simulation"),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("mentioned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "platform", "external_id", name="uq_mention_external"),
    )
    op.create_index("ix_social_mentions_organization_id", "social_mentions", ["organization_id"])
    op.create_index("ix_social_mentions_brand_id", "social_mentions", ["brand_id"])
    op.create_index("ix_social_mentions_term_id", "social_mentions", ["term_id"])
    op.create_index("ix_social_mentions_mentioned_at", "social_mentions", ["mentioned_at"])


def downgrade() -> None:
    op.drop_table("social_mentions")
    op.drop_table("listening_terms")
    op.drop_table("automation_runs")
    op.drop_table("automation_rules")
