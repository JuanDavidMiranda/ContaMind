from decimal import Decimal

from app.modules.reconciliations.application.facts import (
    NO_PENDING_LABEL,
    build_review_progress,
    extract_total_delta,
)


def test_missing_documents_have_null_delta_and_matches_can_be_zero():
    missing = extract_total_delta(
        "MISSING_IN_DIAN",
        {"differences": [], "erp_row_indexes": [0], "dian_row_indexes": [], "erp_normalized": {"total_amount": "10"}},
    )
    absent_in_erp = extract_total_delta(
        "MISSING_IN_ERP",
        {"differences": [], "erp_row_indexes": [], "dian_row_indexes": [0], "dian_normalized": {"total_amount": "10"}},
    )
    matched = extract_total_delta(
        "MATCHED",
        {
            "differences": [],
            "erp_row_indexes": [0],
            "dian_row_indexes": [0],
            "erp_normalized": {"total_amount": "10.00"},
            "dian_normalized": {"total_amount": "10.00"},
        },
    )
    mismatch = extract_total_delta(
        "VALUE_MISMATCH",
        {
            "differences": [{"field": "total_amount", "delta": "-190.00"}],
            "erp_row_indexes": [0],
            "dian_row_indexes": [0],
        },
    )
    assert missing is None
    assert absent_in_erp is None
    assert matched == Decimal("0")
    assert mismatch == Decimal("-190.00")


def test_review_progress_ignores_matches_and_avoids_empty_division():
    assert build_review_progress([]) is None
    only_matches = build_review_progress([("MATCHED", "PENDING"), ("MATCHED", "JUSTIFIED")])
    assert only_matches is not None
    assert only_matches["actionable_count"] == 0
    assert only_matches["progress_label"] == NO_PENDING_LABEL
    mixed = build_review_progress(
        [
            ("MATCHED", "PENDING"),
            ("VALUE_MISMATCH", "JUSTIFIED"),
            ("MISSING_IN_DIAN", "IN_REVIEW"),
            ("DATE_MISMATCH", "RESOLVED"),
            ("THIRD_PARTY_MISMATCH", "PENDING"),
        ]
    )
    assert mixed is not None
    assert mixed["actionable_count"] == 4
    assert mixed["pending_count"] == 2
    assert mixed["reviewed_count"] == 2
    assert mixed["progress_label"] == "2 de 4 documentos revisados"
