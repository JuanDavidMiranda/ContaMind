from decimal import Decimal

from app.modules.reconciliations.engine.normalization import (
    normalize_date,
    normalize_document_number,
    normalize_money,
    normalize_tax_id,
)
from app.modules.reconciliations.engine.reconcile import reconcile

FULL = {
    "document_number": "factura",
    "third_party_id": "nit",
    "issue_date": "fecha",
    "base_amount": "base",
    "tax_amount": "iva",
    "total_amount": "total",
}


def mapping(*active: str) -> dict[str, str | None]:
    selected = set(active or FULL.keys())
    return {field: column if field in selected else None for field, column in FULL.items()}


def invoice(**overrides) -> dict[str, str | None]:
    row = {
        "factura": "FV001",
        "nit": "900123456-1",
        "fecha": "2026-01-15",
        "base": "1000.00",
        "iva": "190.00",
        "total": "1190.00",
    }
    row.update(overrides)
    return row


def by_key(outcome):
    return {row.document_key: row for row in outcome.results}


def test_matching_records_and_different_row_order():
    erp = [invoice(factura="FV002"), invoice(factura="FV001")]
    dian = [invoice(factura="FV001"), invoice(factura="FV002", nit="900.123.456-1")]
    outcome = reconcile(erp, dian, mapping(), mapping())
    assert outcome.summary["matched"] == 2
    assert outcome.summary["result_count"] == 2
    assert by_key(outcome)["FV001"].primary_category == "MATCHED"
    assert by_key(outcome)["FV002"].primary_category == "MATCHED"


def test_missing_documents_on_each_source():
    outcome = reconcile(
        [invoice(factura="SOLOERP")],
        [invoice(factura="SOLODIAN")],
        mapping(),
        mapping(),
    )
    results = by_key(outcome)
    assert results["SOLOERP"].primary_category == "MISSING_IN_DIAN"
    assert results["SOLODIAN"].primary_category == "MISSING_IN_ERP"
    assert outcome.summary["missing_in_dian"] == 1
    assert outcome.summary["missing_in_erp"] == 1


def test_value_date_and_third_party_differences_keep_every_flag():
    outcome = reconcile(
        [invoice()],
        [invoice(nit="800111222-3", fecha="2026-01-16", base="900", iva="171", total="1071")],
        mapping(),
        mapping(),
    )
    result = outcome.results[0]
    assert result.primary_category == "THIRD_PARTY_MISMATCH"
    assert result.flags == [
        "THIRD_PARTY_MISMATCH",
        "VALUE_MISMATCH",
        "DATE_MISMATCH",
    ]
    fields = {item.field for item in result.differences}
    assert fields == {"third_party_id", "issue_date", "base_amount", "tax_amount", "total_amount"}
    total = next(item for item in result.differences if item.field == "total_amount")
    assert total.delta == "-119"
    assert "incumplimiento tributario" in result.messages[-1]


def test_value_difference_has_priority_over_date():
    outcome = reconcile(
        [invoice()],
        [invoice(fecha="2026-01-20", total="1191.00")],
        mapping(),
        mapping(),
    )
    result = outcome.results[0]
    assert result.primary_category == "VALUE_MISMATCH"
    assert "DATE_MISMATCH" in result.flags


def test_exact_duplicates_are_counted_once_and_flagged():
    repeated = invoice()
    outcome = reconcile([repeated, dict(repeated)], [invoice()], mapping(), mapping())
    assert outcome.summary["result_count"] == 1
    result = outcome.results[0]
    assert result.primary_category == "MATCHED"
    assert result.duplicate_kind == "exact"
    assert "POSSIBLE_DUPLICATE" in result.flags
    assert result.erp_row_indexes == [0, 1]
    assert outcome.summary["duplicate_groups"] == 1
    assert outcome.summary["matched"] == 1


def test_conflicting_duplicates_are_not_paired_automatically():
    outcome = reconcile(
        [invoice(total="1190.00"), invoice(total="1500.00")],
        [invoice()],
        mapping(),
        mapping(),
    )
    assert len(outcome.results) == 1
    result = outcome.results[0]
    assert result.primary_category == "REQUIRES_REVIEW"
    assert result.duplicate_kind == "conflicting"
    assert result.differences == []
    assert "POSSIBLE_DUPLICATE" in result.flags


def test_conflicting_duplicate_without_counterpart_stays_in_review():
    outcome = reconcile(
        [invoice(total="10"), invoice(total="20")],
        [],
        mapping(),
        mapping(),
    )
    result = outcome.results[0]
    assert result.primary_category == "REQUIRES_REVIEW"
    assert any("DIAN" in message for message in result.messages)


def test_leading_zeroes_are_preserved_and_do_not_match_a_shorter_number():
    normalized, issues = normalize_document_number("00123")
    assert normalized == "00123"
    assert issues == []
    outcome = reconcile(
        [invoice(factura="00123")],
        [invoice(factura="123")],
        mapping(),
        mapping(),
    )
    assert by_key(outcome)["00123"].primary_category == "MISSING_IN_DIAN"
    assert by_key(outcome)["123"].primary_category == "MISSING_IN_ERP"


def test_document_whitespace_and_case_are_normalized_without_dropping_hyphens():
    left, _ = normalize_document_number(" fv-001 ")
    right, _ = normalize_document_number("FV-001")
    assert left == right == "FV-001"
    other, _ = normalize_document_number("FV001")
    assert other != left


def test_monetary_separators_and_decimal_tolerance():
    grouped, issues = normalize_money("1.234.567,89")
    assert issues == []
    assert grouped == Decimal("1234567.89")
    american, _ = normalize_money("$1,234,567.89")
    assert american == Decimal("1234567.89")
    ambiguous, ambiguous_issues = normalize_money("1.234")
    assert ambiguous is None
    assert ambiguous_issues[0].code == "ambiguous_amount"
    outcome = reconcile(
        [invoice(total="1190,00")],
        [invoice(total="1190.01")],
        mapping(),
        mapping(),
        tolerance=Decimal("0.01"),
    )
    assert outcome.results[0].primary_category == "MATCHED"
    strict = reconcile(
        [invoice(total="1190,00")],
        [invoice(total="1190.01")],
        mapping(),
        mapping(),
        tolerance=Decimal("0"),
    )
    assert strict.results[0].primary_category == "VALUE_MISMATCH"


def test_invalid_and_ambiguous_dates_are_not_guessed():
    ambiguous, ambiguous_issues = normalize_date("01/02/2026")
    assert ambiguous is None
    assert ambiguous_issues[0].code == "ambiguous_date"
    invalid, invalid_issues = normalize_date("31/02/2026")
    assert invalid is None
    assert invalid_issues[0].code == "invalid_date"
    unambiguous, issues = normalize_date("15/01/2026")
    assert issues == []
    assert unambiguous.isoformat() == "2026-01-15"
    outcome = reconcile(
        [invoice(fecha="01/02/2026")],
        [invoice(fecha="2026-02-01")],
        mapping(),
        mapping(),
    )
    assert outcome.results[0].primary_category == "REQUIRES_REVIEW"
    assert outcome.summary["processing_errors"] == 1


def test_unmapped_amount_is_skipped_and_incomplete_rows_are_kept_visible():
    outcome = reconcile(
        [invoice(total="1"), {"factura": " ", "nit": "900123456-1", "fecha": "2026-01-15", "base": "1", "iva": "1", "total": "1"}],
        [invoice(total="2")],
        mapping("document_number", "third_party_id", "issue_date"),
        mapping("document_number", "third_party_id", "issue_date"),
    )
    assert "total_amount" in {item["field"] for item in outcome.rules["skipped_fields"]}
    assert by_key(outcome)["FV001"].primary_category == "MATCHED"
    assert outcome.summary["erp_rows_rejected"] == 1
    assert any(error.document_key is None and error.source == "erp" for error in outcome.validation_errors)


def test_empty_sources_produce_no_results():
    outcome = reconcile([], [], mapping(), mapping())
    assert outcome.results == []
    assert outcome.summary["erp_rows_read"] == 0
    assert outcome.summary["result_count"] == 0


def test_tax_id_keeps_check_digit_and_leading_zeroes():
    normalized, issues = normalize_tax_id("NIT 0900.123.456-1")
    assert issues == []
    assert normalized == "0900123456-1"


def test_float_amounts_are_rejected():
    value, issues = normalize_money(0.1)
    assert value is None
    assert issues[0].code == "invalid_amount"
