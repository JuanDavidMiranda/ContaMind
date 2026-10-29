from fastapi import APIRouter

from app.core.config import get_settings
from app.modules.companies.api import router as companies_router
from app.modules.reconciliations.api.routes import router as reconciliations_router

router = APIRouter()


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
        "production_ready": False,
        "authentication": "development-local-user" if settings.is_development else "not-configured",
    }


router.include_router(companies_router)
router.include_router(reconciliations_router)
