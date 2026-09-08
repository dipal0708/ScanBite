from fastapi import APIRouter
from pydantic import BaseModel
from app.agents.label_agent import answer_followup

router = APIRouter(prefix="/agent")


class AskRequest(BaseModel):
    scanResult: dict
    question: str


@router.post("/ask")
async def ask(payload: AskRequest):
    return answer_followup(payload.scanResult, payload.question)
