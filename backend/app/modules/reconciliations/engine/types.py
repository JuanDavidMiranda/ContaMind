from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class QualityIssue:
    field: str | None
    code: str
    message: str
    severity: str = "error"

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass
class NormalizedRecord:
    row_index: int
    original_row: dict[str, str | None]
    original: dict[str, str | None]
    values: dict[str, str | None]
    money: dict[str, Decimal | None]
    issue_date: date | None
    issues: list[QualityIssue] = field(default_factory=list)

    @property
    def document_key(self) -> str | None:
        return self.values.get("document_number")

    @property
    def has_blocking_issue(self) -> bool:
        return any(issue.severity == "error" for issue in self.issues)

    @property
    def row_number(self) -> int:
        return self.row_index + 2


@dataclass(frozen=True)
class FieldDifference:
    field: str
    erp_original: str | None
    dian_original: str | None
    erp_normalized: str | None
    dian_normalized: str | None
    delta: str | None = None

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "erp_original": self.erp_original,
            "dian_original": self.dian_original,
            "erp_normalized": self.erp_normalized,
            "dian_normalized": self.dian_normalized,
            "delta": self.delta,
        }


@dataclass
class ReconciliationResultRow:
    document_key: str
    primary_category: str
    flags: list[str]
    differences: list[FieldDifference]
    messages: list[str]
    erp_original: dict[str, str | None] | None
    dian_original: dict[str, str | None] | None
    erp_normalized: dict[str, str | None] | None
    dian_normalized: dict[str, str | None] | None
    erp_row_indexes: list[int]
    dian_row_indexes: list[int]
    erp_candidates: list[dict]
    dian_candidates: list[dict]
    duplicate_kind: str | None

    def to_dict(self) -> dict:
        return {
            "document_key": self.document_key,
            "primary_category": self.primary_category,
            "flags": list(self.flags),
            "differences": [item.to_dict() for item in self.differences],
            "messages": list(self.messages),
            "erp_original": self.erp_original,
            "dian_original": self.dian_original,
            "erp_normalized": self.erp_normalized,
            "dian_normalized": self.dian_normalized,
            "erp_row_indexes": list(self.erp_row_indexes),
            "dian_row_indexes": list(self.dian_row_indexes),
            "erp_row_numbers": [index + 2 for index in self.erp_row_indexes],
            "dian_row_numbers": [index + 2 for index in self.dian_row_indexes],
            "erp_candidates": self.erp_candidates,
            "dian_candidates": self.dian_candidates,
            "duplicate_kind": self.duplicate_kind,
        }


@dataclass
class ValidationErrorRow:
    source: str
    row_index: int
    document_key: str | None
    issues: list[QualityIssue]
    original: dict[str, str | None]
    original_row: dict[str, str | None]

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "row_index": self.row_index,
            "row_number": self.row_index + 2,
            "document_key": self.document_key,
            "issues": [issue.to_dict() for issue in self.issues],
            "original": self.original,
            "original_row": self.original_row,
        }


@dataclass
class EngineOutcome:
    results: list[ReconciliationResultRow]
    validation_errors: list[ValidationErrorRow]
    summary: dict
    rules: dict

    def to_dict(self) -> dict:
        return {
            "results": [row.to_dict() for row in self.results],
            "validation_errors": [row.to_dict() for row in self.validation_errors],
            "summary": self.summary,
            "rules": self.rules,
        }
