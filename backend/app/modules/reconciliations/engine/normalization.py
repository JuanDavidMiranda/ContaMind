import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.modules.reconciliations.engine.types import QualityIssue

MONEY_FIELDS = ("base_amount", "tax_amount", "total_amount")
COMPARABLE_FIELDS = (
    "document_number",
    "third_party_id",
    "issue_date",
    "base_amount",
    "tax_amount",
    "total_amount",
)

_CURRENCY_TOKENS = ("COP", "$", "€", "£")


def format_decimal(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-", "-0"}:
        return "0"
    return text


def normalize_document_number(raw: str | None) -> tuple[str | None, list[QualityIssue]]:
    if raw is None or str(raw).strip() == "":
        return None, [
            QualityIssue(
                "document_number",
                "empty_document_number",
                "El número de documento está vacío.",
            )
        ]
    text = re.sub(r"\s+", "", str(raw)).upper()
    if re.search(r"[\x00-\x1f]", text):
        return None, [
            QualityIssue(
                "document_number",
                "invalid_document_number",
                "El número de documento contiene caracteres no válidos.",
            )
        ]
    return text, []


def normalize_tax_id(raw: str | None) -> tuple[str | None, list[QualityIssue]]:
    if raw is None or str(raw).strip() == "":
        return None, [
            QualityIssue(
                "third_party_id",
                "empty_field",
                "La identificación del tercero está vacía.",
                "warning",
            )
        ]
    text = re.sub(r"\s+", "", str(raw)).upper().replace(".", "")
    if text.startswith("NIT"):
        remainder = text[3:]
        if re.fullmatch(r"\d+(-\d+)?", remainder):
            text = remainder
    if re.search(r"[\x00-\x1f]", text) or text == "":
        return None, [
            QualityIssue(
                "third_party_id",
                "invalid_tax_id",
                "La identificación del tercero no pudo normalizarse.",
            )
        ]
    return text, []


def normalize_date(raw: str | None) -> tuple[date | None, list[QualityIssue]]:
    if raw is None or str(raw).strip() == "":
        return None, [
            QualityIssue(
                "issue_date",
                "empty_field",
                "La fecha de emisión está vacía.",
                "warning",
            )
        ]
    if isinstance(raw, datetime):
        return raw.date(), []
    if isinstance(raw, date):
        return raw, []

    text = str(raw).strip()
    iso_match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})(?:[T ].*)?", text)
    if iso_match:
        return _safe_date(
            int(iso_match.group(1)),
            int(iso_match.group(2)),
            int(iso_match.group(3)),
        )

    regional = re.fullmatch(r"(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})", text)
    if regional:
        first = int(regional.group(1))
        second = int(regional.group(2))
        year = int(regional.group(3))
        if first > 12 and second > 12:
            return None, [_invalid_date()]
        if first > 12:
            return _safe_date(year, second, first)
        if second > 12:
            return _safe_date(year, first, second)
        return None, [
            QualityIssue(
                "issue_date",
                "ambiguous_date",
                "La fecha puede leerse como día/mes o como mes/día. No se eligió una interpretación.",
            )
        ]
    return None, [_invalid_date()]


def normalize_money(raw: str | None) -> tuple[Decimal | None, list[QualityIssue]]:
    if raw is None or str(raw).strip() == "":
        return None, [
            QualityIssue(
                None,
                "empty_field",
                "El importe está vacío.",
                "warning",
            )
        ]
    if isinstance(raw, Decimal):
        return raw, []
    if isinstance(raw, bool) or isinstance(raw, float):
        return None, [_invalid_amount("El importe llegó como número de punto flotante y no se comparó.")]
    if isinstance(raw, int):
        return Decimal(raw), []

    text = str(raw).strip().replace("\u00a0", "").replace(" ", "")
    for token in _CURRENCY_TOKENS:
        text = text.replace(token, "")
    if text == "":
        return None, [_invalid_amount()]

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]
    if text.startswith("+"):
        text = text[1:]
    elif text.startswith("-"):
        negative = True
        text = text[1:]
    if text == "" or not re.fullmatch(r"[\d.,]+", text):
        return None, [_invalid_amount()]

    has_dot = "." in text
    has_comma = "," in text
    if has_dot and has_comma:
        if text.rfind(".") > text.rfind(","):
            decimal_sep, thousands_sep = ".", ","
        else:
            decimal_sep, thousands_sep = ",", "."
        without_thousands = text.replace(thousands_sep, "")
        groups = without_thousands.split(decimal_sep)
        if len(groups) != 2 or not groups[0].isdigit() or not groups[1].isdigit():
            return None, [_invalid_amount()]
        normalized = groups[0] + "." + groups[1]
    elif has_dot or has_comma:
        separator = "." if has_dot else ","
        parts = text.split(separator)
        if not all(part.isdigit() and part != "" for part in parts):
            return None, [_invalid_amount()]
        if len(parts) > 2:
            if all(len(part) == 3 for part in parts[1:]):
                normalized = "".join(parts)
            else:
                return None, [_invalid_amount()]
        else:
            left, right = parts
            if len(right) in {1, 2}:
                normalized = left + "." + right
            elif len(right) == 3:
                return None, [
                    QualityIssue(
                        None,
                        "ambiguous_amount",
                        "El importe tiene un separador y tres dígitos finales. Puede ser miles o decimales, así que no se interpretó.",
                    )
                ]
            else:
                return None, [_invalid_amount()]
    else:
        normalized = text

    try:
        value = Decimal(normalized)
    except InvalidOperation:
        return None, [_invalid_amount()]
    if negative:
        value = -value
    return value, []


def fold_header(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.strip().lower())
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _safe_date(year: int, month: int, day: int) -> tuple[date | None, list[QualityIssue]]:
    try:
        return date(year, month, day), []
    except ValueError:
        return None, [_invalid_date()]


def _invalid_date() -> QualityIssue:
    return QualityIssue(
        "issue_date",
        "invalid_date",
        "La fecha de emisión no tiene un formato reconocible.",
    )


def _invalid_amount(message: str | None = None) -> QualityIssue:
    return QualityIssue(
        None,
        "invalid_amount",
        message or "El importe no pudo interpretarse.",
    )
