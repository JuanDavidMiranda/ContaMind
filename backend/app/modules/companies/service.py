import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.companies.models import Company, CompanyMembership
from app.modules.companies.schemas import CompanyCreate, CompanyUpdate
from app.modules.identity.models import User


def list_companies(db: Session, user: User) -> list[Company]:
    statement = (
        select(Company)
        .join(CompanyMembership, CompanyMembership.company_id == Company.id)
        .where(CompanyMembership.user_id == user.id)
        .order_by(Company.created_at.desc())
    )
    return list(db.scalars(statement).all())


def get_company(db: Session, user: User, company_id: uuid.UUID) -> Company:
    statement = (
        select(Company)
        .join(CompanyMembership, CompanyMembership.company_id == Company.id)
        .where(CompanyMembership.user_id == user.id, Company.id == company_id)
    )
    company = db.scalar(statement)
    if company is None:
        raise AppError("not_found", "La empresa no existe o no tienes acceso.", 404)
    return company


def create_company(db: Session, user: User, payload: CompanyCreate) -> Company:
    company = Company(
        legal_name=payload.legal_name.strip(),
        tax_id=_clean_tax_id(payload.tax_id),
        status="active",
    )
    db.add(company)
    db.flush()
    db.add(CompanyMembership(user_id=user.id, company_id=company.id, role="owner"))
    db.commit()
    db.refresh(company)
    return company


def update_company(db: Session, user: User, company_id: uuid.UUID, payload: CompanyUpdate) -> Company:
    company = get_company(db, user, company_id)
    if payload.legal_name is not None:
        company.legal_name = payload.legal_name.strip()
    if payload.tax_id is not None:
        company.tax_id = _clean_tax_id(payload.tax_id)
    if payload.status is not None:
        company.status = payload.status
    db.commit()
    db.refresh(company)
    return company


def _clean_tax_id(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None
