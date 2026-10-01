from fastapi import APIRouter, HTTPException
from app.schemas import ChatRequest, ChatResponse
from app.services import chat_service

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        return ChatResponse(answer=await chat_service.explain(req))
    except Exception as e:
        raise HTTPException(502, f"Gemini chat failed: {e}")
