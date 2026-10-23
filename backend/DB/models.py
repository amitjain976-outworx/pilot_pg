"""
SQLAlchemy ORM models — mirrors pg_hostel_schema.sql exactly.
All tables kept in one file for POC simplicity (split later if it grows).
"""
import enum
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import (
    String, Text, DateTime, Date, Enum, func, ForeignKey, Numeric,
    SmallInteger, Boolean, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# --- Enums (match the MySQL ENUM columns) ---

class UserRole(str, enum.Enum):
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    RESIDENT = "RESIDENT"


class PGStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class RoomType(str, enum.Enum):
    SINGLE = "SINGLE"
    DOUBLE = "DOUBLE"
    TRIPLE = "TRIPLE"
    DORMITORY = "DORMITORY"
    OTHER = "OTHER"


class RoomStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    MAINTENANCE = "MAINTENANCE"
    INACTIVE = "INACTIVE"


class BedStatus(str, enum.Enum):
    VACANT = "VACANT"
    OCCUPIED = "OCCUPIED"
    MAINTENANCE = "MAINTENANCE"


class ResidentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    NOTICE_PERIOD = "NOTICE_PERIOD"
    INACTIVE = "INACTIVE"


class RentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    PAID = "PAID"
    OVERDUE = "OVERDUE"


class PaymentMode(str, enum.Enum):
    CASH = "CASH"
    UPI = "UPI"
    BANK_TRANSFER = "BANK_TRANSFER"
    CARD = "CARD"
    OTHER = "OTHER"


class PaymentStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    PENDING = "PENDING"
    FAILED = "FAILED"


class ComplaintPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ComplaintStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


# --- Tables ---

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(191), nullable=False, unique=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    resident_profile = relationship("Resident", back_populates="user", uselist=False)


class PG(Base):
    __tablename__ = "pgs"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(191), nullable=True)
    status: Mapped[PGStatus] = mapped_column(Enum(PGStatus), nullable=False, default=PGStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    rooms = relationship("Room", back_populates="pg")


class PGManager(Base):
    __tablename__ = "pg_managers"

    id: Mapped[int] = mapped_column(primary_key=True)
    pg_id: Mapped[int] = mapped_column(ForeignKey("pgs.id", ondelete="CASCADE"))
    manager_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = (UniqueConstraint("pg_id", "room_number", name="uq_room_per_pg"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    pg_id: Mapped[int] = mapped_column(ForeignKey("pgs.id", ondelete="CASCADE"))
    room_number: Mapped[str] = mapped_column(String(20), nullable=False)
    floor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    room_type: Mapped[RoomType] = mapped_column(Enum(RoomType), nullable=False, default=RoomType.OTHER)
    capacity: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    status: Mapped[RoomStatus] = mapped_column(Enum(RoomStatus), nullable=False, default=RoomStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    pg = relationship("PG", back_populates="rooms")
    beds = relationship("Bed", back_populates="room")


class Bed(Base):
    __tablename__ = "beds"
    __table_args__ = (UniqueConstraint("room_id", "bed_number", name="uq_bed_per_room"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    bed_number: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[BedStatus] = mapped_column(Enum(BedStatus), nullable=False, default=BedStatus.VACANT)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    room = relationship("Room", back_populates="beds")


class Resident(Base):
    __tablename__ = "residents"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    pg_id: Mapped[int] = mapped_column(ForeignKey("pgs.id", ondelete="CASCADE"))
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    bed_id: Mapped[int] = mapped_column(ForeignKey("beds.id", ondelete="CASCADE"), unique=True)
    joining_date: Mapped[date] = mapped_column(Date, nullable=False)
    move_in_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    move_out_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rent_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    security_deposit: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    status: Mapped[ResidentStatus] = mapped_column(Enum(ResidentStatus), nullable=False, default=ResidentStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="resident_profile")


class RentRecord(Base):
    __tablename__ = "rent_records"
    __table_args__ = (
        UniqueConstraint("resident_id", "billing_year", "billing_month", name="uq_rent_resident_month"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    resident_id: Mapped[int] = mapped_column(ForeignKey("residents.id", ondelete="CASCADE"))
    billing_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    billing_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    amount_due: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    status: Mapped[RentStatus] = mapped_column(Enum(RentStatus), nullable=False, default=RentStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    resident_id: Mapped[int] = mapped_column(ForeignKey("residents.id", ondelete="CASCADE"))
    rent_record_id: Mapped[int | None] = mapped_column(ForeignKey("rent_records.id", ondelete="SET NULL"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_mode: Mapped[PaymentMode] = mapped_column(Enum(PaymentMode), nullable=False, default=PaymentMode.CASH)
    transaction_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.SUCCESS)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(primary_key=True)
    resident_id: Mapped[int] = mapped_column(ForeignKey("residents.id", ondelete="CASCADE"))
    pg_id: Mapped[int] = mapped_column(ForeignKey("pgs.id", ondelete="CASCADE"))
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[ComplaintPriority] = mapped_column(Enum(ComplaintPriority), nullable=False, default=ComplaintPriority.MEDIUM)
    status: Mapped[ComplaintStatus] = mapped_column(Enum(ComplaintStatus), nullable=False, default=ComplaintStatus.OPEN)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ChatLog(Base):
    __tablename__ = "chat_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_intent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
