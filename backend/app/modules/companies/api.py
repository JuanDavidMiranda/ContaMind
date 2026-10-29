import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.modules.companies.schemas import CompanyCreate, CompanyRead, CompanyUpdate
from app.modules.companies.service import create_company, get_company, list_companies, update_company
from app.modules.identity.models import User

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyRead])
def index(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[CompanyRead]:
    return [CompanyRead.model_validate(company, from_attributes=True) for company in list_companies(db, user)]


@router.post("", response_model=CompanyRead, status_code=201)
def create(
    payload: CompanyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompanyRead:
    return CompanyRead.model_validate(create_company(db, user, payload), from_attributes=True)


@router.get("/{company_id}", response_model=CompanyRead)
def detail(
    company_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompanyRead:
    return CompanyRead.model_validate(get_company(db, user, company_id), from_attributes=True)


@router.patch("/{company_id}", response_model=CompanyRead)
def update(
    company_id: uuid.UUID,
    payload: CompanyUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompanyRead:
    return CompanyRead.model_validate(update_company(db, user, company_id, payload), from_attributes=True)
