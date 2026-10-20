from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Auth ----------
class LoginIn(BaseModel):
    customer_number: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    customer_number: str


class DemoAccount(BaseModel):
    customer_number: str
    full_name: str


# ---------- Customer ----------
class ProfileOut(BaseModel):
    customer_number: str
    full_name: str
    segment: str
    age: int
    tenure_days: int
    email: str
    phone: str


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    number: str
    balance: float | None


class CustomerOut(BaseModel):
    profile: ProfileOut
    accounts: list[AccountOut]


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: datetime
    description: str
    category: str
    amount: float


# ---------- Products ----------
class ProductOut(BaseModel):
    target_key: str
    product_code: str
    product_name: str
    category: str
    badge: str
    description: str
    threshold: float
    highlights: list[str]


# ---------- Recommendations (khớp output VIBRecommendationEngine.predict_single) ----------
class RecommendationItem(BaseModel):
    target_key: str
    product_code: str
    product_name: str
    category: str
    badge: str
    description: str
    score: float
    percent: float
    recommended: bool
    reasons: list[str]


class TopProduct(BaseModel):
    code: str
    name: str
    score: float
    percent: float


class PredictionOut(BaseModel):
    customer_number: str
    top_product: TopProduct
    summary_explanation: str
    recommendations: list[RecommendationItem]


# ---------- Applications ----------
class ApplicationIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    product_code: str
    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=8, max_length=20)
    email: EmailStr
    amount: float | None = Field(default=None, ge=0)
    term_months: int | None = Field(default=None, ge=1, le=120)
    monthly_income: float | None = Field(default=None, ge=0)


class ApplicationOut(BaseModel):
    application_id: str
    status: str
    product_code: str
    created_at: datetime
