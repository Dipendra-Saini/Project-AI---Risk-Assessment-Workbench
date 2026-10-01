from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from raw.db import Base, EmbeddingType


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(String(256))


class ConfigVersion(Base):
    __tablename__ = "config_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(Integer, unique=True)
    content: Mapped[dict] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))
    note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Control(Base):
    __tablename__ = "controls"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    dims: Mapped[list] = mapped_column(JSON)
    design: Mapped[float] = mapped_column(Float)
    operating: Mapped[float] = mapped_column(Float)
    keywords: Mapped[list] = mapped_column(JSON, default=list)


class ChangeRequest(Base):
    __tablename__ = "change_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    ref: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text)
    change_type: Mapped[str] = mapped_column(String(32))
    business_line: Mapped[str] = mapped_column(String(64))
    launch_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    config_version_id: Mapped[int | None] = mapped_column(ForeignKey("config_versions.id"), nullable=True)
    graph_run: Mapped[int] = mapped_column(Integer, default=0)
    pipeline_state: Mapped[str] = mapped_column(String(16), default="idle")  # idle|running|waiting|failed
    pipeline_step: Mapped[str] = mapped_column(String(64), default="")
    needs_human: Mapped[bool] = mapped_column(Boolean, default=False)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    info_request: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    documents: Mapped[list["Document"]] = relationship(back_populates="cr", order_by="Document.id")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    cr_id: Mapped[int] = mapped_column(ForeignKey("change_requests.id"), index=True)
    filename: Mapped[str] = mapped_column(String(256))
    mime: Mapped[str] = mapped_column(String(128))
    text: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    cr: Mapped[ChangeRequest] = relationship(back_populates="documents")


class Extraction(Base):
    __tablename__ = "extractions"
    id: Mapped[int] = mapped_column(primary_key=True)
    cr_id: Mapped[int] = mapped_column(ForeignKey("change_requests.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    data: Mapped[dict] = mapped_column(JSON)
    flags: Mapped[list] = mapped_column(JSON, default=list)
    provider: Mapped[str] = mapped_column(String(32), default="")
    prompt_version: Mapped[str] = mapped_column(String(32), default="")
    confirmed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Assessment(Base):
    __tablename__ = "assessments"
    id: Mapped[int] = mapped_column(primary_key=True)
    cr_id: Mapped[int] = mapped_column(ForeignKey("change_requests.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    config_version_id: Mapped[int] = mapped_column(ForeignKey("config_versions.id"))
    extraction_id: Mapped[int | None] = mapped_column(ForeignKey("extractions.id"), nullable=True)
    inherent_overall: Mapped[float] = mapped_column(Float, default=0)
    residual_overall: Mapped[float] = mapped_column(Float, default=0)
    inherent_tier: Mapped[str] = mapped_column(String(16), default="")
    residual_tier: Mapped[str] = mapped_column(String(16), default="")
    risk_types: Mapped[list] = mapped_column(JSON, default=list)
    score_trace: Mapped[dict] = mapped_column(JSON, default=dict)
    retrieval: Mapped[dict] = mapped_column(JSON, default=dict)
    narrative: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    narrative_provider: Mapped[str] = mapped_column(String(32), default="")
    narrative_stale: Mapped[bool] = mapped_column(Boolean, default=False)
    critique: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    narrative_signed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    narrative_signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    warnings_ack_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    factors: Mapped[list["FactorRating"]] = relationship(order_by="FactorRating.id")
    controls: Mapped[list["AssessmentControl"]] = relationship(order_by="AssessmentControl.id")


class FactorRating(Base):
    __tablename__ = "factor_ratings"
    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id"), index=True)
    dimension: Mapped[str] = mapped_column(String(8))
    likelihood: Mapped[int] = mapped_column(Integer)
    impact: Mapped[int] = mapped_column(Integer)
    origin: Mapped[str] = mapped_column(String(16))  # rule | ai | offline | human
    rule_ids: Mapped[list] = mapped_column(JSON, default=list)
    risk_types: Mapped[list] = mapped_column(JSON, default=list)
    rationale: Mapped[str] = mapped_column(Text, default="")
    citations: Mapped[list] = mapped_column(JSON, default=list)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class AssessmentControl(Base):
    __tablename__ = "assessment_controls"
    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id"), index=True)
    control_id: Mapped[str] = mapped_column(ForeignKey("controls.id"))
    dims: Mapped[list] = mapped_column(JSON)
    design: Mapped[float] = mapped_column(Float)
    operating: Mapped[float] = mapped_column(Float)
    origin: Mapped[str] = mapped_column(String(16))  # mapped | human
    matched_on: Mapped[str] = mapped_column(String(256), default="")


class Override(Base):
    __tablename__ = "overrides"
    id: Mapped[int] = mapped_column(primary_key=True)
    cr_id: Mapped[int] = mapped_column(ForeignKey("change_requests.id"), index=True)
    assessment_id: Mapped[int | None] = mapped_column(ForeignKey("assessments.id"), nullable=True)
    target_type: Mapped[str] = mapped_column(String(32))  # extraction|factor|control|narrative
    target_key: Mapped[str] = mapped_column(String(64))
    old_value: Mapped[Any] = mapped_column(JSON)
    new_value: Mapped[Any] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    tier_before: Mapped[str | None] = mapped_column(String(16), nullable=True)
    tier_after: Mapped[str | None] = mapped_column(String(16), nullable=True)
    requires_ack: Mapped[bool] = mapped_column(Boolean, default=False)
    acked_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    acked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CommitteeVote(Base):
    __tablename__ = "committee_votes"
    __table_args__ = (UniqueConstraint("cr_id", "user_id", "round"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    cr_id: Mapped[int] = mapped_column(ForeignKey("change_requests.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    round: Mapped[int] = mapped_column(Integer, default=1)
    vote: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rationale: Mapped[str] = mapped_column(Text, default="")
    conflict: Mapped[bool] = mapped_column(Boolean, default=False)
    conditions: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    cr_id: Mapped[int] = mapped_column(ForeignKey("change_requests.id"), index=True)
    round: Mapped[int] = mapped_column(Integer, default=1)
    outcome: Mapped[str] = mapped_column(String(32))
    conditions: Mapped[list] = mapped_column(JSON, default=list)
    vote_summary: Mapped[dict] = mapped_column(JSON)
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PolicyChunk(Base):
    __tablename__ = "policy_chunks"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    doc_id: Mapped[str] = mapped_column(String(32))
    doc_title: Mapped[str] = mapped_column(String(256))
    section_title: Mapped[str] = mapped_column(String(256))
    text: Mapped[str] = mapped_column(Text)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    source_url: Mapped[str] = mapped_column(String(512), default="")
    embed_model: Mapped[str] = mapped_column(String(64), default="")
    embedding: Mapped[list | None] = mapped_column(EmbeddingType(768), nullable=True)


class LLMCall(Base):
    __tablename__ = "llm_calls"
    id: Mapped[int] = mapped_column(primary_key=True)
    cr_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    node: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(64))
    prompt_id: Mapped[str] = mapped_column(String(64))
    prompt_version: Mapped[str] = mapped_column(String(16))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_tokens: Mapped[int] = mapped_column(Integer, default=0)  # pre-call estimate; "saved" when cached/skipped
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32))  # ok | fallback | error | budget_skip
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LLMCache(Base):
    __tablename__ = "llm_cache"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    ts: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))
