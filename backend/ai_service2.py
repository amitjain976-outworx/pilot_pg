"""
AI chatbot service — local Ollama model with controlled database tools.

Hard rule: the LLM never gets raw SQL access. It can only call the named
functions in TOOL_REGISTRY below, each of which re-checks the caller's
scope (role + allowed pg_id/resident_id) before touching the database —
even if the model tries to pass in an id it shouldn't have access to.

    user message -> resolve scope (role, allowed_pg_ids, resident_id)
                 -> send message + role-appropriate tools to Ollama
                 -> execute any tool_calls the model requests (scope-checked)
                 -> feed results back to the model
                 -> model produces the final grounded answer
                 -> logged to chat_logs
"""
import json
import logging
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv
from ollama import Client
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from DB.models import (
    ChatLog, Complaint, PG, PGManager, Payment, RentRecord, Resident, User, UserRole,
)

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
MAX_TOOL_ITERATIONS = 4

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# 1. Permission scope — resolved server-side, never derived from the LLM
# ---------------------------------------------------------------------

@dataclass
class UserScope:
    user_id: int
    role: UserRole
    allowed_pg_ids: list[int] = field(default_factory=list)
    resident_id: int | None = None


def resolve_scope(db: Session, user: User) -> UserScope:
    if user.role == UserRole.OWNER:
        pg_ids = list(db.scalars(select(PG.id).where(PG.owner_id == user.id)))
        return UserScope(user_id=user.id, role=user.role, allowed_pg_ids=pg_ids)

    if user.role == UserRole.MANAGER:
        pg_ids = list(
            db.scalars(select(PGManager.pg_id).where(PGManager.manager_id == user.id, PGManager.is_active.is_(True)))
        )
        return UserScope(user_id=user.id, role=user.role, allowed_pg_ids=pg_ids)

    if user.role == UserRole.RESIDENT:
        resident = db.scalar(select(Resident).where(Resident.user_id == user.id))
        if resident is None:
            return UserScope(user_id=user.id, role=user.role)
        return UserScope(user_id=user.id, role=user.role, allowed_pg_ids=[resident.pg_id], resident_id=resident.id)

    return UserScope(user_id=user.id, role=user.role)


# ---------------------------------------------------------------------
# 2. Controlled tools — the ONLY functions the LLM can call
# ---------------------------------------------------------------------

NOT_AUTHORIZED = {"error": "not_authorized", "message": "You do not have access to that PG or record."}


def _pg_allowed(scope: UserScope, pg_id: int) -> bool:
    return pg_id in scope.allowed_pg_ids


def get_my_pgs(db: Session, scope: UserScope) -> dict:
    if scope.role != UserRole.OWNER:
        return NOT_AUTHORIZED
    rows = db.execute(select(PG.id, PG.name, PG.city, PG.status).where(PG.id.in_(scope.allowed_pg_ids))).all()
    return {"pgs": [{"pg_id": r.id, "name": r.name, "city": r.city, "status": r.status.value} for r in rows]}


def get_pg_occupancy(db: Session, scope: UserScope, pg_id: int) -> dict:
    """
    Returns bed-level AND room-level occupancy as separate, explicit fields.

    Why both: "vacant_beds" and "vacant rooms" are different units (a room
    with 2 beds where only 1 is occupied is neither fully vacant nor fully
    occupied). If we only returned bed counts, the model would have to
    infer room-level vacancy itself — exactly the kind of derived/guessed
    number this tool is meant to prevent. So we compute it here, in code,
    against the real bed-to-room mapping, and hand the model a number it
    never has to calculate itself.
    """
    if not _pg_allowed(scope, pg_id):
        return NOT_AUTHORIZED

    summary = db.execute(text("SELECT * FROM v_pg_occupancy WHERE pg_id = :pg_id"), {"pg_id": pg_id}).mappings().first()
    if not summary:
        return {"error": "not_found", "message": "No such PG."}

    room_rows = db.execute(
        text(
            """
            SELECT r.id AS room_id, COUNT(b.id) AS bed_count,
                   SUM(CASE WHEN b.status = 'OCCUPIED' THEN 1 ELSE 0 END) AS occupied_count
            FROM rooms r
            LEFT JOIN beds b ON b.room_id = r.id
            WHERE r.pg_id = :pg_id
            GROUP BY r.id
            """
        ),
        {"pg_id": pg_id},
    ).all()

    fully_vacant_rooms = sum(1 for r in room_rows if r.bed_count > 0 and r.occupied_count == 0)
    fully_occupied_rooms = sum(1 for r in room_rows if r.bed_count > 0 and r.occupied_count == r.bed_count)
    partially_occupied_rooms = len(room_rows) - fully_vacant_rooms - fully_occupied_rooms

    result = dict(summary)
    result.update({
        "fully_vacant_rooms": fully_vacant_rooms,
        "fully_occupied_rooms": fully_occupied_rooms,
        "partially_occupied_rooms": partially_occupied_rooms,
    })
    return result


def get_pending_rents(db: Session, scope: UserScope, pg_id: int, billing_month: int, billing_year: int) -> dict:
    if scope.role not in (UserRole.OWNER, UserRole.MANAGER) or not _pg_allowed(scope, pg_id):
        return NOT_AUTHORIZED
    rows = db.execute(
        select(User.name, RentRecord.amount_due, RentRecord.amount_paid, RentRecord.status)
        .join(Resident, Resident.id == RentRecord.resident_id)
        .join(User, User.id == Resident.user_id)
        .where(
            Resident.pg_id == pg_id,
            RentRecord.billing_month == billing_month,
            RentRecord.billing_year == billing_year,
            RentRecord.status.in_(["PENDING", "PARTIAL", "OVERDUE"]),
        )
    ).all()
    return {
        "pending_residents": [
            {"name": r.name, "amount_due": float(r.amount_due), "amount_paid": float(r.amount_paid),
             "outstanding": float(r.amount_due - r.amount_paid), "status": r.status.value}
            for r in rows
        ]
    }


def get_complaints(db: Session, scope: UserScope, pg_id: int) -> dict:
    if scope.role not in (UserRole.OWNER, UserRole.MANAGER) or not _pg_allowed(scope, pg_id):
        return NOT_AUTHORIZED
    rows = db.execute(
        select(Complaint.id, Complaint.category, Complaint.priority, Complaint.status)
        .where(Complaint.pg_id == pg_id, Complaint.status.in_(["OPEN", "IN_PROGRESS"]))
    ).all()
    return {"complaints": [{"id": r.id, "category": r.category, "priority": r.priority.value, "status": r.status.value} for r in rows]}


def get_my_payment_history(db: Session, scope: UserScope) -> dict:
    if scope.role != UserRole.RESIDENT or scope.resident_id is None:
        return NOT_AUTHORIZED
    rows = db.execute(
        select(Payment.amount, Payment.payment_date, Payment.payment_mode, Payment.status)
        .where(Payment.resident_id == scope.resident_id)
        .order_by(Payment.payment_date.desc())
    ).all()
    return {"payments": [{"amount": float(r.amount), "date": r.payment_date.isoformat(), "mode": r.payment_mode.value, "status": r.status.value} for r in rows]}


def get_my_rent_status(db: Session, scope: UserScope) -> dict:
    if scope.role != UserRole.RESIDENT or scope.resident_id is None:
        return NOT_AUTHORIZED
    resident = db.get(Resident, scope.resident_id)
    latest = db.execute(
        select(RentRecord).where(RentRecord.resident_id == scope.resident_id)
        .order_by(RentRecord.billing_year.desc(), RentRecord.billing_month.desc()).limit(1)
    ).scalar_one_or_none()

    result = {"monthly_rent": float(resident.rent_amount)} if resident else {}
    if latest:
        result.update({
            "billing_month": latest.billing_month, "billing_year": latest.billing_year,
            "amount_due": float(latest.amount_due), "amount_paid": float(latest.amount_paid),
            "outstanding": float(latest.amount_due - latest.amount_paid), "status": latest.status.value,
        })
    else:
        result["note"] = "No rent record found yet."
    return result


def get_my_room(db: Session, scope: UserScope) -> dict:
    if scope.role != UserRole.RESIDENT or scope.resident_id is None:
        return NOT_AUTHORIZED
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
        {"resident_id": scope.resident_id},
    ).mappings().first()
    return dict(row) if row else {"note": "No room assignment found."}


TOOL_REGISTRY = {
    "get_my_pgs": get_my_pgs,
    "get_pg_occupancy": get_pg_occupancy,
    "get_pending_rents": get_pending_rents,
    "get_complaints": get_complaints,
    "get_my_payment_history": get_my_payment_history,
    "get_my_rent_status": get_my_rent_status,
    "get_my_room": get_my_room,
}

TOOLS_BY_ROLE: dict[UserRole, list[str]] = {
    UserRole.OWNER: ["get_my_pgs", "get_pg_occupancy", "get_pending_rents", "get_complaints"],
    UserRole.MANAGER: ["get_pg_occupancy", "get_pending_rents", "get_complaints"],
    UserRole.RESIDENT: ["get_my_payment_history", "get_my_rent_status", "get_my_room"],
}

TOOL_SCHEMAS = {
    "get_my_pgs": {"type": "function", "function": {
        "name": "get_my_pgs", "description": "List all PG properties owned by the current user.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    "get_pg_occupancy": {"type": "function", "function": {
        "name": "get_pg_occupancy",
        "description": (
            "Get occupancy stats for one PG. Returns BOTH bed-level counts "
            "(total_beds, occupied_beds, vacant_beds) AND room-level counts "
            "(total_rooms, fully_vacant_rooms, fully_occupied_rooms, "
            "partially_occupied_rooms) as separate pre-computed fields. "
            "A 'bed' and a 'room' are different units — a room can hold "
            "multiple beds — so never use a bed count as a room count or "
            "vice versa; always quote the field that matches what was asked."
        ),
        "parameters": {"type": "object", "properties": {"pg_id": {"type": "integer"}}, "required": ["pg_id"]}}},
    "get_pending_rents": {"type": "function", "function": {
        "name": "get_pending_rents", "description": "List residents with pending/partial/overdue rent for a PG and month.",
        "parameters": {"type": "object", "properties": {
            "pg_id": {"type": "integer"}, "billing_month": {"type": "integer"}, "billing_year": {"type": "integer"}},
            "required": ["pg_id", "billing_month", "billing_year"]}}},
    "get_complaints": {"type": "function", "function": {
        "name": "get_complaints", "description": "List open/in-progress complaints for a PG.",
        "parameters": {"type": "object", "properties": {"pg_id": {"type": "integer"}}, "required": ["pg_id"]}}},
    "get_my_payment_history": {"type": "function", "function": {
        "name": "get_my_payment_history", "description": "Get the current resident's own payment history. No arguments.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    "get_my_rent_status": {"type": "function", "function": {
        "name": "get_my_rent_status", "description": "Get the current resident's rent amount and outstanding balance. No arguments.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    "get_my_room": {"type": "function", "function": {
        "name": "get_my_room", "description": "Get the current resident's PG, room, and bed. No arguments.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
}


def get_tool_schemas_for_role(role: UserRole) -> list[dict]:
    return [TOOL_SCHEMAS[name] for name in TOOLS_BY_ROLE.get(role, [])]


def build_system_prompt(scope: UserScope) -> str:
    return (
        "You are the assistant embedded in a PG/Hostel management application.\n"
        f"The current user's role is {scope.role.value}. Their accessible PG id(s): {scope.allowed_pg_ids or 'none'}.\n"
        "Rules: (1) Only answer using the provided tools — never guess or invent data. "
        "(2) You have no direct database or SQL access. "
        "(3) If a tool result has an 'error' field, tell the user you don't have access to that — don't work around it. "
        "(4) Keep answers short and grounded only in tool results. "
        "(5) Never blend numbers across different units — a count of 'beds' is not a count of 'rooms', "
        "a count of 'residents' is not a count of 'PGs', etc. Only state a count for the exact unit the "
        "user asked about, using the field that names that unit. If the tool result has no field for the "
        "unit asked about, say you don't have that specific figure rather than deriving or estimating it.\n"
    )


# ---------------------------------------------------------------------
# 3. Ollama client
# ---------------------------------------------------------------------

class OllamaUnavailableError(Exception):
    pass


def _ollama_chat(messages: list[dict], tools: list[dict] | None) -> dict:
    client = Client(host=OLLAMA_HOST)
    try:
        response = client.chat(model=OLLAMA_MODEL, messages=messages, tools=tools or None)
    except Exception as exc:
        raise OllamaUnavailableError(
            f"Could not reach Ollama at {OLLAMA_HOST} with model '{OLLAMA_MODEL}'. "
            f"Is `ollama serve` running and is the model pulled (`ollama pull {OLLAMA_MODEL}`)? Error: {exc}"
        ) from exc
    return response["message"]


# ---------------------------------------------------------------------
# 4. Chat orchestration — the tool-calling loop
# ---------------------------------------------------------------------

def handle_chat_message(db: Session, user: User, user_message: str) -> tuple[str, list[str]]:
    scope = resolve_scope(db, user)
    tool_schemas = get_tool_schemas_for_role(scope.role)

    messages = [
        {"role": "system", "content": build_system_prompt(scope)},
        {"role": "user", "content": user_message},
    ]
    tool_calls_made: list[str] = []

    for _ in range(MAX_TOOL_ITERATIONS):
        try:
            assistant_message = _ollama_chat(messages, tool_schemas)
        except OllamaUnavailableError as exc:
            logger.warning("Ollama unavailable: %s", exc)
            reply = "The AI assistant isn't reachable right now (Ollama may not be running). Please try again shortly."
            _log_chat(db, user, user_message, ",".join(tool_calls_made) or None, reply)
            return reply, tool_calls_made

        tool_calls = assistant_message.get("tool_calls")
        if not tool_calls:
            reply = assistant_message.get("content", "").strip() or "I don't have an answer for that."
            _log_chat(db, user, user_message, ",".join(tool_calls_made) or None, reply)
            return reply, tool_calls_made

        messages.append(assistant_message)
        for call in tool_calls:
            fn_name = call["function"]["name"]
            raw_args = call["function"].get("arguments") or {}
            args = raw_args if isinstance(raw_args, dict) else json.loads(raw_args)
            tool_calls_made.append(fn_name)

            tool_fn = TOOL_REGISTRY.get(fn_name)
            if tool_fn is None:
                result = {"error": "unknown_tool", "message": f"No such tool: {fn_name}"}
            else:
                try:
                    result = tool_fn(db=db, scope=scope, **args)  # scope is server-resolved, never from args
                except TypeError as exc:
                    result = {"error": "bad_arguments", "message": str(exc)}
                except Exception:
                    logger.exception("Tool '%s' failed", fn_name)
                    result = {"error": "internal_error", "message": "Something went wrong running that lookup."}

            messages.append({"role": "tool", "content": json.dumps(result, default=str)})

    reply = "I couldn't finish answering that within the allowed steps. Could you rephrase or narrow your question?"
    _log_chat(db, user, user_message, ",".join(tool_calls_made) or None, reply)
    return reply, tool_calls_made


def _log_chat(db: Session, user: User, message: str, resolved_intent: str | None, response: str) -> None:
    try:
        db.add(ChatLog(user_id=user.id, role=user.role, message=message, resolved_intent=resolved_intent, response=response))
        db.commit()
    except Exception:
        logger.exception("Failed to write chat_logs entry")
        db.rollback()
