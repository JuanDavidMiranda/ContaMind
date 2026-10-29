import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.identity.models import utcnow


class Reconciliation(Base):
    __tablename__ = "reconciliations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    tolerance: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    erp_mapping: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    dian_mapping: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    validation_errors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    runs: Mapped[list["ReconciliationRun"]] = relationship(
        back_populates="reconciliation",
        cascade="all, delete-orphan",
        order_by="ReconciliationRun.sequence",
    )


class ReconciliationRun(Base):
    __tablename__ = "reconciliation_runs"
    __table_args__ = (UniqueConstraint("reconciliation_id", "sequence", name="uq_reconciliation_run_sequence"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reconciliation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reconciliations.id", ondelete="CASCADE"),
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    tolerance: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    erp_mapping: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    dian_mapping: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    validation_errors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reconciliation: Mapped[Reconciliation] = relationship(back_populates="runs")
    files: Mapped[list["ReconciliationFile"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )
    results: Mapped[list["ReconciliationResult"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )
    events: Mapped[list["ReconciliationEvent"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class ReconciliationFile(Base):
    __tablename__ = "reconciliation_files"
    __table_args__ = (UniqueConstraint("run_id", "source", name="uq_run_file_source"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reconciliation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reconciliations.id", ondelete="CASCADE"),
        index=True,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(16))
    original_filename: Mapped[str] = mapped_column(String(255))
    detected_type: Mapped[str] = mapped_column(String(16))
    encoding: Mapped[str | None] = mapped_column(String(32), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_path: Mapped[str] = mapped_column(String(500))
    row_count: Mapped[int] = mapped_column(Integer)
    headers: Mapped[list] = mapped_column(JSON)
    warnings: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped[ReconciliationRun] = relationship(back_populates="files")


class ReconciliationResult(Base):
    __tablename__ = "reconciliation_results"
    __table_args__ = (UniqueConstraint("run_id", "document_key", name="uq_run_document_key"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reconciliation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reconciliations.id", ondelete="CASCADE"),
        index=True,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), index=True)
    document_key: Mapped[str] = mapped_column(String(255), index=True)
    primary_category: Mapped[str] = mapped_column(String(32), index=True)
    flags_text: Mapped[str] = mapped_column(String(255), default="")
    duplicate_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)
    review_status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    review_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    third_party_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    erp_issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    dian_issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_delta: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)

    run: Mapped[ReconciliationRun] = relationship(back_populates="results")
    review_events: Mapped[list["ResultEvent"]] = relationship(
        back_populates="result",
        cascade="all, delete-orphan",
        order_by="ResultEvent.created_at",
    )


class ReconciliationEvent(Base):
    __tablename__ = "reconciliation_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reconciliation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reconciliations.id", ondelete="CASCADE"),
        index=True,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped[ReconciliationRun] = relationship(back_populates="events")


class ResultEvent(Base):
    """Historial de revisión. Las operaciones normales solo agregan filas."""

    __tablename__ = "result_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    result_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reconciliation_results.id", ondelete="CASCADE"),
        index=True,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), index=True)
    reconciliation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reconciliations.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text)
    previous_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    result: Mapped[ReconciliationResult] = relationship(back_populates="review_events")
