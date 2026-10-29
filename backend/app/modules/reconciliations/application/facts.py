"""Datos derivados del resultado del motor para consultarlos y revisarlos.

El motor no participa aquí. Estos valores se guardan junto al resultado y no
cambian la clasificación ni los importes originales.
"""

from datetime import date
from decimal import Decimal, InvalidOperation

MISSING_CATEGORIES = {"MISSING_IN_DIAN", "MISSING_IN_ERP"}
PENDING_REVIEW_STATUSES = {"PENDING", "IN_REVIEW"}
REVIEWED_STATUSES = {"JUSTIFIED", "RESOLVED"}
NO_PENDING_LABEL = "No hay documentos pendientes de revisión"


def extract_total_delta(primary_category: str, payload: dict) -> Decimal | None:
    """El delta es nulo cuando falta una fuente. No se sustituye por cero."""
    if primary_category in MISSING_CATEGORIES:
        return None
    if not payload.get("erp_row_indexes") or not payload.get("dian_row_indexes"):
        return None
    for item in payload.get("differences") or []:
        if item.get("field") != "total_amount":
            continue
        return _decimal_or_none(item.get("delta"))
    erp_total = (payload.get("erp_normalized") or {}).get("total_amount")
    dian_total = (payload.get("dian_normalized") or {}).get("total_amount")
    if erp_total is None or dian_total is None:
        return None
    left = _decimal_or_none(erp_total)
    right = _decimal_or_none(dian_total)
    if left is None or right is None:
        return None
    if left == right:
        return Decimal("0")
    return None


def extract_issue_date(payload: dict, source: str) -> date | None:
    raw = (payload.get(f"{source}_normalized") or {}).get("issue_date")
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


def extract_third_party_key(payload: dict) -> str | None:
    values: list[str] = []
    for source in ("erp", "dian"):
        raw = (payload.get(f"{source}_normalized") or {}).get("third_party_id")
        if raw and raw not in values:
            values.append(str(raw))
    if not values:
        return None
    return " ".join(values)[:512]


def build_review_progress(rows: list[tuple[str, str]]) -> dict | None:
    """El avance solo cuenta documentos cuya categoría principal no es MATCHED."""
    if not rows:
        return None
    actionable = [status for category, status in rows if category != "MATCHED"]
    if not actionable:
        return {
            "actionable_count": 0,
            "pending_count": 0,
            "reviewed_count": 0,
            "progress_label": NO_PENDING_LABEL,
        }
    pending = sum(status in PENDING_REVIEW_STATUSES for status in actionable)
    reviewed = sum(status in REVIEWED_STATUSES for status in actionable)
    return {
        "actionable_count": len(actionable),
        "pending_count": pending,
        "reviewed_count": reviewed,
        "progress_label": f"{reviewed} de {len(actionable)} documentos revisados",
    }


def _decimal_or_none(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
