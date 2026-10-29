from app.modules.reconciliations.engine.normalization import fold_header

FIELD_SYNONYMS: dict[str, tuple[str, ...]] = {
    "document_number": (
        "numero de factura",
        "numero factura",
        "nro factura",
        "no factura",
        "num factura",
        "factura",
        "numero de documento",
        "numero documento",
        "nro documento",
        "no documento",
        "documento",
        "consecutivo",
        "invoice",
        "invoice number",
        "document number",
        "numero",
        "nro",
    ),
    "third_party_id": (
        "identificacion del tercero",
        "identificacion tercero",
        "documento del tercero",
        "nit del emisor",
        "nit emisor",
        "nit del cliente",
        "nit cliente",
        "nit del proveedor",
        "nit proveedor",
        "nit",
        "identificacion",
        "cedula",
        "tax id",
        "tercero",
    ),
    "issue_date": (
        "fecha de emision",
        "fecha emision",
        "fecha de la factura",
        "fecha factura",
        "fecha del documento",
        "fecha documento",
        "issue date",
        "fecha",
    ),
    "base_amount": (
        "base gravable",
        "base de la operacion",
        "valor base",
        "subtotal",
        "base",
        "neto",
    ),
    "tax_amount": (
        "valor iva",
        "iva",
        "impuesto",
        "tax",
    ),
    "total_amount": (
        "valor total",
        "total factura",
        "gran total",
        "total documento",
        "total",
    ),
}

FIELD_PRIORITY = (
    "document_number",
    "third_party_id",
    "issue_date",
    "total_amount",
    "tax_amount",
    "base_amount",
)


def suggest_columns(headers: list[str]) -> dict[str, dict]:
    folded_headers = [(header, fold_header(header)) for header in headers]
    candidates: list[tuple[float, int, str, str]] = []
    for field_index, field in enumerate(FIELD_PRIORITY):
        for header, folded in folded_headers:
            score = _score(folded, FIELD_SYNONYMS[field])
            if score > 0:
                candidates.append((score, -field_index, field, header))
    candidates.sort(reverse=True)

    assigned_fields: set[str] = set()
    assigned_headers: set[str] = set()
    suggestions: dict[str, dict] = {}
    for score, _priority, field, header in candidates:
        if field in assigned_fields or header in assigned_headers:
            continue
        assigned_fields.add(field)
        assigned_headers.add(header)
        suggestions[field] = {
            "column": header,
            "confidence": round(score, 2),
            "reason": "El nombre de la columna se parece a un sinónimo conocido.",
        }
    for field in FIELD_SYNONYMS:
        suggestions.setdefault(
            field,
            {
                "column": None,
                "confidence": 0,
                "reason": "No se encontró una columna con un nombre reconocible.",
            },
        )
    return suggestions


def _score(folded_header: str, synonyms: tuple[str, ...]) -> float:
    if not folded_header:
        return 0
    best = 0.0
    for synonym in synonyms:
        if folded_header == synonym:
            best = max(best, 1.0)
        elif f" {synonym} " in f" {folded_header} ":
            best = max(best, 0.75 + min(len(synonym), 40) / 400)
    return best
