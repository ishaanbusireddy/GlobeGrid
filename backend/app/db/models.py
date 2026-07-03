"""SQLAlchemy models matching the Section 6 schema exactly (all field names,
types, and nullability as specified in the build manual).

Embedding columns use pgvector's Vector(384) when the pgvector package is
importable; otherwise they fall back to a plain float array, per the
Section 3.2 install-note fallback (pgvector preferred, Python-side cosine
similarity fallback if the extension isn't available).
"""
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.types import ARRAY, Float

from geoalchemy2 import Geography

try:
    from pgvector.sqlalchemy import Vector

    def embedding_column():
        return Column(Vector(384), nullable=True)

except ImportError:  # pragma: no cover - exercised only when pgvector absent

    def embedding_column():
        return Column(ARRAY(Float), nullable=True)


Base = declarative_base()


def _uuid_pk():
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Source(Base):
    """Section 6.1 sources"""

    __tablename__ = "sources"

    id = _uuid_pk()
    name = Column(Text, nullable=False)
    type = Column(Text, nullable=False)  # rss | gdelt | usgs | market | reddit
    url = Column(Text, nullable=False)
    leaning = Column(Text, nullable=True)  # left | center | right | n/a
    poll_interval_seconds = Column(Integer, nullable=False)
    health_status = Column(Text, nullable=False, default="ok")  # ok | degraded | down
    last_fetched_at = Column(TIMESTAMP(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

    raw_items = relationship("RawItem", back_populates="source")
    extracted_facts = relationship("ExtractedFact", back_populates="source")


class RawItem(Base):
    """Section 6.2 raw_items"""

    __tablename__ = "raw_items"

    id = _uuid_pk()
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    raw_content = Column(JSONB, nullable=False)
    fetched_at = Column(TIMESTAMP(timezone=True), nullable=False)
    processed = Column(Boolean, nullable=False, default=False)
    processing_error = Column(Text, nullable=True)

    source = relationship("Source", back_populates="raw_items")
    events = relationship("Event", back_populates="raw_item")


class Event(Base):
    """Section 6.3 events"""

    __tablename__ = "events"

    id = _uuid_pk()
    raw_item_id = Column(UUID(as_uuid=True), ForeignKey("raw_items.id"), nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    location = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    location_name = Column(Text, nullable=True)
    category = Column(Text, nullable=False)  # geopolitics | finance | disaster | conflict | other
    severity = Column(Integer, nullable=False)  # 1-5
    occurred_at = Column(TIMESTAMP(timezone=True), nullable=False)
    embedding = embedding_column()

    raw_item = relationship("RawItem", back_populates="events")
    extracted_facts = relationship("ExtractedFact", back_populates="event")


class ExtractedFact(Base):
    """Section 6.4 extracted_facts — the permanent fact chain (Section 5.9).
    Rows in this table are never deleted or expired."""

    __tablename__ = "extracted_facts"

    id = _uuid_pk()
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    who = Column(Text, nullable=False)
    what = Column(Text, nullable=False)
    where = Column(Text, nullable=True)
    when_occurred = Column(TIMESTAMP(timezone=True), nullable=False)
    embedding = embedding_column()
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)

    event = relationship("Event", back_populates="extracted_facts")
    source = relationship("Source", back_populates="extracted_facts")


class Story(Base):
    """Section 6.5 stories (written starting Phase 2; table exists from Phase 1 schema)"""

    __tablename__ = "stories"

    id = _uuid_pk()
    headline = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    causal_narrative = Column(JSONB, nullable=True)
    confidence = Column(Text, nullable=True)  # high | medium | low
    first_seen_at = Column(TIMESTAMP(timezone=True), nullable=True)
    last_updated_at = Column(TIMESTAMP(timezone=True), nullable=True)


class StoryMember(Base):
    """Section 6.6 story_members (written starting Phase 2).

    The manual lists no id column for this join table; a surrogate uuid PK
    is added here as a pragmatic ORM/Postgres requirement (event_id and
    fact_id are individually nullable, so neither can anchor a composite
    key) — every other field matches Section 6.6 exactly.
    """

    __tablename__ = "story_members"

    id = _uuid_pk()
    story_id = Column(UUID(as_uuid=True), ForeignKey("stories.id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=True)
    fact_id = Column(UUID(as_uuid=True), ForeignKey("extracted_facts.id"), nullable=True)
    linked_via = Column(Text, nullable=False)  # same_window | historical_chain
    linked_at = Column(TIMESTAMP(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("story_id", "event_id", "fact_id", "linked_via", name="uq_story_member"),
    )


class InstabilityScore(Base):
    """Section 6.7 instability_scores (written starting Phase 6)"""

    __tablename__ = "instability_scores"

    id = _uuid_pk()
    score = Column(Numeric(5, 2), nullable=False)
    computed_at = Column(TIMESTAMP(timezone=True), nullable=False)
    component_breakdown = Column(JSONB, nullable=True)
