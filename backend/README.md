# PG / Hostel Management — POC Backend

Flat structure for demo purposes. Full production-grade layering
(services/, core/, per-domain model files, Alembic migrations, etc.) is
intentionally skipped here — see the notes at the bottom for what changes
when this moves past POC.

## Setup

```bash
# 1. DB — run pg_hostel_schema.sql first, then create an app DB user
#    (root uses socket auth on most MySQL/MariaDB installs, which won't
#    work with this app's TCP connection):
mysql -u root -e "
  CREATE USER 'pg_app'@'%' IDENTIFIED BY 'choose_a_real_password';
  GRANT ALL PRIVILEGES ON pg_hostel_saas.* TO 'pg_app'@'%';
  FLUSH PRIVILEGES;
"

# 2. Python env
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Config
cp .env.example .env            # fill in DB_PASSWORD, JWT_SECRET_KEY

# 4. Ollama (for the chatbot demo)
ollama serve                    # usually auto-starts
ollama pull llama3.1            # or qwen2.5 / mistral-nemo — must support tool calling

# 5. Run
uvicorn app:app --reload
```

Docs: http://localhost:8000/docs · Health check: http://localhost:8000/health

## Demo flow (matches the doc's example)

1. Register an OWNER, a MANAGER, and a RESIDENT via `/api/auth/register`.
2. Log in as OWNER → `POST /api/owner/pgs` to create a PG.
3. Still as OWNER → `POST /api/owner/pgs/{pg_id}/managers` with the manager's user id.
4. Log in as MANAGER → create a room (`/api/manager/rooms`), a bed
   (`/api/manager/rooms/{room_id}/beds`), then attach the resident
   (`/api/manager/residents`) and a rent record (`/api/manager/rent-records`).
5. Log in as RESIDENT → `/api/resident/me/room`, `/api/resident/me/rent`,
   `/api/resident/me/payments`.
6. Any logged-in role → `POST /api/chat` with `{"message": "..."}` to try
   the AI assistant. Try it as each role to show the different tool sets
   (e.g. resident can ask "what's my rent status", owner can ask "how many
   PGs do I own").

## How the chatbot stays safe (ai_service.py)

```
message -> resolve_scope(user)  [role + allowed pg_ids/resident_id, server-side]
        -> Ollama gets only the tool schemas for that role
        -> each tool re-checks the id it's given against scope before querying
        -> result fed back to Ollama -> final grounded answer
        -> logged to chat_logs
```

The model never gets raw SQL access or a generic "run query" tool — only
the named functions in `TOOL_REGISTRY`. If the model asks for something
outside the caller's scope, the tool returns `{"error": "not_authorized"}`
instead of data, and the model is instructed to relay that, not route
around it.

## What's deliberately thin for POC

- All models in one `DB/models.py`, all schemas in one `DB/schemas.py` —
  fine at 9 tables, worth splitting by domain once the app grows.
- Business logic lives directly in the route handlers — no separate
  `services/` layer yet.
- No Alembic migrations — schema changes go through `pg_hostel_schema.sql`
  directly for now.
- Complaints and notices have DB tables and `ai_service.py` tool support
  (`get_complaints`) but no CRUD routes yet — add `routes/complaints.py`
  and `routes/notices.py` following the same pattern as `routes/manager.py`
  when needed.
- CORS is wide open (`allow_origins=["*"]`) — tighten before this leaves
  a demo environment.
