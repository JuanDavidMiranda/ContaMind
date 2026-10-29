from collections import Counter, defaultdict
from decimal import Decimal

from app.modules.reconciliations.engine.normalization import MONEY_FIELDS, format_decimal
from app.modules.reconciliations.engine.records import mapping_fields, normalize_rows
from app.modules.reconciliations.engine.types import (
    EngineOutcome,
    FieldDifference,
    NormalizedRecord,
    ReconciliationResultRow,
    ValidationErrorRow,
)

OPTIONAL_FIELDS = (
    "third_party_id",
    "issue_date",
    "base_amount",
    "tax_amount",
    "total_amount",
)
PRIMARY_PRECEDENCE = (
    "THIRD_PARTY_MISMATCH",
    "VALUE_MISMATCH",
    "DATE_MISMATCH",
)
FLAG_ORDER = (
    "THIRD_PARTY_MISMATCH",
    "VALUE_MISMATCH",
    "DATE_MISMATCH",
    "POSSIBLE_DUPLICATE",
)
FIELD_FLAGS = {
    "third_party_id": "THIRD_PARTY_MISMATCH",
    "issue_date": "DATE_MISMATCH",
    "base_amount": "VALUE_MISMATCH",
    "tax_amount": "VALUE_MISMATCH",
    "total_amount": "VALUE_MISMATCH",
}
FIELD_LABELS = {
    "third_party_id": "identificación del tercero",
    "issue_date": "fecha de emisión",
    "base_amount": "base",
    "tax_amount": "IVA",
    "total_amount": "total",
}
FIELD_DIFF_MESSAGES = {
    "third_party_id": "La identificación del tercero difiere entre las fuentes.",
    "issue_date": "La fecha de emisión difiere entre las fuentes.",
    "base_amount": "La base difiere entre las fuentes.",
    "tax_amount": "El IVA difiere entre las fuentes.",
    "total_amount": "El total difiere entre las fuentes.",
}
DISCLAIMER = (
    "La diferencia identifica una discrepancia para revisión. "
    "No constituye por sí sola un incumplimiento tributario ni un error contable confirmado."
)


def reconcile(
    erp_rows: list[dict[str, str | None]],
    dian_rows: list[dict[str, str | None]],
    erp_mapping: dict[str, str | None],
    dian_mapping: dict[str, str | None],
    tolerance: Decimal | str | int = Decimal("0"),
) -> EngineOutcome:
    tolerance_value = _tolerance(tolerance)
    active_fields, skipped_fields = _comparison_plan(erp_mapping, dian_mapping)
    erp_records = normalize_rows(erp_rows, erp_mapping)
    dian_records = normalize_rows(dian_rows, dian_mapping)
    erp_groups, erp_rejected = _group(erp_records, mapping_fields(erp_mapping))
    dian_groups, dian_rejected = _group(dian_records, mapping_fields(dian_mapping))

    results: list[ReconciliationResultRow] = []
    for document_key in sorted(set(erp_groups) | set(dian_groups)):
        erp_group = erp_groups.get(document_key)
        dian_group = dian_groups.get(document_key)
        if erp_group and dian_group:
            results.append(
                _paired_result(
                    document_key,
                    erp_group,
                    dian_group,
                    active_fields,
                    tolerance_value,
                )
            )
        elif erp_group:
            results.append(_single_source_result(document_key, "erp", erp_group))
        else:
            results.append(_single_source_result(document_key, "dian", dian_group))

    validation_errors = _validation_errors("erp", erp_records) + _validation_errors(
        "dian", dian_records
    )
    summary = _summary(
        erp_records,
        dian_records,
        erp_rejected,
        dian_rejected,
        results,
        validation_errors,
    )
    rules = {
        "tolerance": format_decimal(tolerance_value),
        "match_key": "document_number",
        "active_fields": active_fields,
        "skipped_fields": skipped_fields,
        "primary_precedence": [
            "REQUIRES_REVIEW cuando la correspondencia es ambigua o un valor no puede interpretarse",
            *PRIMARY_PRECEDENCE,
            "MATCHED",
        ],
        "disclaimer": DISCLAIMER,
    }
    return EngineOutcome(
        results=results,
        validation_errors=validation_errors,
        summary=summary,
        rules=rules,
    )


def _tolerance(value: Decimal | str | int) -> Decimal:
    tolerance = value if isinstance(value, Decimal) else Decimal(str(value))
    if tolerance < 0:
        raise ValueError("La tolerancia monetaria no puede ser negativa.")
    return tolerance


def _comparison_plan(
    erp_mapping: dict[str, str | None],
    dian_mapping: dict[str, str | None],
) -> tuple[list[str], list[dict[str, str]]]:
    active: list[str] = []
    skipped: list[dict[str, str]] = []
    for field in OPTIONAL_FIELDS:
        if erp_mapping.get(field) and dian_mapping.get(field):
            active.append(field)
        else:
            skipped.append(
                {
                    "field": field,
                    "reason": (
                        "La columna no está confirmada en ambas fuentes, "
                        "así que esta comparación no se ejecuta."
                    ),
                }
            )
    return active, skipped


def _group(
    records: list[NormalizedRecord],
    mapped_fields: list[str],
) -> tuple[dict[str, tuple[str, list[NormalizedRecord]]], list[NormalizedRecord]]:
    buckets: dict[str, list[NormalizedRecord]] = defaultdict(list)
    rejected: list[NormalizedRecord] = []
    for record in records:
        if record.document_key is None:
            rejected.append(record)
            continue
        buckets[record.document_key].append(record)
    grouped: dict[str, tuple[str, list[NormalizedRecord]]] = {}
    for key, rows in buckets.items():
        grouped[key] = (_duplicate_kind(rows, mapped_fields), rows)
    return grouped, rejected


def _duplicate_kind(rows: list[NormalizedRecord], mapped_fields: list[str]) -> str:
    if len(rows) == 1:
        return "unique"
    if any(row.has_blocking_issue for row in rows):
        return "conflicting"
    comparable = [field for field in mapped_fields if field != "document_number"]
    signatures = [tuple(row.values.get(field) for field in comparable) for row in rows]
    if all(signature == signatures[0] for signature in signatures):
        return "exact"
    return "conflicting"


def _paired_result(
    document_key: str,
    erp_group: tuple[str, list[NormalizedRecord]],
    dian_group: tuple[str, list[NormalizedRecord]],
    active_fields: list[str],
    tolerance: Decimal,
) -> ReconciliationResultRow:
    erp_kind, erp_rows = erp_group
    dian_kind, dian_rows = dian_group
    flags: list[str] = []
    messages: list[str] = []
    duplicate_kind = _combined_duplicate_kind(erp_kind, dian_kind)
    if erp_kind == "exact" or dian_kind == "exact":
        flags.append("POSSIBLE_DUPLICATE")
        messages.append(
            "Hay duplicados exactos con el mismo número de documento. "
            "Se consolidaron para no contar el documento más de una vez."
        )
    if erp_kind == "conflicting" or dian_kind == "conflicting":
        if "POSSIBLE_DUPLICATE" not in flags:
            flags.append("POSSIBLE_DUPLICATE")
        messages.append(
            "Hay varios registros con el mismo número de documento y valores distintos. "
            "No se emparejó automáticamente."
        )
        messages.append(DISCLAIMER)
        return _make_result(
            document_key,
            "REQUIRES_REVIEW",
            flags,
            [],
            messages,
            erp_rows,
            dian_rows,
            "conflicting",
        )

    erp = erp_rows[0]
    dian = dian_rows[0]
    differences: list[FieldDifference] = []
    inconclusive = erp.has_blocking_issue or dian.has_blocking_issue
    if inconclusive:
        messages.append(
            "Uno de los registros tiene un valor que no pudo interpretarse. "
            "La comparación de ese campo no es concluyente."
        )

    for field in active_fields:
        if _field_blocked(erp, field) or _field_blocked(dian, field):
            inconclusive = True
            messages.append(
                f"El campo {FIELD_LABELS[field]} no se comparó porque su valor no es válido o es ambiguo."
            )
            continue
        if not _values_differ(erp, dian, field, tolerance):
            continue
        differences.append(_difference(erp, dian, field))
        flag = FIELD_FLAGS[field]
        if flag not in flags:
            flags.append(flag)
        messages.append(FIELD_DIFF_MESSAGES[field])

    comparison_flags = [flag for flag in flags if flag != "POSSIBLE_DUPLICATE"]
    if inconclusive:
        primary = "REQUIRES_REVIEW"
        messages.append(DISCLAIMER)
    elif not comparison_flags:
        primary = "MATCHED"
        messages.append("Los campos comparables coinciden dentro de la tolerancia configurada.")
    else:
        primary = next(flag for flag in PRIMARY_PRECEDENCE if flag in comparison_flags)
        messages.append(DISCLAIMER)

    return _make_result(
        document_key,
        primary,
        flags,
        differences,
        messages,
        erp_rows,
        dian_rows,
        duplicate_kind,
    )


def _single_source_result(
    document_key: str,
    source: str,
    group: tuple[str, list[NormalizedRecord]] | None,
) -> ReconciliationResultRow:
    if group is None:
        raise ValueError("El grupo de una fuente ausente no puede estar vacío.")
    kind, rows = group
    other_phrase = "la DIAN" if source == "erp" else "el ERP"
    source_phrase = "el ERP" if source == "erp" else "la DIAN"
    flags: list[str] = []
    messages: list[str] = []
    duplicate_kind = None
    if kind == "conflicting":
        primary = "REQUIRES_REVIEW"
        duplicate_kind = "conflicting"
        flags.append("POSSIBLE_DUPLICATE")
        messages.append(
            "Hay varios registros con el mismo número de documento y valores distintos. "
            "No se emparejó automáticamente."
        )
        messages.append(f"Tampoco se encontró una correspondencia en el archivo de {other_phrase}.")
    else:
        primary = "MISSING_IN_DIAN" if source == "erp" else "MISSING_IN_ERP"
        if kind == "exact":
            duplicate_kind = "exact"
            flags.append("POSSIBLE_DUPLICATE")
            messages.append(
                "Hay duplicados exactos. Se consolidaron para no contar el documento más de una vez."
            )
        messages.append(
            f"El documento aparece en {source_phrase} y no se encontró una correspondencia "
            f"válida en el archivo de {other_phrase}."
        )
    messages.append(DISCLAIMER)
    erp_rows = rows if source == "erp" else []
    dian_rows = rows if source == "dian" else []
    return _make_result(
        document_key,
        primary,
        flags,
        [],
        messages,
        erp_rows,
        dian_rows,
        duplicate_kind,
    )


def _combined_duplicate_kind(erp_kind: str, dian_kind: str) -> str | None:
    if "conflicting" in {erp_kind, dian_kind}:
        return "conflicting"
    if "exact" in {erp_kind, dian_kind}:
        return "exact"
    return None


def _field_blocked(record: NormalizedRecord, field: str) -> bool:
    return any(issue.field == field and issue.severity == "error" for issue in record.issues)


def _values_differ(
    erp: NormalizedRecord,
    dian: NormalizedRecord,
    field: str,
    tolerance: Decimal,
) -> bool:
    if field in MONEY_FIELDS:
        left = erp.money.get(field)
        right = dian.money.get(field)
        if left is None and right is None:
            return False
        if left is None or right is None:
            return True
        return abs(left - right) > tolerance
    return erp.values.get(field) != dian.values.get(field)


def _difference(erp: NormalizedRecord, dian: NormalizedRecord, field: str) -> FieldDifference:
    delta = None
    if field in MONEY_FIELDS and erp.money.get(field) is not None and dian.money.get(field) is not None:
        delta = format_decimal(dian.money[field] - erp.money[field])
    return FieldDifference(
        field=field,
        erp_original=erp.original.get(field),
        dian_original=dian.original.get(field),
        erp_normalized=erp.values.get(field),
        dian_normalized=dian.values.get(field),
        delta=delta,
    )


def _make_result(
    document_key: str,
    primary: str,
    flags: list[str],
    differences: list[FieldDifference],
    messages: list[str],
    erp_rows: list[NormalizedRecord],
    dian_rows: list[NormalizedRecord],
    duplicate_kind: str | None,
) -> ReconciliationResultRow:
    ordered_flags = [flag for flag in FLAG_ORDER if flag in flags]
    erp_first = erp_rows[0] if erp_rows else None
    dian_first = dian_rows[0] if dian_rows else None
    return ReconciliationResultRow(
        document_key=document_key,
        primary_category=primary,
        flags=ordered_flags,
        differences=differences,
        messages=messages,
        erp_original=None if erp_first is None else dict(erp_first.original),
        dian_original=None if dian_first is None else dict(dian_first.original),
        erp_normalized=None if erp_first is None else dict(erp_first.values),
        dian_normalized=None if dian_first is None else dict(dian_first.values),
        erp_row_indexes=[row.row_index for row in erp_rows],
        dian_row_indexes=[row.row_index for row in dian_rows],
        erp_candidates=[_candidate(row) for row in erp_rows],
        dian_candidates=[_candidate(row) for row in dian_rows],
        duplicate_kind=duplicate_kind,
    )


def _candidate(row: NormalizedRecord) -> dict:
    return {
        "row_index": row.row_index,
        "row_number": row.row_number,
        "original": dict(row.original),
        "normalized": dict(row.values),
        "original_row": dict(row.original_row),
        "issues": [issue.to_dict() for issue in row.issues],
    }


def _validation_errors(source: str, records: list[NormalizedRecord]) -> list[ValidationErrorRow]:
    errors: list[ValidationErrorRow] = []
    for record in records:
        if not record.issues:
            continue
        errors.append(
            ValidationErrorRow(
                source=source,
                row_index=record.row_index,
                document_key=record.document_key,
                issues=list(record.issues),
                original=dict(record.original),
                original_row=dict(record.original_row),
            )
        )
    return errors


def _summary(
    erp_records: list[NormalizedRecord],
    dian_records: list[NormalizedRecord],
    erp_rejected: list[NormalizedRecord],
    dian_rejected: list[NormalizedRecord],
    results: list[ReconciliationResultRow],
    validation_errors: list[ValidationErrorRow],
) -> dict:
    primary = Counter(row.primary_category for row in results)
    flags = Counter(flag for row in results for flag in row.flags)
    processing_errors = sum(
        1 for row in validation_errors if any(issue.severity == "error" for issue in row.issues)
    )
    return {
        "erp_rows_read": len(erp_records),
        "erp_rows_usable": len(erp_records) - len(erp_rejected),
        "erp_rows_rejected": len(erp_rejected),
        "dian_rows_read": len(dian_records),
        "dian_rows_usable": len(dian_records) - len(dian_rejected),
        "dian_rows_rejected": len(dian_rejected),
        "result_count": len(results),
        "matched": primary["MATCHED"],
        "missing_in_dian": primary["MISSING_IN_DIAN"],
        "missing_in_erp": primary["MISSING_IN_ERP"],
        "value_mismatch_primary": primary["VALUE_MISMATCH"],
        "date_mismatch_primary": primary["DATE_MISMATCH"],
        "third_party_mismatch_primary": primary["THIRD_PARTY_MISMATCH"],
        "requires_review": primary["REQUIRES_REVIEW"],
        "value_mismatch_flags": flags["VALUE_MISMATCH"],
        "date_mismatch_flags": flags["DATE_MISMATCH"],
        "third_party_mismatch_flags": flags["THIRD_PARTY_MISMATCH"],
        "duplicate_groups": flags["POSSIBLE_DUPLICATE"],
        "duplicate_exact_groups": sum(1 for row in results if row.duplicate_kind == "exact"),
        "duplicate_conflicting_groups": sum(
            1 for row in results if row.duplicate_kind == "conflicting"
        ),
        "processing_errors": processing_errors,
        "primary_counts": {
            "MATCHED": primary["MATCHED"],
            "MISSING_IN_DIAN": primary["MISSING_IN_DIAN"],
            "MISSING_IN_ERP": primary["MISSING_IN_ERP"],
            "VALUE_MISMATCH": primary["VALUE_MISMATCH"],
            "DATE_MISMATCH": primary["DATE_MISMATCH"],
            "THIRD_PARTY_MISMATCH": primary["THIRD_PARTY_MISMATCH"],
            "REQUIRES_REVIEW": primary["REQUIRES_REVIEW"],
            "POSSIBLE_DUPLICATE": flags["POSSIBLE_DUPLICATE"],
        },
    }
