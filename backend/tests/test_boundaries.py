from pathlib import Path


def test_reconciliation_engine_has_no_framework_or_ai_imports():
    engine_dir = Path(__file__).resolve().parents[1] / "app" / "modules" / "reconciliations" / "engine"
    forbidden = ("fastapi", "sqlalchemy", "langgraph", "ollama", "openai")
    for path in engine_dir.glob("*.py"):
        source = path.read_text(encoding="utf-8").lower()
        for name in forbidden:
            assert f"import {name}" not in source
            assert f"from {name}" not in source


def test_ai_port_does_not_run_during_reconciliation():
    from app.modules.ai.application.ports import AnalysisRequest, UnavailableDifferenceAnalyzer

    response = UnavailableDifferenceAnalyzer().analyze(AnalysisRequest(reconciliation_id="synthetic"))
    assert response.provider == "unavailable"
    assert response.notes == []
