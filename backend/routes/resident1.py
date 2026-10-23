from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from DB.database import get_db
from DB.models import Payment, RentRecord, Resident, User, UserRole
from DB.schemas import MyRentOut, MyRoomOut, PaymentCreate, PaymentOut
from utils import require_roles

router = APIRouter(prefix="/api/resident", tags=["resident"])


def _my_resident_or_404(db: Session, user: User) -> Resident:
    resident = db.scalar(select(Resident).where(Resident.user_id == user.id))
    if not resident:
        raise HTTPException(status_code=404, detail="No resident profile found for your account yet.")
    return resident


@router.get("/room", response_model=MyRoomOut)
def my_room(db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.RESIDENT))):
    resident = _my_resident_or_404(db, user)
    row = db.execute(
        text(
            """
            SELECT p.name AS pg_name, r.room_number, b.bed_number
            FROM residents res
            JOIN pgs p ON res.pg_id = p.id
            JOIN rooms r ON res.room_id = r.id
            JOIN beds b ON res.bed_id = b.id
            WHERE res.id = :resident_id
            """
        ),
        {"resident_id": resident.id},
    ).mappings().first()
    return dict(row)


@router.get("/rent", response_model=MyRentOut)
def my_rent(db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.RESIDENT))):
    resident = _my_resident_or_404(db, user)
    latest = db.execute(
        select(RentRecord).where(RentRecord.resident_id == resident.id)
        .order_by(RentRecord.billing_year.desc(), RentRecord.billing_month.desc()).limit(1)
    ).scalar_one_or_none()

    result = {"monthly_rent": float(resident.rent_amount)}
    if latest:
        result.update({
            "billing_month": latest.billing_month, "billing_year": latest.billing_year,
            "amount_due": float(latest.amount_due), "amount_paid": float(latest.amount_paid),
            "outstanding": float(latest.amount_due - latest.amount_paid), "status": latest.status.value,
        })
    return result


@router.get("/payments", response_model=list[PaymentOut])
def my_payments(db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.RESIDENT))):
    resident = _my_resident_or_404(db, user)
    rows = db.scalars(select(Payment).where(Payment.resident_id == resident.id).order_by(Payment.payment_date.desc()))
    return list(rows)


@router.post("/payments", response_model=PaymentOut, status_code=201)
def log_payment(payload: PaymentCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.RESIDENT))):
    resident = _my_resident_or_404(db, user)
    payment = Payment(resident_id=resident.id, **payload.model_dump())
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment
