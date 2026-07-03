"""Initial schema — Section 6 tables (sources, raw_items, events,
extracted_facts, stories, story_members, instability_scores).

Assumes scripts/db_bootstrap.sql has already been run against the target
database (CREATE EXTENSION postgis; CREATE EXTENSION vector;).

Revision ID: 0001
Revises:
Create Date: 2026-07-03
"""
import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

try:
    from pgvector.sqlalchemy import Vector

    def embedding_type():
        return Vector(384)

except ImportError:

    def embedding_type():
        return ARRAY(sa.Float)


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("leaning", sa.Text, nullable=True),
        sa.Column("poll_interval_seconds", sa.Integer, nullable=False),
        sa.Column("health_status", sa.Text, nullable=False, server_default="ok"),
        sa.Column("last_fetched_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text, nullable=True),
    )

    op.create_table(
        "raw_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", UUID(as_uuid=True), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("raw_content", JSONB, nullable=False),
        sa.Column("fetched_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("processed", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("processing_error", sa.Text, nullable=True),
    )
    op.create_index("ix_raw_items_source_id", "raw_items", ["source_id"])
    op.create_index("ix_raw_items_processed", "raw_items", ["processed"])

    op.create_table(
        "events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("raw_item_id", UUID(as_uuid=True), sa.ForeignKey("raw_items.id"), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("location", Geography(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("location_name", sa.Text, nullable=True),
        sa.Column("category", sa.Text, nullable=False),
        sa.Column("severity", sa.Integer, nullable=False),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("embedding", embedding_type(), nullable=True),
    )
    op.create_index("ix_events_raw_item_id", "events", ["raw_item_id"])
    op.create_index("ix_events_occurred_at", "events", ["occurred_at"])
    op.create_index("ix_events_category", "events", ["category"])

    op.create_table(
        "extracted_facts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=True),
        sa.Column("source_id", UUID(as_uuid=True), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("who", sa.Text, nullable=False),
        sa.Column("what", sa.Text, nullable=False),
        sa.Column("where", sa.Text, nullable=True),
        sa.Column("when_occurred", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("embedding", embedding_type(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_index("ix_extracted_facts_event_id", "extracted_facts", ["event_id"])
    op.create_index("ix_extracted_facts_source_id", "extracted_facts", ["source_id"])
    op.create_index("ix_extracted_facts_when_occurred", "extracted_facts", ["when_occurred"])

    op.create_table(
        "stories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("headline", sa.Text, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("causal_narrative", JSONB, nullable=True),
        sa.Column("confidence", sa.Text, nullable=True),
        sa.Column("first_seen_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_table(
        "story_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("story_id", UUID(as_uuid=True), sa.ForeignKey("stories.id"), nullable=False),
        sa.Column("event_id", UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=True),
        sa.Column("fact_id", UUID(as_uuid=True), sa.ForeignKey("extracted_facts.id"), nullable=True),
        sa.Column("linked_via", sa.Text, nullable=False),
        sa.Column("linked_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.UniqueConstraint("story_id", "event_id", "fact_id", "linked_via", name="uq_story_member"),
    )
    op.create_index("ix_story_members_story_id", "story_members", ["story_id"])

    op.create_table(
        "instability_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("computed_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("component_breakdown", JSONB, nullable=True),
    )
    op.create_index("ix_instability_scores_computed_at", "instability_scores", ["computed_at"])


def downgrade() -> None:
    op.drop_table("instability_scores")
    op.drop_table("story_members")
    op.drop_table("stories")
    op.drop_table("extracted_facts")
    op.drop_table("events")
    op.drop_table("raw_items")
    op.drop_table("sources")
