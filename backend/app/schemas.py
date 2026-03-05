from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator


# Auth
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    currency: Optional[str] = "USD"
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    currency: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


# Transaction
class TransactionOut(BaseModel):
    id: int
    transaction_id: str
    date: datetime
    description: str
    amount: float
    category: Optional[str]
    merchant: Optional[str]
    account: Optional[str]
    tax_category: Optional[str] = None
    is_deductible: bool = False

    model_config = {"from_attributes": True}


class TaxUpdate(BaseModel):
    tax_category: Optional[str] = None
    is_deductible: bool = False


# Invoice
class InvoiceOut(BaseModel):
    id: int
    filename: str
    status: str
    ocr_text: Optional[str]
    extracted_data: Optional[dict]
    uploaded_at: datetime

    model_config = {"from_attributes": True}


# Notification
class NotificationRequest(BaseModel):
    recipient: str
    message: str


# Budget Goals
class BudgetGoalCreate(BaseModel):
    category: str
    monthly_limit: float


class BudgetGoalOut(BaseModel):
    id: int
    category: str
    monthly_limit: float
    spent: float
    created_at: datetime

    model_config = {"from_attributes": True}


# Forecast
class ForecastPoint(BaseModel):
    ds: str
    yhat: float
    yhat_lower: float
    yhat_upper: float
