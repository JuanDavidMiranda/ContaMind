import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.router import router
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging
from app.db.session import get_engine
from app.modules.identity.seed import seed_dev_user

logger = logging.getLogger("contamind.api")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    settings = get_settings()
    settings.resolved_storage_dir().mkdir(parents=True, exist_ok=True)
    with Session(get_engine(), autoflush=False, expire_on_commit=False) as session:
        seed_dev_user(session)
    logger.info("application started env=%s", settings.app_env)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        description=(
            "API del MVP de conciliación de ventas entre ERP y DIAN. "
            "Las diferencias son discrepancias para revisión, no conclusiones tributarias. "
            "La autenticación de este MVP no es apta para producción."
        ),
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(router, prefix="/api/v1")
    application.add_exception_handler(AppError, _app_error)
    application.add_exception_handler(RequestValidationError, _validation_error)
    application.add_exception_handler(SQLAlchemyError, _database_error)
    return application


async def _app_error(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


async def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Los datos enviados no son válidos.",
                "details": _json_safe(exc.errors()),
            }
        },
    )


def _json_safe(value):
    if isinstance(value, BaseException):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


async def _database_error(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("database error")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "database_error",
                "message": "No fue posible completar la operación de datos.",
            }
        },
    )


app = create_app()
