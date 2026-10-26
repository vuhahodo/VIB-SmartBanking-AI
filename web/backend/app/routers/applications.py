import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai_engine import PRODUCTS_BY_CODE
from ..auth import get_current_customer
from ..database import get_db
from ..models import Application
from ..schemas import ApplicationIn, ApplicationOut

router = APIRouter(prefix="/applications", tags=["applications"])


def to_out(a: Application) -> ApplicationOut:
    return ApplicationOut(application_id=a.application_code, status=a.status, product_code=a.product_code, created_at=a.created_at)


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def submit_application(body: ApplicationIn, db: Session = Depends(get_db), current: str = Depends(get_current_customer)):
    if body.product_code not in PRODUCTS_BY_CODE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Sản phẩm không tồn tại")
    app = Application(
        application_code=f"APP-{secrets.token_hex(3).upper()}",
        customer_number=current,
        product_code=body.product_code,
        payload=body.model_dump(mode="json", exclude={"product_code"}),
    )
    db.add(app)
    db.commit()
    return to_out(app)


@router.get("", response_model=list[ApplicationOut])
def my_applications(db: Session = Depends(get_db), current: str = Depends(get_current_customer)):
    rows = db.scalars(
        select(Application).where(Application.customer_number == current).order_by(Application.created_at.desc())
    ).all()
    return [to_out(a) for a in rows]
