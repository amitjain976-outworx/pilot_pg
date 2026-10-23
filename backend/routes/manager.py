from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from DB.database import get_db
from DB.models import Bed, BedStatus, PGManager, Payment, Resident, RentRecord, Room, User, UserRole
from DB.schemas import BedCreate, BedOut, PaymentCreate, PaymentOut, PendingRentOut, RentRecordCreate, ResidentCreate, ResidentOut, RoomCreate, RoomOut, ManagerSecurityDepositOut
from utils import apply_payment_to_rent_record, require_roles

router = APIRouter(prefix="/api/manager", tags=["manager"])


def _managers_active_pg_id(db: Session, manager: User) -> int:
    """Every manager route is scoped to the single PG this manager currently
    runs. 403s (not a 404) if they have no active assignment — that's an
    authorization gap, not a missing-resource one."""
    assignment = db.scalar(
        select(PGManager).where(PGManager.manager_id == manager.id, PGManager.is_active.is_(True))
    )
    if not assignment:
        raise HTTPException(status_code=403, detail="You are not currently assigned to any PG.")
    return assignment.pg_id


# --- Rooms ---

@router.post("/rooms", response_model=RoomOut, status_code=201)
def create_room(payload: RoomCreate, db: Session = Depends(get_db), manager: User = Depends(require_roles(UserRole.MANAGER))):
    pg_id = _managers_active_pg_id(db, manager)
    room = Room(pg_id=pg_id, **payload.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@router.get("/rooms", response_model=list[RoomOut])
def list_rooms(db: Session = Depends(get_db), manager: User = Depends(require_roles(UserRole.MANAGER))):
    pg_id = _managers_active_pg_id(db, manager)
    return list(db.scalars(select(Room).where(Room.pg_id == pg_id)))


# --- Beds ---

@router.post("/rooms/{room_id}/beds", response_model=BedOut, status_code=201)
def create_bed(room_id: int, payload: BedCreate, db: Session = Depends(get_db), manager: User = Depends(require_roles(UserRole.MANAGER))):
    pg_id = _managers_active_pg_id(db, manager)
    room = db.get(Room, room_id)
    if not room or room.pg_id != pg_id:
        raise HTTPException(status_code=404, detail="Room not found in your PG.")

    bed = Bed(room_id=room_id, bed_number=payload.bed_number)
    db.add(bed)
    db.commit()
    db.refresh(bed)
    return bed


@router.get("/rooms/{room_id}/beds", response_model=list[BedOut])
def list_beds(room_id: int, db: Session = Depends(get_db), manager: User = Depends(require_roles(UserRole.MANAGER))):
    pg_id = _managers_active_pg_id(db, manager)
    room = db.get(Room, room_id)
    if not room or room.pg_id != pg_id:
        raise HTTPException(status_code=404, detail="Room not found in your PG.")
    return list(db.scalars(select(Bed).where(Bed.room_id == room_id)))


# --- Residents ---

@router.post("/residents", response_model=ResidentOut, status_code=201)
def create_resident(payload: ResidentCreate, db: Session = Depends(get_db), manager: User = Depends(require_roles(UserRole.MANAGER))):
    pg_id = _managers_active_pg_id(db, manager)

    resident_user = db.get(User, payload.user_id)
    if not resident_user or resident_user.role != UserRole.RESIDENT:
        raise HTTPException(status_code=400, detail="user_id must belong to an existing user with role RESIDENT.")

    room = db.get(Room, payload.room_id)
    if not room or room.pg_id != pg_id:
        raise HTTPException(status_code=404, detail="Room not found in your PG.")

    bed = db.get(Bed, payload.bed_id)
    if not bed or bed.room_id != payload.room_id:
        raise HTTPException(status_code=404, detail="Bed not found in that room.")
    if bed.status == BedStatus.OCCUPIED:
        raise HTTPException(status_code=400, detail="That bed is already occupied.")

    resident = Resident(
        user_id=payload.user_id, pg_id=pg_id, room_id=payload.room_id, bed_id=payload.bed_id,
        joining_date=payload.joining_date, move_in_date=payload.joining_date,
        rent_amount=payload.rent_amount, security_deposit=payload.security_deposit,
        emergency_contact_name=payload.emergency_contact_name, emergency_contact_phone=payload.emergency_contact_phone,
    )
    db.add(resident)
    bed.status = BedStatus.OCCUPIED
    db.commit()
    db.refresh(resident)
    return resident


@router.get("/residents", response_model=list[ResidentOut])
def list_residents(db: Session = Depends(get_db), manager: User = Depends(require_roles(UserRole.MANAGER))):
    pg_id = _managers_active_pg_id(db, manager)
    residents = list(db.scalars(select(Resident).where(Resident.pg_id == pg_id)))
    
    # Enrich resident data with names and room/bed details
    result = []
    for resident in residents:
        user = db.get(User, resident.user_id)
        room = db.get(Room, resident.room_id)
        bed = db.get(Bed, resident.bed_id)
        
        resident_data = ResidentOut.from_orm(resident)
        resident_data.resident_name = user.name if user else f"User {resident.user_id}"
        resident_data.room_number = room.room_number if room else None
        resident_data.bed_number = bed.bed_number if bed else None
        result.append(resident_data)
    
    return result


# --- Rent ---

@router.post("/rent-records", status_code=201)
def create_rent_record(payload: RentRecordCreate, db: Session = Depends(get_db), manager: User = Depends(require_roles(UserRole.MANAGER))):
    pg_id = _managers_active_pg_id(db, manager)
    resident = db.get(Resident, payload.resident_id)
    if not resident or resident.pg_id != pg_id:
        raise HTTPException(status_code=404, detail="Resident not found in your PG.")

    record = RentRecord(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "message": "Rent record created."}


@router.get("/rent-records/pending", response_model=list[PendingRentOut])
def pending_rents(billing_month: int, billing_year: int, db: Session = Depends(get_db), manager: User = Depends(require_roles(UserRole.MANAGER))):
    pg_id = _managers_active_pg_id(db, manager)
    rows = (
        db.query(Resident.id, User.name, RentRecord.amount_due, RentRecord.amount_paid, RentRecord.status)
        .join(Resident, Resident.id == RentRecord.resident_id)
        .join(User, User.id == Resident.user_id)
        .filter(
            Resident.pg_id == pg_id,
            RentRecord.billing_month == billing_month,
            RentRecord.billing_year == billing_year,
            RentRecord.status.in_(["PENDING", "PARTIAL", "OVERDUE"]),
        )
        .all()
    )
    return [
        {"resident_id": r.id, "resident_name": r.name if r.name else f"User {r.id}", 
         "amount_due": float(r.amount_due), "amount_paid": float(r.amount_paid),
         "outstanding": float(r.amount_due - r.amount_paid), "status": r.status.value}
        for r in rows
    ]


# --- Collecting a rent payment (THE endpoint for "mark rent as paid") ---

@router.post("/rent-records/{rent_record_id}/payments", response_model=PaymentOut, status_code=201)
def collect_payment(
    rent_record_id: int, payload: PaymentCreate,
    db: Session = Depends(get_db), manager: User = Depends(require_roles(UserRole.MANAGER)),
):
    """
    This is how a manager marks rent as paid (in full or in part): record a
    payment against a specific rent_record. It creates the Payment row AND
    updates that rent_record's amount_paid/status in the same transaction —
    creating a rent_record via POST /rent-records does NOT do this; that
    endpoint only schedules what's owed, it doesn't collect anything.
    """
    pg_id = _managers_active_pg_id(db, manager)

    rent_record = db.get(RentRecord, rent_record_id)
    if not rent_record:
        raise HTTPException(status_code=404, detail="Rent record not found.")

    resident = db.get(Resident, rent_record.resident_id)
    if not resident or resident.pg_id != pg_id:
        raise HTTPException(status_code=404, detail="Rent record not found in your PG.")

    if payload.rent_record_id is not None and payload.rent_record_id != rent_record_id:
        raise HTTPException(status_code=400, detail="rent_record_id in the body must match the URL, or be omitted.")

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


# --- Security Deposits ---

@router.get("/security-deposits", response_model=list[ManagerSecurityDepositOut])
def get_security_deposits(db: Session = Depends(get_db), manager: User = Depends(require_roles(UserRole.MANAGER))):
    """Get a list of all security deposits from residents in the manager's assigned PG."""
    pg_id = _managers_active_pg_id(db, manager)
    
    residents = list(
        db.scalars(select(Resident).where(Resident.pg_id == pg_id))
    )
    
    result = []
    for resident in residents:
        user = db.get(User, resident.user_id)
        room = db.get(Room, resident.room_id)
        bed = db.get(Bed, resident.bed_id)
        
        result.append({
            "resident_id": resident.id,
            "resident_name": user.name if user else f"User {resident.user_id}",
            "room_number": room.room_number if room else "Unknown",
            "bed_number": bed.bed_number if bed else "Unknown",
            "amount": float(resident.security_deposit),
            "status": resident.status.value
        })
    
    return result
