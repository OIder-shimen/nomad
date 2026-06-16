"""
DeepSeek AI Chat Proxy — no auth required so unauthenticated users can use the chatbot.
"""
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import settings

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 2000


@router.post("/chat")
async def ai_chat(req: ChatRequest):
    if not settings.deepseek_api_key:
        raise HTTPException(status_code=503, detail="AI service not configured")

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.deepseek_api_key}",
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": m.role, "content": m.content} for m in req.messages],
                "temperature": req.temperature,
                "max_tokens": req.max_tokens,
            },
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"AI API error: {resp.status_code}")
        return resp.json()
