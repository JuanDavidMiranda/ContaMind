import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CompanyCreate(BaseModel):
    legal_name: str = Field(min_length=1, max_length=255)
    tax_id: str | None = Field(default=None, max_length=64)


class CompanyUpdate(BaseModel):
    legal_name: str | None = Field(default=None, min_length=1, max_length=255)
    tax_id: str | None = Field(default=None, max_length=64)
    status: Literal["active", "inactive"] | None = None


class CompanyRead(BaseModel):
    id: uuid.UUID
    legal_name: str
    tax_id: str | None
    status: str
    created_at: datetime
