from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from database import get_db
from services.chat_service import chat_service


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    text: str
    cards: list[dict] | None = None
    conversation_id: str | None = None


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    messages = [m.model_dump() for m in req.messages]
    result = await chat_service.chat(messages, db)
    return ChatResponse(**result)
