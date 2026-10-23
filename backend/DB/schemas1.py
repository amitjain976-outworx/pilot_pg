"""
Pydantic schemas for request/response validation.
All schemas kept in one file for POC simplicity.
"""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

from DB.models import UserRole


# --- Auth ---

class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    phone: str | None = None
    password: str = Field(min_length=8)
    role: UserRole


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str | None
    role: UserRole
    is_active: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Owner: PG + Manager assignment ---

class PGCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    address: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None


class PGOut(BaseModel):
    id: int
    name: str
    city: str | None
    status: str

    class Config:
        from_attributes = True


class AssignManagerRequest(BaseModel):
    manager_user_id: int


class OccupancyOut(BaseModel):
    pg_id: int
    pg_name: str
    total_rooms: int
    total_beds: int
    occupied_beds: int
    vacant_beds: int
    occupancy_percentage: float | None


# --- Manager: rooms, beds, residents, rent ---

class RoomCreate(BaseModel):
    room_number: str = Field(min_length=1, max_length=20)
    floor: str | None = None
    room_type: str = "OTHER"
    capacity: int = 1


class RoomOut(BaseModel):
    id: int
    room_number: str
    floor: str | None
    room_type: str
    capacity: int
    status: str

    class Config:
        from_attributes = True


class BedCreate(BaseModel):
    bed_number: str = Field(min_length=1, max_length=10)


class BedOut(BaseModel):
    id: int
    bed_number: str
    status: str

    class Config:
        from_attributes = True


class ResidentCreate(BaseModel):
    user_id: int          # an existing user with role=RESIDENT
    room_id: int
    bed_id: int
    joining_date: date
    rent_amount: Decimal
    security_deposit: Decimal = Decimal("0.00")
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None


class ResidentOut(BaseModel):
    id: int
    user_id: int
    room_id: int
    bed_id: int
    rent_amount: Decimal
    status: str

    class Config:
        from_attributes = True


class RentRecordCreate(BaseModel):
    resident_id: int
    billing_month: int = Field(ge=1, le=12)
    billing_year: int
    amount_due: Decimal
    due_date: date


class PendingRentOut(BaseModel):
    resident_name: str
    amount_due: float
    amount_paid: float
    outstanding: float
    status: str


# --- Resident: own data ---

class MyRoomOut(BaseModel):
    pg_name: str
    room_number: str
    bed_number: str


class MyRentOut(BaseModel):
    monthly_rent: float
    billing_month: int | None = None
    billing_year: int | None = None
    amount_due: float | None = None
    amount_paid: float | None = None
    outstanding: float | None = None
    status: str | None = None


class PaymentOut(BaseModel):
    amount: float
    payment_date: date
    payment_mode: str
    status: str


class PaymentCreate(BaseModel):
    amount: Decimal
    payment_date: date
    payment_mode: str = "UPI"
    transaction_reference: str | None = None


# --- Chat ---

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    tool_calls_made: list[str] = []
