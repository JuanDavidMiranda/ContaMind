"""Motor determinista de conciliación.

No importa FastAPI, SQLAlchemy, LangGraph ni Ollama.
"""

from app.modules.reconciliations.engine.reconcile import reconcile

__all__ = ["reconcile"]
