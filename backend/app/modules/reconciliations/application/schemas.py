import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_serializer, model_validator


class ReconciliationCreate(BaseModel):
    company_id: uuid.UUID
    period_start: date
    period_end: date
    tolerance: Decimal = Decimal("0")

    @model_validator(mode="after")
    def validate_period(self):
        if self.period_end < self.period_start:
            raise ValueError("El periodo termina antes de comenzar.")
        if self.tolerance < 0:
            raise ValueError("La tolerancia monetaria no puede ser negativa.")
        return self

    @field_serializer("tolerance")
    def serialize_tolerance(self, value: Decimal) -> str:
        return format(value, "f")


class ColumnMapping(BaseModel):
    document_number: str = Field(min_length=1, max_length=255)
    third_party_id: str | None = Field(default=None, max_length=255)
    issue_date: str | None = Field(default=None, max_length=255)
    base_amount: str | None = Field(default=None, max_length=255)
    tax_amount: str | None = Field(default=None, max_length=255)
    total_amount: str | None = Field(default=None, max_length=255)


class MappingConfirmation(BaseModel):
    erp: ColumnMapping
    dian: ColumnMapping


class FileRead(BaseModel):
    id: uuid.UUID
    source: str
    original_filename: str
    detected_type: str
    encoding: str | None
    size_bytes: int
    row_count: int
    warnings: list[str]


class ReconciliationRead(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    company_name: str
    period_start: date
    period_end: date
    status: str
    tolerance: str
    erp_mapping: dict | None
    dian_mapping: dict | None
    summary: dict | None
    rules: dict | None
    executed_at: datetime | None
    created_at: datetime
    files: list[FileRead]
    current_run_id: uuid.UUID
    run_count: int
    review_progress: dict | None = None


class ColumnSuggestion(BaseModel):
    column: str | None
    confidence: float
    reason: str


class SourcePreview(BaseModel):
    source: Literal["erp", "dian"]
    filename: str
    headers: list[str]
    suggestions: dict[str, ColumnSuggestion]
    sample_rows: list[dict[str, str | None]]
    warnings: list[str]


class ColumnsPreview(BaseModel):
    erp: SourcePreview | None
    dian: SourcePreview | None


class ResultPage(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int


class UserRead(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    authentication: str
