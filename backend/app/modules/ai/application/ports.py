from typing import Protocol

from pydantic import BaseModel, Field


class DifferenceContext(BaseModel):
    document_key: str
    primary_category: str
    flags: list[str]
    messages: list[str]
    differences: list[dict]
    disclaimer: str = (
        "Una explicación generada no convierte una discrepancia en un error tributario confirmado."
    )


class AnalysisRequest(BaseModel):
    reconciliation_id: str
    differences: list[DifferenceContext] = Field(default_factory=list)


class AnalysisNote(BaseModel):
    document_key: str
    narrative: str
    source: str


class AnalysisResponse(BaseModel):
    notes: list[AnalysisNote] = Field(default_factory=list)
    provider: str


class DifferenceAnalyzer(Protocol):
    """Contrato para un analizador futuro. La conciliación no lo invoca."""

    def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        """Devuelve notas explicativas, sin modificar categorías ni importes."""


class UnavailableDifferenceAnalyzer:
    """Implementación explícita mientras no haya un proveedor configurado."""

    provider_name = "unavailable"

    def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        return AnalysisResponse(notes=[], provider=self.provider_name)
