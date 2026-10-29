from decimal import Decimal

from app.modules.reconciliations.engine.normalization import (
    MONEY_FIELDS,
    format_decimal,
    normalize_date,
    normalize_document_number,
    normalize_money,
    normalize_tax_id,
)
from app.modules.reconciliations.engine.types import NormalizedRecord, QualityIssue


def mapping_fields(mapping: dict[str, str | None]) -> list[str]:
    return [field for field, column in mapping.items() if column]


def normalize_rows(
    rows: list[dict[str, str | None]],
    mapping: dict[str, str | None],
) -> list[NormalizedRecord]:
    return [normalize_row(index, row, mapping) for index, row in enumerate(rows)]


def normalize_row(
    row_index: int,
    raw_row: dict[str, str | None],
    mapping: dict[str, str | None],
) -> NormalizedRecord:
    original: dict[str, str | None] = {}
    values: dict[str, str | None] = {}
    money: dict[str, Decimal | None] = {}
    issues: list[QualityIssue] = []
    parsed_date = None

    for field, column in mapping.items():
        if not column:
            continue
        raw = _cell(raw_row.get(column))
        original[field] = raw
        if field == "document_number":
            value, field_issues = normalize_document_number(raw)
            issues.extend(field_issues)
            values[field] = value
        elif field == "third_party_id":
            value, field_issues = normalize_tax_id(raw)
            issues.extend(field_issues)
            values[field] = value
        elif field == "issue_date":
            value, field_issues = normalize_date(raw)
            issues.extend(field_issues)
            parsed_date = value
            values[field] = value.isoformat() if value else None
        elif field in MONEY_FIELDS:
            value, field_issues = normalize_money(raw)
            retargeted = [
                QualityIssue(field, issue.code, issue.message, issue.severity)
                for issue in field_issues
            ]
            issues.extend(retargeted)
            money[field] = value
            values[field] = format_decimal(value) if value is not None else None

    return NormalizedRecord(
        row_index=row_index,
        original_row={key: _cell(value) for key, value in raw_row.items()},
        original=original,
        values=values,
        money=money,
        issue_date=parsed_date,
        issues=issues,
    )


def _cell(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null"}:
        return None
    return text
