import logging
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.errors import AppError
from app.modules.companies.models import Company, CompanyMembership
from app.modules.companies.service import get_company
from app.modules.identity.models import User
from app.modules.reconciliations.application.schemas import (
    ColumnMapping,
    ColumnsPreview,
    FileRead,
    ReconciliationCreate,
    ReconciliationRead,
    ResultPage,
    SourcePreview,
)
from app.modules.reconciliations.application.facts import (
    build_review_progress,
    extract_issue_date,
    extract_third_party_key,
    extract_total_delta,
)
from app.modules.reconciliations.engine.columns import suggest_columns
from app.modules.reconciliations.engine.normalization import format_decimal
from app.modules.reconciliations.engine.reconcile import reconcile
from app.modules.reconciliations.infrastructure.orm import (
    Reconciliation,
    ReconciliationEvent,
    ReconciliationFile,
    ReconciliationResult,
    ReconciliationRun,
)
from app.modules.reconciliations.infrastructure.reader import read_tabular
from app.modules.reconciliations.infrastructure.report import build_report
from app.modules.reconciliations.infrastructure.storage import (
    content_sha256,
    delete_private_file,
    resolve_private_file,
    save_private_file,
)

logger = logging.getLogger("contamind.reconciliations")
FLAG_CATEGORIES = {
    "VALUE_MISMATCH",
    "DATE_MISMATCH",
    "THIRD_PARTY_MISMATCH",
    "POSSIBLE_DUPLICATE",
    "REQUIRES_REVIEW",
}


def create_reconciliation(db: Session, user: User, payload: ReconciliationCreate) -> Reconciliation:
    company = get_company(db, user, payload.company_id)
    if company.status != "active":
        raise AppError("inactive_company", "La empresa no está activa.", 409)
    reconciliation = Reconciliation(
        company_id=company.id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        tolerance=payload.tolerance,
        status="draft",
    )
    db.add(reconciliation)
    db.flush()
    run = ReconciliationRun(
        reconciliation_id=reconciliation.id,
        sequence=1,
        status="draft",
        tolerance=payload.tolerance,
    )
    db.add(run)
    db.flush()
    _event(db, reconciliation, run, "reconciliation_created", "Se creó la conciliación.")
    db.commit()
    db.refresh(reconciliation)
    logger.info("reconciliation created id=%s company_id=%s", reconciliation.id, company.id)
    return reconciliation


def list_reconciliations(db: Session, user: User, company_id: uuid.UUID | None = None) -> list[Reconciliation]:
    statement = (
        select(Reconciliation)
        .where(Reconciliation.company_id.in_(_company_ids(db, user)))
        .order_by(Reconciliation.created_at.desc())
    )
    if company_id is not None:
        get_company(db, user, company_id)
        statement = statement.where(Reconciliation.company_id == company_id)
    return list(db.scalars(statement).unique().all())


def get_reconciliation(db: Session, user: User, reconciliation_id: uuid.UUID) -> Reconciliation:
    statement = (
        select(Reconciliation)
        .where(
            Reconciliation.id == reconciliation_id,
            Reconciliation.company_id.in_(_company_ids(db, user)),
        )
    )
    reconciliation = db.scalar(statement)
    if reconciliation is None:
        raise AppError("not_found", "La conciliación no existe o no tienes acceso.", 404)
    return reconciliation


def upload_file(
    db: Session,
    user: User,
    reconciliation_id: uuid.UUID,
    source: str,
    filename: str,
    content: bytes,
) -> ReconciliationFile:
    if source not in {"erp", "dian"}:
        raise AppError("invalid_source", "La fuente debe ser erp o dian.", 422)
    settings = get_settings()
    if len(content) > settings.max_upload_bytes:
        raise AppError(
            "file_too_large",
            "El archivo supera el tamaño máximo permitido para este proceso.",
            422,
        )
    safe_name = Path(filename or "").name
    if not safe_name:
        raise AppError("invalid_filename", "El archivo no tiene nombre.", 422)
    reconciliation = get_reconciliation(db, user, reconciliation_id)
    run = _mutable_run(db, reconciliation)
    table = read_tabular(content, safe_name, max_rows=settings.max_rows_per_file)
    existing = _file_or_none(run, source)
    if existing is not None:
        delete_private_file(existing.storage_path)
        db.delete(existing)
        db.flush()
    relative_path = save_private_file(reconciliation.id, source, safe_name, content)
    stored = ReconciliationFile(
        reconciliation_id=reconciliation.id,
        run_id=run.id,
        source=source,
        original_filename=safe_name,
        detected_type=table.detected_type,
        encoding=table.encoding,
        size_bytes=len(content),
        sha256=content_sha256(content),
        storage_path=relative_path,
        row_count=len(table.rows),
        headers=table.headers,
        warnings=table.warnings,
    )
    db.add(stored)
    run.erp_mapping = None
    run.dian_mapping = None
    _clear_draft_output(db, run)
    db.flush()
    db.expire(run, ["files"])
    sources = {item.source for item in run.files}
    run.status = "files_uploaded" if {"erp", "dian"} <= sources else "draft"
    _project(reconciliation, run)
    _event(
        db,
        reconciliation,
        run,
        "file_stored",
        f"Se guardó el archivo de {source}.",
        {"filename": safe_name, "rows": len(table.rows), "type": table.detected_type},
    )
    db.commit()
    db.refresh(stored)
    logger.info(
        "file stored reconciliation_id=%s source=%s rows=%s",
        reconciliation.id,
        source,
        len(table.rows),
    )
    return stored


def preview_columns(db: Session, user: User, reconciliation_id: uuid.UUID) -> ColumnsPreview:
    reconciliation = get_reconciliation(db, user, reconciliation_id)
    run = _latest_run(db, reconciliation)
    return ColumnsPreview(
        erp=_preview_source(run, "erp"),
        dian=_preview_source(run, "dian"),
    )


def confirm_mapping(db: Session, user: User, reconciliation_id: uuid.UUID, erp: ColumnMapping, dian: ColumnMapping):
    reconciliation = get_reconciliation(db, user, reconciliation_id)
    run = _mutable_run(db, reconciliation)
    erp_file = _require_file(run, "erp")
    dian_file = _require_file(run, "dian")
    _validate_mapping(erp, erp_file.headers)
    _validate_mapping(dian, dian_file.headers)
    run.erp_mapping = erp.model_dump()
    run.dian_mapping = dian.model_dump()
    run.status = "mapping_confirmed"
    _clear_draft_output(db, run)
    _project(reconciliation, run)
    _event(db, reconciliation, run, "mapping_confirmed", "Se confirmó la asignación de columnas.")
    db.commit()
    db.refresh(reconciliation)
    return reconciliation


def run_reconciliation(db: Session, user: User, reconciliation_id: uuid.UUID) -> Reconciliation:
    reconciliation = get_reconciliation(db, user, reconciliation_id)
    run = _mutable_run(db, reconciliation)
    if run.status not in {"mapping_confirmed"}:
        raise AppError(
            "mapping_required",
            "Confirma la asignación de columnas antes de ejecutar la conciliación.",
            409,
        )
    if not run.erp_mapping or not run.dian_mapping:
        raise AppError("mapping_required", "Falta la asignación de columnas.", 409)
    erp_file = _require_file(run, "erp")
    dian_file = _require_file(run, "dian")
    run.status = "running"
    _project(reconciliation, run)
    _event(db, reconciliation, run, "run_started", "Comenzó la conciliación.")
    db.commit()
    try:
        settings = get_settings()
        erp_table = read_tabular(
            resolve_private_file(erp_file.storage_path).read_bytes(),
            erp_file.original_filename,
            max_rows=settings.max_rows_per_file,
        )
        dian_table = read_tabular(
            resolve_private_file(dian_file.storage_path).read_bytes(),
            dian_file.original_filename,
            max_rows=settings.max_rows_per_file,
        )
        outcome = reconcile(
            erp_table.rows,
            dian_table.rows,
            run.erp_mapping,
            run.dian_mapping,
            tolerance=Decimal(str(run.tolerance)),
        )
        _clear_draft_output(db, run)
        for row in outcome.results:
            if len(row.document_key) > 255:
                raise AppError(
                    "document_key_too_long",
                    "Hay un número de documento demasiado largo para guardarlo.",
                    422,
                )
            payload = row.to_dict()
            db.add(
                ReconciliationResult(
                    reconciliation_id=reconciliation.id,
                    run_id=run.id,
                    document_key=row.document_key,
                    primary_category=row.primary_category,
                    flags_text=",".join(row.flags),
                    duplicate_kind=row.duplicate_kind,
                    payload=payload,
                    review_status="PENDING",
                    third_party_key=extract_third_party_key(payload),
                    erp_issue_date=extract_issue_date(payload, "erp"),
                    dian_issue_date=extract_issue_date(payload, "dian"),
                    total_delta=extract_total_delta(row.primary_category, payload),
                )
            )
        run.summary = outcome.summary
        run.rules = outcome.rules
        run.validation_errors = [item.to_dict() for item in outcome.validation_errors]
        run.status = "completed"
        run.executed_at = datetime.now(timezone.utc)
        _project(reconciliation, run)
        _event(
            db,
            reconciliation,
            run,
            "run_completed",
            "La conciliación terminó.",
            {"result_count": outcome.summary["result_count"], "run_id": str(run.id)},
        )
        db.commit()
        logger.info(
            "reconciliation completed id=%s run_id=%s results=%s",
            reconciliation.id,
            run.id,
            outcome.summary["result_count"],
        )
    except AppError as exc:
        _mark_failed(db, reconciliation_id, run.id, exc.message)
        raise
    except Exception as exc:
        logger.exception("reconciliation failed id=%s", reconciliation_id)
        _mark_failed(db, reconciliation_id, run.id, "No fue posible ejecutar la conciliación.")
        raise AppError(
            "reconciliation_failed",
            "No fue posible ejecutar la conciliación.",
            500,
        ) from exc
    db.refresh(reconciliation)
    return reconciliation


def list_results(
    db: Session,
    user: User,
    reconciliation_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    category: str | None,
    query: str | None,
) -> ResultPage:
    reconciliation = get_reconciliation(db, user, reconciliation_id)
    run = _latest_run(db, reconciliation)
    filters = [ReconciliationResult.run_id == run.id]
    if category:
        if category in FLAG_CATEGORIES:
            filters.append(
                or_(
                    ReconciliationResult.primary_category == category,
                    ReconciliationResult.flags_text.contains(category),
                )
            )
        else:
            filters.append(ReconciliationResult.primary_category == category)
    if query:
        filters.append(ReconciliationResult.document_key.contains(query.strip().upper().replace(" ", "")))
    total = db.scalar(select(func.count()).select_from(ReconciliationResult).where(*filters)) or 0
    rows = db.scalars(
        select(ReconciliationResult)
        .where(*filters)
        .order_by(ReconciliationResult.document_key)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return ResultPage(
        items=[_public_result(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_result(db: Session, user: User, reconciliation_id: uuid.UUID, result_id: uuid.UUID) -> dict:
    reconciliation = get_reconciliation(db, user, reconciliation_id)
    row = db.scalar(
        select(ReconciliationResult).where(
            ReconciliationResult.id == result_id,
            ReconciliationResult.reconciliation_id == reconciliation.id,
        )
    )
    if row is None:
        raise AppError("not_found", "El resultado no existe.", 404)
    payload = _public_result(row)
    run = db.get(ReconciliationRun, row.run_id)
    row_indexes = {
        ("erp", index) for index in payload.get("erp_row_indexes") or []
    } | {("dian", index) for index in payload.get("dian_row_indexes") or []}
    validation_errors = run.validation_errors if run is not None else []
    payload["validation_errors"] = [
        error
        for error in validation_errors or []
        if (error.get("source"), error.get("row_index")) in row_indexes
    ]
    return payload


def build_reconciliation_report(
    db: Session,
    user: User,
    reconciliation_id: uuid.UUID,
    run_id: uuid.UUID | None = None,
) -> tuple[str, bytes]:
    reconciliation = get_reconciliation(db, user, reconciliation_id)
    run = _completed_run(db, reconciliation, run_id)
    company = get_company(db, user, reconciliation.company_id)
    results = db.scalars(
        select(ReconciliationResult)
        .where(ReconciliationResult.run_id == run.id)
        .order_by(ReconciliationResult.document_key)
    ).all()
    context = {
        "company_name": company.legal_name,
        "tax_id": company.tax_id,
        "period_start": reconciliation.period_start.isoformat(),
        "period_end": reconciliation.period_end.isoformat(),
        "executed_at": run.executed_at.isoformat() if run.executed_at else None,
        "erp_filename": _require_file(run, "erp").original_filename,
        "dian_filename": _require_file(run, "dian").original_filename,
        "rules": run.rules,
        "summary": run.summary,
    }
    content = build_report(
        context,
        [row.payload for row in results],
        reconciliation.validation_errors or [],
    )
    filename = f"conciliacion-{reconciliation.period_start.isoformat()}-{reconciliation.id}.xlsx"
    return filename, content


def to_read_model(db: Session, reconciliation: Reconciliation) -> ReconciliationRead:
    company = db.get(Company, reconciliation.company_id)
    run = _latest_run(db, reconciliation)
    run_count = db.scalar(
        select(func.count()).select_from(ReconciliationRun).where(ReconciliationRun.reconciliation_id == reconciliation.id)
    ) or 0
    progress_rows = db.execute(
        select(ReconciliationResult.primary_category, ReconciliationResult.review_status).where(
            ReconciliationResult.run_id == run.id
        )
    ).all()
    return ReconciliationRead(
        id=reconciliation.id,
        company_id=reconciliation.company_id,
        company_name=company.legal_name if company else "",
        period_start=reconciliation.period_start,
        period_end=reconciliation.period_end,
        status=run.status,
        tolerance=format_decimal(Decimal(str(run.tolerance))),
        erp_mapping=run.erp_mapping,
        dian_mapping=run.dian_mapping,
        summary=run.summary,
        rules=run.rules,
        executed_at=run.executed_at,
        created_at=reconciliation.created_at,
        current_run_id=run.id,
        run_count=int(run_count),
        review_progress=build_review_progress([(category, status) for category, status in progress_rows]),
        files=[
            FileRead(
                id=item.id,
                source=item.source,
                original_filename=item.original_filename,
                detected_type=item.detected_type,
                encoding=item.encoding,
                size_bytes=item.size_bytes,
                row_count=item.row_count,
                warnings=item.warnings or [],
            )
            for item in run.files
        ],
    )


def _public_result(row: ReconciliationResult) -> dict:
    payload = dict(row.payload)
    payload["id"] = str(row.id)
    payload["run_id"] = str(row.run_id)
    payload["review_status"] = row.review_status
    payload["total_delta"] = format_decimal(row.total_delta) if row.total_delta is not None else None
    return payload


def _preview_source(run: ReconciliationRun, source: str) -> SourcePreview | None:
    stored = _file_or_none(run, source)
    if stored is None:
        return None
    settings = get_settings()
    table = read_tabular(
        resolve_private_file(stored.storage_path).read_bytes(),
        stored.original_filename,
        max_rows=settings.max_rows_per_file,
    )
    return SourcePreview(
        source=source,
        filename=stored.original_filename,
        headers=table.headers,
        suggestions=suggest_columns(table.headers),
        sample_rows=table.rows[:5],
        warnings=table.warnings,
    )


def _validate_mapping(mapping: ColumnMapping, headers: list[str]) -> None:
    used: list[str] = []
    for column in mapping.model_dump().values():
        if column is None:
            continue
        if column not in headers:
            raise AppError("unknown_column", f"La columna «{column}» no existe en el archivo.", 422)
        if column in used:
            raise AppError("duplicate_column", "Una misma columna no puede asignarse a dos campos.", 422)
        used.append(column)


def _require_file(run: ReconciliationRun, source: str) -> ReconciliationFile:
    stored = _file_or_none(run, source)
    if stored is None:
        raise AppError("file_required", f"Falta el archivo de {source}.", 409)
    return stored


def _file_or_none(run: ReconciliationRun, source: str) -> ReconciliationFile | None:
    return next((item for item in run.files if item.source == source), None)


def _latest_run(db: Session, reconciliation: Reconciliation) -> ReconciliationRun:
    run = db.scalar(
        select(ReconciliationRun)
        .where(ReconciliationRun.reconciliation_id == reconciliation.id)
        .options(selectinload(ReconciliationRun.files))
        .order_by(ReconciliationRun.sequence.desc())
        .limit(1)
    )
    if run is None:
        raise AppError("run_missing", "La conciliación no tiene una ejecución asociada.", 500)
    return run


def _mutable_run(db: Session, reconciliation: Reconciliation) -> ReconciliationRun:
    run = _latest_run(db, reconciliation)
    if run.status == "running":
        raise AppError("conflict", "No se puede modificar la conciliación mientras se ejecuta.", 409)
    if run.status in {"completed", "failed"}:
        return _spawn_run(db, reconciliation, run)
    return run


def _spawn_run(db: Session, reconciliation: Reconciliation, previous: ReconciliationRun) -> ReconciliationRun:
    copied_files: list[ReconciliationFile] = []
    for stored in previous.files:
        content = resolve_private_file(stored.storage_path).read_bytes()
        relative_path = save_private_file(reconciliation.id, stored.source, stored.original_filename, content)
        copied_files.append(
            ReconciliationFile(
                reconciliation_id=reconciliation.id,
                source=stored.source,
                original_filename=stored.original_filename,
                detected_type=stored.detected_type,
                encoding=stored.encoding,
                size_bytes=stored.size_bytes,
                sha256=stored.sha256,
                storage_path=relative_path,
                row_count=stored.row_count,
                headers=list(stored.headers or []),
                warnings=list(stored.warnings or []),
            )
        )
    sources = {item.source for item in copied_files}
    has_mappings = bool(previous.erp_mapping and previous.dian_mapping)
    if has_mappings and {"erp", "dian"} <= sources:
        status = "mapping_confirmed"
    elif {"erp", "dian"} <= sources:
        status = "files_uploaded"
    elif copied_files:
        status = "draft"
    else:
        status = "draft"
    run = ReconciliationRun(
        reconciliation_id=reconciliation.id,
        sequence=previous.sequence + 1,
        status=status,
        tolerance=previous.tolerance,
        erp_mapping=deepcopy(previous.erp_mapping),
        dian_mapping=deepcopy(previous.dian_mapping),
    )
    db.add(run)
    db.flush()
    for stored in copied_files:
        stored.run_id = run.id
        db.add(stored)
    db.flush()
    db.expire(run, ["files"])
    _project(reconciliation, run)
    _event(
        db,
        reconciliation,
        run,
        "run_opened",
        "Se abrió una ejecución nueva. La ejecución anterior permanece sin cambios.",
        {"previous_run_id": str(previous.id), "sequence": run.sequence},
    )
    return run


def _completed_run(db: Session, reconciliation: Reconciliation, run_id: uuid.UUID | None) -> ReconciliationRun:
    statement = (
        select(ReconciliationRun)
        .where(ReconciliationRun.reconciliation_id == reconciliation.id)
        .options(selectinload(ReconciliationRun.files))
    )
    if run_id is not None:
        statement = statement.where(ReconciliationRun.id == run_id)
    else:
        statement = statement.where(ReconciliationRun.status == "completed").order_by(ReconciliationRun.sequence.desc())
    run = db.scalar(statement.limit(1))
    if run is None:
        if run_id is not None:
            raise AppError("not_found", "La ejecución no existe o no tienes acceso.", 404)
        raise AppError("report_not_ready", "El informe está disponible cuando la ejecución ha terminado.", 409)
    if run.status != "completed" or run.summary is None:
        raise AppError("report_not_ready", "El informe está disponible cuando la ejecución ha terminado.", 409)
    return run


def _project(reconciliation: Reconciliation, run: ReconciliationRun) -> None:
    reconciliation.status = run.status
    reconciliation.tolerance = run.tolerance
    reconciliation.erp_mapping = run.erp_mapping
    reconciliation.dian_mapping = run.dian_mapping
    reconciliation.summary = run.summary
    reconciliation.rules = run.rules
    reconciliation.validation_errors = run.validation_errors
    reconciliation.executed_at = run.executed_at


def _clear_draft_output(db: Session, run: ReconciliationRun) -> None:
    if run.status in {"completed", "failed"}:
        raise AppError("sealed_run", "Una ejecución terminada no se modifica.", 409)
    db.execute(delete(ReconciliationResult).where(ReconciliationResult.run_id == run.id))
    run.summary = None
    run.rules = None
    run.validation_errors = None
    run.executed_at = None


def _company_ids(db: Session, user: User):
    return select(CompanyMembership.company_id).where(CompanyMembership.user_id == user.id)


def _event(
    db: Session,
    reconciliation: Reconciliation,
    run: ReconciliationRun,
    event_type: str,
    message: str,
    details: dict | None = None,
) -> None:
    db.add(
        ReconciliationEvent(
            reconciliation_id=reconciliation.id,
            run_id=run.id,
            event_type=event_type,
            message=message,
            details=details,
        )
    )


def _mark_failed(db: Session, reconciliation_id: uuid.UUID, run_id: uuid.UUID, message: str) -> None:
    db.rollback()
    reconciliation = db.get(Reconciliation, reconciliation_id)
    run = db.get(ReconciliationRun, run_id)
    if reconciliation is None or run is None:
        return
    run.status = "failed"
    _project(reconciliation, run)
    _event(db, reconciliation, run, "run_failed", message)
    db.commit()
