from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from DB.database import engine
from routes import auth, owner, manager, resident, chatbot

app = FastAPI(title="PG Hostel Management API (POC)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before anything beyond a POC demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(owner.router)
app.include_router(manager.router)
app.include_router(resident.router)
app.include_router(chatbot.router)


@app.get("/health")
def health():
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {"status": "ok", "database_connected": db_ok}
