from datetime import date, datetime

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

from config.settings import settings


# --- Engine and Session Setup ---

sync_engine = create_engine(settings.database_url_sync, echo=False)
async_engine = create_async_engine(settings.database_url, echo=False)

SyncSessionLocal = sessionmaker(bind=sync_engine)
AsyncSessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# --- Models ---


class Regulator(Base):
    __tablename__ = "regulators"

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    full_name = Column(Text, nullable=False)
    website_url = Column(Text)
    jurisdiction = Column(String(50), default="INDIA")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    documents = relationship("Document", back_populates="regulator")
    violations = relationship("Violation", back_populates="regulator")
    scrape_runs = relationship("ScrapeRun", back_populates="regulator")


class ViolationType(Base):
    __tablename__ = "violation_types"

    id = Column(Integer, primary_key=True)
    category = Column(String(50), nullable=False)
    subtype = Column(String(50), nullable=False)
    description = Column(Text)

    __table_args__ = (UniqueConstraint("category", "subtype"),)

    violations = relationship("Violation", back_populates="violation_type")


class Entity(Base):
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True)
    entity_type = Column(
        String(20),
        CheckConstraint("entity_type IN ('COMPANY', 'INDIVIDUAL', 'BANK', 'NBFC', 'OTHER')"),
        nullable=False,
    )
    entity_name = Column(Text, nullable=False)
    cin = Column(String(21), unique=True)
    pan = Column(String(10))
    gstin = Column(String(15))
    mca_status = Column(String(30))
    aliases = Column(ARRAY(Text), default=[])
    metadata_ = Column("metadata", JSONB, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    violations = relationship("Violation", back_populates="entity")

    __table_args__ = (
        Index("idx_entities_name_trgm", "entity_name", postgresql_using="gin", postgresql_ops={"entity_name": "gin_trgm_ops"}),
        Index("idx_entities_cin", "cin", postgresql_where="cin IS NOT NULL"),
        Index("idx_entities_type", "entity_type"),
    )


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    source_url = Column(Text, nullable=False)
    content_hash = Column(String(64), unique=True, nullable=False)
    regulator_id = Column(Integer, ForeignKey("regulators.id"))
    document_type = Column(
        String(10),
        CheckConstraint("document_type IN ('PDF', 'HTML', 'IMAGE')"),
        nullable=False,
    )
    title = Column(Text)
    raw_storage_key = Column(Text, nullable=False)
    extracted_text = Column(Text)
    extraction_method = Column(String(20))
    language = Column(String(10), default="en")
    page_count = Column(Integer)
    scraped_at = Column(DateTime(timezone=True), nullable=False)
    processed_at = Column(DateTime(timezone=True))
    processing_status = Column(
        String(20),
        CheckConstraint("processing_status IN ('pending', 'processing', 'completed', 'failed', 'review')"),
        default="pending",
    )
    metadata_ = Column("metadata", JSONB, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    regulator = relationship("Regulator", back_populates="documents")
    violations = relationship("Violation", back_populates="document")

    __table_args__ = (
        Index("idx_documents_hash", "content_hash"),
        Index("idx_documents_regulator", "regulator_id"),
        Index("idx_documents_status", "processing_status"),
        Index("idx_documents_scraped", "scraped_at"),
    )


class Violation(Base):
    __tablename__ = "violations"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    regulator_id = Column(Integer, ForeignKey("regulators.id"), nullable=False)
    entity_id = Column(Integer, ForeignKey("entities.id"))
    violation_type_id = Column(Integer, ForeignKey("violation_types.id"))

    order_date = Column(Date)
    violation_date = Column(Date)
    summary = Column(Text)
    raw_excerpt = Column(Text)

    violation_category = Column(String(50))
    violation_subtype = Column(String(50))
    severity = Column(
        String(20),
        CheckConstraint("severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')"),
    )

    appeal_status = Column(String(30))

    extraction_confidence = Column(Float, nullable=False, default=0.0)
    review_status = Column(
        String(20),
        CheckConstraint("review_status IN ('auto_approved', 'pending_review', 'human_approved', 'human_rejected')"),
        default="auto_approved",
    )
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime(timezone=True))

    metadata_ = Column("metadata", JSONB, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    document = relationship("Document", back_populates="violations")
    regulator = relationship("Regulator", back_populates="violations")
    entity = relationship("Entity", back_populates="violations")
    violation_type = relationship("ViolationType", back_populates="violations")
    penalties = relationship("Penalty", back_populates="violation")

    __table_args__ = (
        Index("idx_violations_entity", "entity_id"),
        Index("idx_violations_regulator", "regulator_id"),
        Index("idx_violations_order_date", "order_date"),
        Index("idx_violations_type", "violation_category", "violation_subtype"),
        Index("idx_violations_review", "review_status", postgresql_where="review_status = 'pending_review'"),
    )


class Penalty(Base):
    __tablename__ = "penalties"

    id = Column(Integer, primary_key=True)
    violation_id = Column(Integer, ForeignKey("violations.id"), nullable=False)
    penalty_type = Column(
        String(30),
        CheckConstraint("penalty_type IN ('MONETARY', 'SUSPENSION', 'REVOCATION', 'WARNING', 'DEBARMENT', 'DIRECTION', 'OTHER')"),
        nullable=False,
    )
    amount_inr = Column(Numeric(15, 2))
    amount_raw_text = Column(Text)
    currency = Column(String(3), default="INR")
    duration_days = Column(Integer)
    description = Column(Text)
    metadata_ = Column("metadata", JSONB, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    violation = relationship("Violation", back_populates="penalties")

    __table_args__ = (
        Index("idx_penalties_violation", "violation_id"),
        Index("idx_penalties_amount", "amount_inr", postgresql_where="amount_inr IS NOT NULL"),
    )


class ViolationEntity(Base):
    __tablename__ = "violation_entities"

    violation_id = Column(Integer, ForeignKey("violations.id"), primary_key=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), primary_key=True)
    role = Column(
        String(30),
        CheckConstraint("role IN ('RESPONDENT', 'COMPLAINANT', 'WITNESS', 'RELATED_PARTY')"),
        primary_key=True,
        default="RESPONDENT",
    )


class MCACompanyMaster(Base):
    __tablename__ = "mca_company_master"

    cin = Column(String(21), primary_key=True)
    company_name = Column(Text, nullable=False)
    company_status = Column(String(30))
    company_class = Column(String(30))
    date_of_incorporation = Column(Date)
    registered_state = Column(String(50))
    roc = Column(String(50))
    email = Column(Text)
    loaded_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_mca_name_trgm", "company_name", postgresql_using="gin", postgresql_ops={"company_name": "gin_trgm_ops"}),
        Index("idx_mca_status", "company_status"),
    )


class EntityResolutionLog(Base):
    __tablename__ = "entity_resolution_log"

    id = Column(Integer, primary_key=True)
    extracted_name = Column(Text, nullable=False)
    resolved_entity_id = Column(Integer, ForeignKey("entities.id"))
    resolution_method = Column(String(30))
    confidence = Column(Float)
    resolved_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class ReviewQueue(Base):
    __tablename__ = "review_queue"

    id = Column(Integer, primary_key=True)
    violation_id = Column(Integer, ForeignKey("violations.id"))
    document_id = Column(Integer, ForeignKey("documents.id"))
    reason = Column(Text, nullable=False)
    priority = Column(Integer, default=5)
    assigned_to = Column(String(100))
    status = Column(
        String(20),
        CheckConstraint("status IN ('open', 'assigned', 'resolved', 'skipped')"),
        default="open",
    )
    resolution_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    resolved_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_review_queue_status", "status", "priority"),
    )


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id = Column(Integer, primary_key=True)
    regulator_id = Column(Integer, ForeignKey("regulators.id"), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    status = Column(
        String(20),
        CheckConstraint("status IN ('running', 'completed', 'failed', 'partial')"),
        default="running",
    )
    documents_found = Column(Integer, default=0)
    documents_new = Column(Integer, default=0)
    documents_failed = Column(Integer, default=0)
    error_message = Column(Text)
    metadata_ = Column("metadata", JSONB, default={})

    regulator = relationship("Regulator", back_populates="scrape_runs")
