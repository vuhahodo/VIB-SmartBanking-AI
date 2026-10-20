from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings

_bearer = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(customer_number: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode({"sub": customer_number, "exp": expire}, settings.JWT_SECRET, algorithm=ALGORITHM)


def get_current_customer(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    """Dependency: trả về mã khách hàng từ JWT, 401 nếu thiếu/không hợp lệ."""
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Chưa đăng nhập")
    try:
        payload = jwt.decode(creds.credentials, settings.JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Phiên đăng nhập đã hết hạn")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token không hợp lệ")
    return payload["sub"]


def ensure_self(customer_number: str, current: str) -> None:
    """Khách hàng chỉ được truy cập dữ liệu của chính mình."""
    if customer_number != current:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Không có quyền truy cập dữ liệu khách hàng khác")
