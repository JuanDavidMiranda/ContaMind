"""Ejecuciones versionadas y datos de revisión por resultado.

Cada conciliación existente se convierte en la ejecución 1. Se conservan los
UUID de conciliaciones, archivos, resultados y eventos.
"""

import json
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

from app.modules.reconciliations.application.facts import (
    extract_issue_date,
    extract_third_party_key,
    extract_total_delta,
)

revision = "0002_reconciliation_runs"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reconciliation_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("reconciliation_id", sa.Uuid(), sa.ForeignKey("reconciliations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("tolerance", sa.Numeric(18, 4), nullable=False),
        sa.Column("erp_mapping", sa.JSON(), nullable=True),
        sa.Column("dian_mapping", sa.JSON(), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("rules", sa.JSON(), nullable=True),
        sa.Column("validation_errors", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("reconciliation_id", "sequence", name="uq_reconciliation_run_sequence"),
    )
    op.create_index("ix_reconciliation_runs_reconciliation_id", "reconciliation_runs", ["reconciliation_id"])
    op.create_index("ix_reconciliation_runs_status", "reconciliation_runs", ["status"])
    _backfill_runs()
    _attach_children()
    op.create_table(
        "result_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("result_id", sa.Uuid(), sa.ForeignKey("reconciliation_results.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reconciliation_id", sa.Uuid(), sa.ForeignKey("reconciliations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("previous_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_result_events_result_id", "result_events", ["result_id"])
    op.create_index("ix_result_events_run_id", "result_events", ["run_id"])
    op.create_index("ix_result_events_reconciliation_id", "result_events", ["reconciliation_id"])


def downgrade() -> None:
    bind = op.get_bind()
    extra = bind.execute(sa.text("SELECT COUNT(*) FROM reconciliation_runs WHERE sequence > 1")).scalar_one()
    if extra:
        raise RuntimeError("No se revierte la migración porque hay conciliaciones con más de una ejecución.")
    op.drop_table("result_events")
    if bind.dialect.name == "sqlite":
        _sqlite_detach()
    else:
        _postgres_detach()
    op.drop_index("ix_reconciliation_runs_status", table_name="reconciliation_runs")
    op.drop_index("ix_reconciliation_runs_reconciliation_id", table_name="reconciliation_runs")
    op.drop_table("reconciliation_runs")


def _backfill_runs() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT id, status, tolerance, erp_mapping, dian_mapping, summary, rules,
                   validation_errors, created_at, executed_at
            FROM reconciliations
            """
        )
    ).mappings()
    now = datetime.now(timezone.utc)
    json_value = "CAST(:{name} AS json)" if bind.dialect.name == "postgresql" else ":{name}"
    statement = sa.text(
        f"""
        INSERT INTO reconciliation_runs (
            id, reconciliation_id, sequence, status, tolerance, erp_mapping, dian_mapping,
            summary, rules, validation_errors, created_at, executed_at
        ) VALUES (
            :id, :reconciliation_id, 1, :status, :tolerance,
            {json_value.format(name="erp_mapping")},
            {json_value.format(name="dian_mapping")},
            {json_value.format(name="summary")},
            {json_value.format(name="rules")},
            {json_value.format(name="validation_errors")},
            :created_at, :executed_at
        )
        """
    )
    for row in rows:
        bind.execute(
            statement,
            {
                "id": _new_id(bind),
                "reconciliation_id": _as_text(row["id"], bind),
                "status": row["status"],
                "tolerance": row["tolerance"],
                "erp_mapping": _json_param(row["erp_mapping"]),
                "dian_mapping": _json_param(row["dian_mapping"]),
                "summary": _json_param(row["summary"]),
                "rules": _json_param(row["rules"]),
                "validation_errors": _json_param(row["validation_errors"]),
                "created_at": row["created_at"] or now,
                "executed_at": row["executed_at"],
            },
        )


def _attach_children() -> None:
    bind = op.get_bind()
    _add_run_links()
    runs = bind.execute(sa.text("SELECT id, reconciliation_id FROM reconciliation_runs WHERE sequence = 1")).mappings()
    for run in runs:
        params = {"run_id": _as_text(run["id"], bind), "reconciliation_id": _as_text(run["reconciliation_id"], bind)}
        for table in ("reconciliation_files", "reconciliation_results", "reconciliation_events"):
            bind.execute(
                sa.text(f"UPDATE {table} SET run_id = :run_id WHERE reconciliation_id = :reconciliation_id"),
                params,
            )
    _backfill_result_facts()
    if bind.dialect.name == "sqlite":
        _sqlite_finalize()
    else:
        _postgres_finalize()


def _add_run_links() -> None:
    op.add_column("reconciliation_files", sa.Column("run_id", sa.Uuid(), nullable=True))
    op.add_column("reconciliation_results", sa.Column("run_id", sa.Uuid(), nullable=True))
    op.add_column("reconciliation_results", sa.Column("review_status", sa.String(32), nullable=False, server_default="PENDING"))
    op.add_column("reconciliation_results", sa.Column("review_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("reconciliation_results", sa.Column("third_party_key", sa.String(512), nullable=True))
    op.add_column("reconciliation_results", sa.Column("erp_issue_date", sa.Date(), nullable=True))
    op.add_column("reconciliation_results", sa.Column("dian_issue_date", sa.Date(), nullable=True))
    op.add_column("reconciliation_results", sa.Column("total_delta", sa.Numeric(18, 4), nullable=True))
    op.add_column("reconciliation_events", sa.Column("run_id", sa.Uuid(), nullable=True))


def _backfill_result_facts() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, primary_category, payload FROM reconciliation_results")).mappings()
    for row in rows:
        payload = _load_json(row["payload"]) or {}
        if not isinstance(payload, dict):
            payload = {}
        delta = extract_total_delta(row["primary_category"], payload)
        erp_date = extract_issue_date(payload, "erp")
        dian_date = extract_issue_date(payload, "dian")
        bind.execute(
            sa.text(
                """
                UPDATE reconciliation_results
                SET total_delta = :total_delta,
                    third_party_key = :third_party_key,
                    erp_issue_date = :erp_issue_date,
                    dian_issue_date = :dian_issue_date
                WHERE id = :id
                """
            ),
            {
                "id": _as_text(row["id"], bind),
                "total_delta": None if delta is None else format(delta, "f"),
                "third_party_key": extract_third_party_key(payload),
                "erp_issue_date": None if erp_date is None else erp_date.isoformat(),
                "dian_issue_date": None if dian_date is None else dian_date.isoformat(),
            },
        )


def _postgres_finalize() -> None:
    op.alter_column("reconciliation_files", "run_id", nullable=False)
    op.alter_column("reconciliation_results", "run_id", nullable=False)
    op.alter_column("reconciliation_events", "run_id", nullable=False)
    op.create_foreign_key("fk_reconciliation_files_run_id", "reconciliation_files", "reconciliation_runs", ["run_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_reconciliation_results_run_id", "reconciliation_results", "reconciliation_runs", ["run_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_reconciliation_events_run_id", "reconciliation_events", "reconciliation_runs", ["run_id"], ["id"], ondelete="CASCADE")
    op.drop_constraint("uq_reconciliation_file_source", "reconciliation_files", type_="unique")
    op.drop_constraint("uq_reconciliation_document_key", "reconciliation_results", type_="unique")
    op.create_unique_constraint("uq_run_file_source", "reconciliation_files", ["run_id", "source"])
    op.create_unique_constraint("uq_run_document_key", "reconciliation_results", ["run_id", "document_key"])
    op.create_index("ix_reconciliation_files_run_id", "reconciliation_files", ["run_id"])
    op.create_index("ix_reconciliation_results_run_id", "reconciliation_results", ["run_id"])
    op.create_index("ix_reconciliation_results_review_status", "reconciliation_results", ["review_status"])
    op.create_index("ix_reconciliation_events_run_id", "reconciliation_events", ["run_id"])


def _sqlite_finalize() -> None:
    with op.batch_alter_table("reconciliation_files") as batch:
        batch.alter_column("run_id", existing_type=sa.Uuid(), nullable=False)
        batch.create_foreign_key("fk_reconciliation_files_run_id", "reconciliation_runs", ["run_id"], ["id"], ondelete="CASCADE")
        batch.drop_constraint("uq_reconciliation_file_source", type_="unique")
        batch.create_unique_constraint("uq_run_file_source", ["run_id", "source"])
    with op.batch_alter_table("reconciliation_results") as batch:
        batch.alter_column("run_id", existing_type=sa.Uuid(), nullable=False)
        batch.create_foreign_key("fk_reconciliation_results_run_id", "reconciliation_runs", ["run_id"], ["id"], ondelete="CASCADE")
        batch.drop_constraint("uq_reconciliation_document_key", type_="unique")
        batch.create_unique_constraint("uq_run_document_key", ["run_id", "document_key"])
    with op.batch_alter_table("reconciliation_events") as batch:
        batch.alter_column("run_id", existing_type=sa.Uuid(), nullable=False)
        batch.create_foreign_key("fk_reconciliation_events_run_id", "reconciliation_runs", ["run_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_reconciliation_files_run_id", "reconciliation_files", ["run_id"])
    op.create_index("ix_reconciliation_results_run_id", "reconciliation_results", ["run_id"])
    op.create_index("ix_reconciliation_results_review_status", "reconciliation_results", ["review_status"])
    op.create_index("ix_reconciliation_events_run_id", "reconciliation_events", ["run_id"])


def _sqlite_detach() -> None:
    op.drop_index("ix_reconciliation_events_run_id", table_name="reconciliation_events")
    op.drop_index("ix_reconciliation_results_review_status", table_name="reconciliation_results")
    op.drop_index("ix_reconciliation_results_run_id", table_name="reconciliation_results")
    op.drop_index("ix_reconciliation_files_run_id", table_name="reconciliation_files")
    with op.batch_alter_table("reconciliation_events") as batch:
        batch.drop_constraint("fk_reconciliation_events_run_id", type_="foreignkey")
        batch.drop_column("run_id")
    with op.batch_alter_table("reconciliation_results") as batch:
        batch.drop_constraint("uq_run_document_key", type_="unique")
        batch.create_unique_constraint("uq_reconciliation_document_key", ["reconciliation_id", "document_key"])
        batch.drop_constraint("fk_reconciliation_results_run_id", type_="foreignkey")
        batch.drop_column("total_delta")
        batch.drop_column("dian_issue_date")
        batch.drop_column("erp_issue_date")
        batch.drop_column("third_party_key")
        batch.drop_column("review_updated_at")
        batch.drop_column("review_status")
        batch.drop_column("run_id")
    with op.batch_alter_table("reconciliation_files") as batch:
        batch.drop_constraint("uq_run_file_source", type_="unique")
        batch.create_unique_constraint("uq_reconciliation_file_source", ["reconciliation_id", "source"])
        batch.drop_constraint("fk_reconciliation_files_run_id", type_="foreignkey")
        batch.drop_column("run_id")


def _postgres_detach() -> None:
    op.drop_index("ix_reconciliation_events_run_id", table_name="reconciliation_events")
    op.drop_index("ix_reconciliation_results_review_status", table_name="reconciliation_results")
    op.drop_index("ix_reconciliation_results_run_id", table_name="reconciliation_results")
    op.drop_index("ix_reconciliation_files_run_id", table_name="reconciliation_files")
    op.drop_constraint("fk_reconciliation_events_run_id", "reconciliation_events", type_="foreignkey")
    op.drop_constraint("fk_reconciliation_results_run_id", "reconciliation_results", type_="foreignkey")
    op.drop_constraint("fk_reconciliation_files_run_id", "reconciliation_files", type_="foreignkey")
    op.drop_constraint("uq_run_file_source", "reconciliation_files", type_="unique")
    op.drop_constraint("uq_run_document_key", "reconciliation_results", type_="unique")
    op.create_unique_constraint("uq_reconciliation_file_source", "reconciliation_files", ["reconciliation_id", "source"])
    op.create_unique_constraint("uq_reconciliation_document_key", "reconciliation_results", ["reconciliation_id", "document_key"])
    op.drop_column("reconciliation_events", "run_id")
    for name in ("total_delta", "dian_issue_date", "erp_issue_date", "third_party_key", "review_updated_at", "review_status", "run_id"):
        op.drop_column("reconciliation_results", name)
    op.drop_column("reconciliation_files", "run_id")


def _load_json(value):
    if value is None or isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return value


def _json_param(value):
    loaded = _load_json(value)
    if loaded is None:
        return None
    return json.dumps(loaded)


def _new_id(bind) -> str:
    value = uuid.uuid4()
    if bind.dialect.name == "postgresql":
        return str(value)
    return value.hex


def _as_text(value, bind) -> str:
    if isinstance(value, uuid.UUID):
        return str(value) if bind.dialect.name == "postgresql" else value.hex
    text = str(value)
    if bind.dialect.name == "postgresql":
        return text
    return text.replace("-", "")
