from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import create_access_token, verify_password
from ..config import settings
from ..database import get_db
from ..models import Customer
from ..schemas import DemoAccount, LoginIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    customer = db.get(Customer, body.customer_number.strip())
    if customer is None or not verify_password(body.password, customer.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Mã khách hàng hoặc mật khẩu không đúng")
    return TokenOut(access_token=create_access_token(customer.customer_number), customer_number=customer.customer_number)


@router.get("/demo-accounts", response_model=list[DemoAccount])
def demo_accounts(db: Session = Depends(get_db)):
    """Danh sách tài khoản demo cho màn hình đăng nhập (chỉ bật khi DEMO_MODE=true)."""
    if not settings.DEMO_MODE:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    rows = db.scalars(select(Customer).order_by(Customer.customer_number)).all()
    return [DemoAccount(customer_number=c.customer_number, full_name=c.full_name) for c in rows]
