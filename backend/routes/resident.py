from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from DB.database import get_db
from DB.models import Payment, PG, RentRecord, RentStatus, Resident, User, UserRole
from DB.schemas import MyRentOut, MyRoomOut, PaymentCreate, PaymentOut, ResidentSecurityDepositOut
from utils import apply_payment_to_rent_record, require_roles

router = APIRouter(prefix="/api/resident", tags=["resident"])


def _my_resident_or_404(db: Session, user: User) -> Resident:
    resident = db.scalar(select(Resident).where(Resident.user_id == user.id))
    if not resident:
        raise HTTPException(status_code=404, detail="No resident profile found for your account yet.")
    return resident


@router.get("/me/room", response_model=MyRoomOut)
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


@router.get("/me/rent", response_model=MyRentOut)
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


@router.get("/me/payments", response_model=list[PaymentOut])
def my_payments(db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.RESIDENT))):
    resident = _my_resident_or_404(db, user)
    rows = db.scalars(select(Payment).where(Payment.resident_id == resident.id).order_by(Payment.payment_date.desc()))
    return list(rows)


@router.post("/me/payments", response_model=PaymentOut, status_code=201)
def log_payment(payload: PaymentCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.RESIDENT))):
    """
    Self-reported payment (e.g. "I just paid via UPI, here's the reference").
    This links to and updates a real rent_record — it's not just a log entry.
    If rent_record_id isn't given, it applies to the oldest unpaid/partial
    record for this resident (most common case: paying this month's rent).
    """
    resident = _my_resident_or_404(db, user)

    if payload.rent_record_id is not None:
        rent_record = db.get(RentRecord, payload.rent_record_id)
        if not rent_record or rent_record.resident_id != resident.id:
            raise HTTPException(status_code=404, detail="Rent record not found for your account.")
    else:
        rent_record = db.execute(
            select(RentRecord)
            .where(RentRecord.resident_id == resident.id, RentRecord.status != RentStatus.PAID)
            .order_by(RentRecord.billing_year.asc(), RentRecord.billing_month.asc())
            .limit(1)
        ).scalar_one_or_none()
        if not rent_record:
            raise HTTPException(status_code=400, detail="No unpaid rent record found to apply this payment to.")

    payment = Payment(
        resident_id=resident.id,
        rent_record_id=rent_record.id,
        amount=payload.amount,
        payment_date=payload.payment_date,
        payment_mode=payload.payment_mode,
        transaction_reference=payload.transaction_reference,
    )
    db.add(payment)
    apply_payment_to_rent_record(db, rent_record, payload.amount)
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/me/security-deposit", response_model=ResidentSecurityDepositOut)
def my_security_deposit(db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.RESIDENT))):
    """Get the security deposit amount deposited by the resident."""
    resident = _my_resident_or_404(db, user)
    pg = db.get(PG, resident.pg_id)
    
    return {
        "amount": float(resident.security_deposit),
        "pg_name": pg.name if pg else "Unknown PG"
    }
