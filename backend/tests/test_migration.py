import json
import uuid

import pytest
from datetime import datetime, timezone

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.db.session import reset_engine


def test_sqlite_migration_keeps_historical_ids_and_null_delta(tmp_path, monkeypatch):
    database = tmp_path / "migration.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{database.as_posix()}")
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    reset_engine()
    config = Config("alembic.ini")
    command.upgrade(config, "0001_initial")

    now = datetime.now(timezone.utc).isoformat()
    user_id = uuid.uuid4().hex
    company_id = uuid.uuid4().hex
    reconciliation_id = uuid.uuid4().hex
    file_id = uuid.uuid4().hex
    missing_id = uuid.uuid4().hex
    matched_id = uuid.uuid4().hex
    event_id = uuid.uuid4().hex
    storage_path = "reconciliations/historical.csv"
    missing_payload = {
        "differences": [],
        "erp_row_indexes": [0],
        "dian_row_indexes": [],
        "erp_normalized": {"total_amount": "1190.00", "third_party_id": "900123456", "issue_date": "2026-01-15"},
        "dian_normalized": None,
    }
    matched_payload = {
        "differences": [],
        "erp_row_indexes": [1],
        "dian_row_indexes": [1],
        "erp_normalized": {"total_amount": "10.00", "issue_date": "2026-01-16"},
        "dian_normalized": {"total_amount": "10.00", "issue_date": "2026-01-16"},
    }
    engine = create_engine(f"sqlite+pysqlite:///{database.as_posix()}")
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO users (id, full_name, email, status, created_at) VALUES (:id, 'Histórico', 'hist@example.com', 'active', :created_at)"),
            {"id": user_id, "created_at": now},
        )
        connection.execute(
            text("INSERT INTO companies (id, legal_name, tax_id, status, created_at) VALUES (:id, 'Empresa Histórica', '900', 'active', :created_at)"),
            {"id": company_id, "created_at": now},
        )
        connection.execute(
            text(
                """
                INSERT INTO reconciliations (
                    id, company_id, period_start, period_end, status, tolerance, created_at, executed_at
                ) VALUES (
                    :id, :company_id, '2026-01-01', '2026-01-31', 'completed', 0, :created_at, :created_at
                )
                """
            ),
            {"id": reconciliation_id, "company_id": company_id, "created_at": now},
        )
        connection.execute(
            text(
                """
                INSERT INTO reconciliation_files (
                    id, reconciliation_id, source, original_filename, detected_type, size_bytes, sha256,
                    storage_path, row_count, headers, warnings, created_at
                ) VALUES (
                    :id, :reconciliation_id, 'erp', 'ventas.csv', 'csv', 12, 'abc',
                    :storage_path, 1, '["factura"]', '[]', :created_at
                )
                """
            ),
            {"id": file_id, "reconciliation_id": reconciliation_id, "storage_path": storage_path, "created_at": now},
        )
        for result_id, category, payload in (
            (missing_id, "MISSING_IN_DIAN", missing_payload),
            (matched_id, "MATCHED", matched_payload),
        ):
            connection.execute(
                text(
                    """
                    INSERT INTO reconciliation_results (
                        id, reconciliation_id, document_key, primary_category, flags_text, payload
                    ) VALUES (:id, :reconciliation_id, :document_key, :category, '', :payload)
                    """
                ),
                {
                    "id": result_id,
                    "reconciliation_id": reconciliation_id,
                    "document_key": category,
                    "category": category,
                    "payload": json.dumps(payload),
                },
            )
        connection.execute(
            text(
                """
                INSERT INTO reconciliation_events (id, reconciliation_id, event_type, message, created_at)
                VALUES (:id, :reconciliation_id, 'run_completed', 'La conciliación terminó.', :created_at)
                """
            ),
            {"id": event_id, "reconciliation_id": reconciliation_id, "created_at": now},
        )

    command.upgrade(config, "head")
    with engine.connect() as connection:
        missing = connection.execute(text("SELECT id, total_delta, review_status, run_id FROM reconciliation_results WHERE id = :id"), {"id": missing_id}).one()
        matched = connection.execute(text("SELECT total_delta FROM reconciliation_results WHERE id = :id"), {"id": matched_id}).one()
        stored_file = connection.execute(text("SELECT id, storage_path FROM reconciliation_files WHERE id = :id"), {"id": file_id}).one()
        event = connection.execute(text("SELECT id, run_id FROM reconciliation_events WHERE id = :id"), {"id": event_id}).one()
        run = connection.execute(text("SELECT sequence, reconciliation_id FROM reconciliation_runs")).one()
        assert missing.id == missing_id
        assert missing.total_delta is None
        assert missing.review_status == "PENDING"
        assert matched.total_delta == 0 or str(matched.total_delta) in {"0", "0.0", "0.0000"}
        assert stored_file.id == file_id
        assert stored_file.storage_path == storage_path
        assert event.id == event_id
        assert event.run_id == missing.run_id
        assert run.sequence == 1
        assert run.reconciliation_id == reconciliation_id
        second_run = uuid.uuid4().hex
        connection.execute(
            text(
                """
                INSERT INTO reconciliation_runs (
                    id, reconciliation_id, sequence, status, tolerance, created_at
                ) VALUES (:id, :reconciliation_id, 2, 'completed', 0, :created_at)
                """
            ),
            {"id": second_run, "reconciliation_id": reconciliation_id, "created_at": now},
        )
        connection.execute(
            text(
                """
                INSERT INTO reconciliation_results (
                    id, reconciliation_id, run_id, document_key, primary_category, flags_text, payload, review_status
                ) VALUES (:id, :reconciliation_id, :run_id, 'MISSING_IN_DIAN', 'MISSING_IN_DIAN', '', '{}', 'PENDING')
                """
            ),
            {"id": uuid.uuid4().hex, "reconciliation_id": reconciliation_id, "run_id": second_run},
        )
    reset_engine()
    get_settings.cache_clear()


def test_postgres_migration_is_opt_in(monkeypatch):
    url = __import__("os").environ.get("POSTGRES_TEST_URL")
    if not url:
        pytest.skip("PostgreSQL 16 no está disponible para validar la migración.")
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    reset_engine()
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    reset_engine()
    get_settings.cache_clear()
