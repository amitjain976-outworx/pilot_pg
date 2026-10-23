from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from DB.database import get_db
from DB.models import User
from DB.schemas import ChatRequest, ChatResponse
from ai_service import handle_chat_message
from utils import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    reply, tool_calls_made = handle_chat_message(db, current_user, payload.message)
    return ChatResponse(reply=reply, tool_calls_made=tool_calls_made)
