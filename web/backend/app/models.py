from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# JSONB trên PostgreSQL, JSON thường trên DB khác (vd. SQLite khi test)
JsonType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Customer(Base):
    __tablename__ = "customers"

    customer_number: Mapped[str] = mapped_column(String(20), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    gender: Mapped[str] = mapped_column(String(10))
    age: Mapped[int]
    email: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20))
    segment: Mapped[str] = mapped_column(String(50), default="Khách hàng cá nhân")
    joined_date: Mapped[date] = mapped_column(Date)
    password_hash: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    accounts: Mapped[list["Account"]] = relationship(back_populates="customer", cascade="all, delete-orphan", order_by="Account.id")
    features: Mapped["CustomerFeature | None"] = relationship(back_populates="customer", cascade="all, delete-orphan")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_number: Mapped[str] = mapped_column(ForeignKey("customers.customer_number", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(60))
    number: Mapped[str] = mapped_column(String(30))
    # NULL với thẻ (không hiển thị số dư)
    balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))

    customer: Mapped[Customer] = relationship(back_populates="accounts")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (Index("ix_transactions_customer_date", "customer_number", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_number: Mapped[str] = mapped_column(ForeignKey("customers.customer_number", ondelete="CASCADE"))
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    description: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(40))
    # Dương = tiền vào, âm = tiền ra
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))


class CustomerFeature(Base):
    """Đặc trưng hành vi (đầu vào mô hình AI) của từng khách hàng."""

    __tablename__ = "customer_features"

    customer_number: Mapped[str] = mapped_column(ForeignKey("customers.customer_number", ondelete="CASCADE"), primary_key=True)
    features: Mapped[dict] = mapped_column(JsonType)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    customer: Mapped[Customer] = relationship(back_populates="features")


class Application(Base):
    """Hồ sơ đăng ký sản phẩm khách gửi từ web."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_code: Mapped[str] = mapped_column(String(20), unique=True)
    customer_number: Mapped[str] = mapped_column(ForeignKey("customers.customer_number", ondelete="CASCADE"), index=True)
    product_code: Mapped[str] = mapped_column(String(30))
    payload: Mapped[dict] = mapped_column(JsonType)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RecommendationLog(Base):
    """Lưu mỗi lần AI gợi ý, phục vụ thống kê/đánh giá sau này."""

    __tablename__ = "recommendation_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_number: Mapped[str] = mapped_column(ForeignKey("customers.customer_number", ondelete="CASCADE"), index=True)
    top_product_code: Mapped[str] = mapped_column(String(30))
    top_score: Mapped[float]
    result: Mapped[dict] = mapped_column(JsonType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
