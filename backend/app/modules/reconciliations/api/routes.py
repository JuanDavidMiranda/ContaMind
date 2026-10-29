import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.modules.identity.models import User
from app.modules.reconciliations.application.schemas import (
    ColumnsPreview,
    MappingConfirmation,
    ReconciliationCreate,
    ReconciliationRead,
    ResultPage,
    UserRead,
)
from app.modules.reconciliations.application.service import (
    build_reconciliation_report,
    confirm_mapping,
    create_reconciliation,
    get_reconciliation,
    get_result,
    list_reconciliations,
    list_results,
    preview_columns,
    run_reconciliation,
    to_read_model,
    upload_file,
)

router = APIRouter(tags=["reconciliations"])


@router.get("/me", response_model=UserRead)
def current_user(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        authentication="development-local-user",
    )


@router.get("/reconciliations", response_model=list[ReconciliationRead])
def index(
    company_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ReconciliationRead]:
    return [to_read_model(db, item) for item in list_reconciliations(db, user, company_id)]


@router.post("/reconciliations", response_model=ReconciliationRead, status_code=201)
def create(
    payload: ReconciliationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReconciliationRead:
    return to_read_model(db, create_reconciliation(db, user, payload))


@router.get("/reconciliations/{reconciliation_id}", response_model=ReconciliationRead)
def detail(
    reconciliation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReconciliationRead:
    return to_read_model(db, get_reconciliation(db, user, reconciliation_id))


@router.post("/reconciliations/{reconciliation_id}/files", response_model=ReconciliationRead)
async def upload(
    reconciliation_id: uuid.UUID,
    source: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReconciliationRead:
    content = await file.read()
    upload_file(db, user, reconciliation_id, source, file.filename or "", content)
    return to_read_model(db, get_reconciliation(db, user, reconciliation_id))


@router.get("/reconciliations/{reconciliation_id}/columns", response_model=ColumnsPreview)
def columns(
    reconciliation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ColumnsPreview:
    return preview_columns(db, user, reconciliation_id)


@router.put("/reconciliations/{reconciliation_id}/mapping", response_model=ReconciliationRead)
def mapping(
    reconciliation_id: uuid.UUID,
    payload: MappingConfirmation,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReconciliationRead:
    return to_read_model(db, confirm_mapping(db, user, reconciliation_id, payload.erp, payload.dian))


@router.post("/reconciliations/{reconciliation_id}/run", response_model=ReconciliationRead)
def run(
    reconciliation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReconciliationRead:
    return to_read_model(db, run_reconciliation(db, user, reconciliation_id))


@router.get("/reconciliations/{reconciliation_id}/results", response_model=ResultPage)
def results(
    reconciliation_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    category: str | None = None,
    q: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResultPage:
    return list_results(
        db,
        user,
        reconciliation_id,
        page=page,
        page_size=page_size,
        category=category,
        query=q,
    )


@router.get("/reconciliations/{reconciliation_id}/results/{result_id}")
def result_detail(
    reconciliation_id: uuid.UUID,
    result_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return get_result(db, user, reconciliation_id, result_id)


@router.get("/reconciliations/{reconciliation_id}/report")
def report(
    reconciliation_id: uuid.UUID,
    run_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    filename, content = build_reconciliation_report(db, user, reconciliation_id, run_id)
    if not content:
        raise AppError("empty_report", "El informe no tiene contenido.", 500)
    encoded = quote(filename)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )
