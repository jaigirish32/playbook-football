from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user
from app.services.chat_service import answer_question
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post(
    "",
    response_model=ChatResponse,
)
async def chat(
    request: Request,
    body   : ChatRequest,
    db     : Session = Depends(get_db),
    _               = Depends(get_current_user),
):
    result = answer_question(db, body.question)
    return ChatResponse(**result)