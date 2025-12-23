"""
SQLAlchemy database models.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Integer, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, DeclarativeBase
import enum


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class AnalysisStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class Repository(Base):
    """Repository model."""
    __tablename__ = "repositories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    url = Column(String(500), nullable=False, unique=True)
    provider = Column(String(50), default="github")  # github, gitlab, bitbucket
    name = Column(String(255))
    owner = Column(String(255))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    analysis_runs = relationship("AnalysisRun", back_populates="repository")


class AnalysisRun(Base):
    """Analysis run model."""
    __tablename__ = "analysis_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    repository_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    status = Column(Enum(AnalysisStatus), default=AnalysisStatus.queued)
    branch = Column(String(255))
    commit_sha = Column(String(40))
    region_mode = Column(String(10), default="EU_UA")

    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    error_message = Column(Text)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    repository = relationship("Repository", back_populates="analysis_runs")
    project = relationship("Project", back_populates="analyses")
    metrics = relationship("Metrics", back_populates="analysis_run", uselist=False)
    tasks = relationship("Task", back_populates="analysis_run")


class Metrics(Base):
    """Metrics storage for an analysis run."""
    __tablename__ = "metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False, unique=True)

    # Scoring results (stored as JSON)
    repo_health = Column(JSON)
    tech_debt = Column(JSON)
    product_level = Column(String(50))
    complexity = Column(String(10))

    # Cost estimates
    cost_estimates = Column(JSON)
    historical_estimate = Column(JSON)

    # Raw analysis data
    structure_data = Column(JSON)
    static_metrics = Column(JSON)
    semgrep_findings = Column(JSON)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    analysis_run = relationship("AnalysisRun", back_populates="metrics")


class TaskPriority(str, enum.Enum):
    p1 = "P1"
    p2 = "P2"
    p3 = "P3"


class TaskCategory(str, enum.Enum):
    documentation = "documentation"
    testing = "testing"
    refactoring = "refactoring"
    infrastructure = "infrastructure"
    security = "security"


class TaskStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    done = "done"
    wont_fix = "wont_fix"


class ProjectStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    on_hold = "on_hold"
    archived = "archived"


class ActivityType(str, enum.Enum):
    project_created = "project_created"
    project_updated = "project_updated"
    status_changed = "status_changed"
    analysis_started = "analysis_started"
    analysis_completed = "analysis_completed"
    analysis_failed = "analysis_failed"
    document_generated = "document_generated"
    comment_added = "comment_added"


class Task(Base):
    """Generated task model."""
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False)

    title = Column(String(500), nullable=False)
    description = Column(Text)
    category = Column(Enum(TaskCategory))
    priority = Column(Enum(TaskPriority), default=TaskPriority.p2)
    status = Column(Enum(TaskStatus), default=TaskStatus.open)
    estimate_hours = Column(Integer)
    labels = Column(JSON)  # List of string labels

    # GitHub integration
    github_issue_number = Column(Integer)
    github_issue_url = Column(String(500))

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    analysis_run = relationship("AnalysisRun", back_populates="tasks")


class Project(Base):
    """Project model for grouping analyses."""
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.active)

    # Client info
    client_name = Column(String(255))
    contract_number = Column(String(100))

    # Repository URLs (JSON array)
    repository_urls = Column(JSON, default=list)

    # Budget and rates
    budget_hours = Column(Integer)
    hourly_rate = Column(Integer)
    currency = Column(String(10), default="USD")

    # Metadata
    tags = Column(JSON, default=list)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    activities = relationship("ProjectActivity", back_populates="project", order_by="desc(ProjectActivity.created_at)")
    analyses = relationship("AnalysisRun", back_populates="project")


class ProjectActivity(Base):
    """Activity log for projects."""
    __tablename__ = "project_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)

    activity_type = Column(Enum(ActivityType), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    details = Column(JSON)  # Additional data like analysis_id, old_status, new_status, etc.

    # Who performed the action (optional)
    actor = Column(String(255))

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    project = relationship("Project", back_populates="activities")


# =========================================================================
# DOCUMENT MANAGEMENT MODELS
# =========================================================================


class DocumentType(str, enum.Enum):
    """Types of documents that can be uploaded."""
    contract = "contract"
    policy = "policy"
    template = "template"
    report = "report"
    invoice = "invoice"
    act = "act"
    other = "other"


class ProcessingStatus(str, enum.Enum):
    """Document processing status."""
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    needs_review = "needs_review"


class DocumentLinkType(str, enum.Enum):
    """Type of link between document and analysis."""
    source_contract = "source_contract"
    reference = "reference"
    generated = "generated"
    comparison = "comparison"


class Document(Base):
    """Uploaded document model."""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Metadata
    title = Column(String(500), nullable=False)
    document_type = Column(Enum(DocumentType), nullable=False, default=DocumentType.other)
    file_name = Column(String(255))
    mime_type = Column(String(100))
    file_size = Column(Integer)

    # Content
    original_content = Column(Text)  # For text-based, use LargeBinary for binary
    extracted_text = Column(Text)

    # Storage reference (for external storage like S3)
    storage_backend = Column(String(50), default="db")  # db, local, s3, gdrive
    storage_key = Column(String(500))  # Path or key in external storage

    # Direct link to analysis (optional, for simple cases)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=True)

    # For versioning
    parent_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    version = Column(Integer, default=1)

    # Processing status
    processing_status = Column(Enum(ProcessingStatus), default=ProcessingStatus.pending)
    processing_error = Column(Text)
    extraction_confidence = Column(Integer)  # 0-100
    extraction_method = Column(String(50))  # regex, llm, hybrid

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime)
    deleted_at = Column(DateTime)  # Soft delete

    # Relationships
    analysis = relationship("AnalysisRun", foreign_keys=[analysis_id])
    parent_document = relationship("Document", remote_side=[id], foreign_keys=[parent_document_id])
    contract_data = relationship("ContractData", back_populates="document", uselist=False, cascade="all, delete-orphan")
    analysis_links = relationship("DocumentAnalysisLink", back_populates="document", cascade="all, delete-orphan")


class ContractData(Base):
    """Extracted contract data."""
    __tablename__ = "contract_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Contract identification
    contract_number = Column(String(100))
    contract_title = Column(String(500))
    contract_date = Column(DateTime)
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    # Financial
    total_amount = Column(Integer)  # Store in cents to avoid float issues
    currency = Column(String(10), default="USD")

    # Parties
    client_name = Column(String(255))
    client_address = Column(Text)
    contractor_name = Column(String(255))
    contractor_address = Column(Text)

    # Structured data (JSON)
    work_plan = Column(JSON)  # [{phase, description, duration, deliverables}]
    budget_breakdown = Column(JSON)  # [{category, amount, description}]
    milestones = Column(JSON)  # [{name, date, deliverable, payment}]
    indicators = Column(JSON)  # [{name, target, measurement}]
    policies = Column(JSON)  # [{type, requirement, source_text}]
    deliverables = Column(JSON)  # [{name, description, due_date}]

    # Raw extracted sections
    raw_sections = Column(JSON)  # {section_name: text}

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    document = relationship("Document", back_populates="contract_data")


class DocumentAnalysisLink(Base):
    """Many-to-many link between documents and analyses."""
    __tablename__ = "document_analysis_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False)
    link_type = Column(Enum(DocumentLinkType), nullable=False, default=DocumentLinkType.reference)

    # Optional metadata
    notes = Column(Text)
    created_by = Column(String(255))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    document = relationship("Document", back_populates="analysis_links")
    analysis = relationship("AnalysisRun")


class ExtractionPattern(Base):
    """Learned extraction patterns."""
    __tablename__ = "extraction_patterns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    pattern_type = Column(String(50), nullable=False)  # date, amount, activity, deliverable
    pattern_regex = Column(Text, nullable=False)
    pattern_description = Column(String(255))

    # Training data
    examples = Column(JSON)  # [{source_text, extracted_value}]
    confidence_score = Column(Integer, default=50)  # 0-100
    usage_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)

    # Status
    is_active = Column(String(10), default="true")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_used_at = Column(DateTime)
