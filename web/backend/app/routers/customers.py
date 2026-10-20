from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import ensure_self, get_current_customer
from ..database import get_db
from ..models import Customer, Transaction
from ..schemas import AccountOut, CustomerOut, ProfileOut, TransactionOut

router = APIRouter(prefix="/customers", tags=["customers"])


def get_customer_or_404(db: Session, customer_number: str) -> Customer:
    customer = db.get(Customer, customer_number)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy khách hàng")
    return customer


@router.get("/{customer_number}", response_model=CustomerOut)
def get_customer(customer_number: str, db: Session = Depends(get_db), current: str = Depends(get_current_customer)):
    ensure_self(customer_number, current)
    c = get_customer_or_404(db, customer_number)
    profile = ProfileOut(
        customer_number=c.customer_number,
        full_name=c.full_name,
        segment=c.segment,
        age=c.age,
        tenure_days=(date.today() - c.joined_date).days,
        email=c.email,
        phone=c.phone,
    )
    return CustomerOut(profile=profile, accounts=[AccountOut.model_validate(a) for a in c.accounts])


@router.get("/{customer_number}/transactions", response_model=list[TransactionOut])
def get_transactions(
    customer_number: str,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current: str = Depends(get_current_customer),
):
    ensure_self(customer_number, current)
    get_customer_or_404(db, customer_number)
    rows = db.scalars(
        select(Transaction)
        .where(Transaction.customer_number == customer_number)
        .order_by(Transaction.date.desc())
        .limit(limit)
    ).all()
    return rows
