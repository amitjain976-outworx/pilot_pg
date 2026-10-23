from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from DB.database import get_db
from DB.models import PG, PGManager, Resident, Room, Bed, User, UserRole
from DB.schemas import AssignManagerRequest, OccupancyOut, PGCreate, PGOut, PendingRentOut, OwnerSecurityDepositOut
from utils import require_roles

router = APIRouter(prefix="/api/owner", tags=["owner"])


def _owned_pg_or_404(db: Session, owner: User, pg_id: int) -> PG:
    pg = db.get(PG, pg_id)
    if not pg or pg.owner_id != owner.id:
        raise HTTPException(status_code=404, detail="PG not found.")
    return pg


@router.post("/pgs", response_model=PGOut, status_code=201)
def create_pg(payload: PGCreate, db: Session = Depends(get_db), owner: User = Depends(require_roles(UserRole.OWNER))):
    pg = PG(owner_id=owner.id, **payload.model_dump())
    db.add(pg)
    db.commit()
    db.refresh(pg)
    return pg


@router.get("/pgs", response_model=list[PGOut])
def list_my_pgs(db: Session = Depends(get_db), owner: User = Depends(require_roles(UserRole.OWNER))):
    return list(db.scalars(select(PG).where(PG.owner_id == owner.id)))


@router.post("/pgs/{pg_id}/managers", status_code=201)
def assign_manager(
    pg_id: int, payload: AssignManagerRequest,
    db: Session = Depends(get_db), owner: User = Depends(require_roles(UserRole.OWNER)),
):
    _owned_pg_or_404(db, owner, pg_id)

    manager_user = db.get(User, payload.manager_user_id)
    if not manager_user or manager_user.role != UserRole.MANAGER:
        raise HTTPException(status_code=400, detail="manager_user_id must belong to an existing user with role MANAGER.")

    # Enforce "one active PG per manager" here in the service layer (see README
    # for why this isn't a DB-level constraint).
    already_active = db.scalar(
        select(PGManager).where(PGManager.manager_id == manager_user.id, PGManager.is_active.is_(True))
    )
    if already_active:
        raise HTTPException(status_code=400, detail="This manager is already assigned to an active PG.")

    assignment = PGManager(pg_id=pg_id, manager_id=manager_user.id, is_active=True)
    db.add(assignment)
    db.commit()
    return {"message": f"Manager '{manager_user.name}' assigned to PG {pg_id}."}


@router.get("/pgs/{pg_id}/occupancy", response_model=OccupancyOut)
def get_occupancy(pg_id: int, db: Session = Depends(get_db), owner: User = Depends(require_roles(UserRole.OWNER))):
    _owned_pg_or_404(db, owner, pg_id)
    row = db.execute(text("SELECT * FROM v_pg_occupancy WHERE pg_id = :pg_id"), {"pg_id": pg_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="PG not found.")
    return dict(row)


@router.get("/pgs/{pg_id}/pending-rents", response_model=list[PendingRentOut])
def get_pending_rents(
    pg_id: int, billing_month: int, billing_year: int,
    db: Session = Depends(get_db), owner: User = Depends(require_roles(UserRole.OWNER)),
):
    _owned_pg_or_404(db, owner, pg_id)
    rows = db.execute(
        text(
            """
            SELECT res.id AS resident_id, u.name AS resident_name, rr.amount_due, rr.amount_paid, rr.status
            FROM rent_records rr
            JOIN residents res ON rr.resident_id = res.id
            JOIN users u ON res.user_id = u.id
            WHERE res.pg_id = :pg_id AND rr.billing_month = :m AND rr.billing_year = :y
              AND rr.status IN ('PENDING','PARTIAL','OVERDUE')
            """
        ),
        {"pg_id": pg_id, "m": billing_month, "y": billing_year},
    ).mappings().all()
    return [
        {
            "resident_id": r["resident_id"],
            "resident_name": r["resident_name"],
            "amount_due": float(r["amount_due"]),
            "amount_paid": float(r["amount_paid"]),
            "outstanding": float(r["amount_due"] - r["amount_paid"]),
            "status": r["status"],
        }
        for r in rows
    ]


# --- Security Deposits ---

@router.get("/pgs/{pg_id}/security-deposits", response_model=list[OwnerSecurityDepositOut])
def get_pg_security_deposits(
    pg_id: int,
    db: Session = Depends(get_db),
    owner: User = Depends(require_roles(UserRole.OWNER))
):
    """Get a list of all security deposits from residents in a specific PG."""
    pg = _owned_pg_or_404(db, owner, pg_id)
    
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
            "pg_name": pg.name,
            "room_number": room.room_number if room else "Unknown",
            "bed_number": bed.bed_number if bed else "Unknown",
            "amount": float(resident.security_deposit),
            "status": resident.status.value
        })
    
    return result


@router.get("/security-deposits", response_model=list[OwnerSecurityDepositOut])
def get_all_security_deposits(
    db: Session = Depends(get_db),
    owner: User = Depends(require_roles(UserRole.OWNER))
):
    """Get a list of all security deposits from residents across all PGs of the owner."""
    # Get all PGs owned by this owner
    pgs = list(db.scalars(select(PG).where(PG.owner_id == owner.id)))
    pg_ids = [pg.id for pg in pgs]
    
    if not pg_ids:
        return []
    
    # Get all residents in these PGs
    residents = list(
        db.scalars(select(Resident).where(Resident.pg_id.in_(pg_ids)))
    )
    
    result = []
    for resident in residents:
        user = db.get(User, resident.user_id)
        room = db.get(Room, resident.room_id)
        bed = db.get(Bed, resident.bed_id)
        pg = db.get(PG, resident.pg_id)
        
        result.append({
            "resident_id": resident.id,
            "resident_name": user.name if user else f"User {resident.user_id}",
            "pg_name": pg.name if pg else "Unknown PG",
            "room_number": room.room_number if room else "Unknown",
            "bed_number": bed.bed_number if bed else "Unknown",
            "amount": float(resident.security_deposit),
            "status": resident.status.value
        })
    
    return result