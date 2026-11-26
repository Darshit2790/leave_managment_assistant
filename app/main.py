"""HR Assistant agent orchestrator (FastAPI + LangGraph).

Run from the project root:
    uvicorn app.main:app --port 8000 --reload

Downstream services (defaults, override via .env):
    Employee service  http://127.0.0.1:9090   (employee_retreival_system)
    Leave service     http://127.0.0.1:9091   (leave_management_system)
    Policy RAG        http://127.0.0.1:8001   (policy_rag_service: python main.py serve)
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app import clients
from app.clients import ServiceError
from app.config import settings
from app.graph import agent_graph, execute_action
from app.llm import llm
from app.sessions import sessions

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("orchestrator")

app = FastAPI(
    title="HR Assistant Orchestrator",
    version="1.0.0",
    description="Routes employee chat messages to the policy RAG, employee and leave services.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------- schemas
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, examples=["What is my remaining leave balance?"])
    session_id: str = Field(..., min_length=1)
    employee_id: str = Field(..., min_length=1, examples=["EMP1001"])


class Source(BaseModel):
    document: Optional[str] = None
    page: Optional[int] = None
    content: Optional[str] = None
    score: Optional[float] = None


class ChatResponse(BaseModel):
    answer: str
    agent: str
    source_type: str
    tool_used: Optional[str] = None
    intent: str
    router: str
    sources: List[Source] = []
    requires_confirmation: bool = False
    action: Optional[str] = None
    action_payload: Optional[Dict[str, Any]] = None
    data: Optional[Any] = None
    session_id: str


class ConfirmRequest(BaseModel):
    action: str
    payload: Dict[str, Any]


class ConfirmResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


def _http(e: ServiceError) -> HTTPException:
    return HTTPException(status_code=e.status_code, detail=e.message)


# ---------------------------------------------------------------- chat
@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    employee_id = req.employee_id.strip().upper()
    session = sessions.get(req.session_id, employee_id)
    state = await agent_graph.ainvoke(
        {"message": req.message.strip(), "employee_id": employee_id, "session": session}
    )
    result, route = state["result"], state["route"]
    session.remember(req.message.strip(), result["answer"], route["intent"])
    log.info("session=%s employee=%s intent=%s router=%s",
             req.session_id, employee_id, route["intent"], route.get("router"))
    return ChatResponse(**result, intent=route["intent"], router=route.get("router", "rules"),
                        session_id=req.session_id)


@app.post("/api/v1/chat/confirm", response_model=ConfirmResponse)
async def confirm(req: ConfirmRequest):
    try:
        return ConfirmResponse(**await execute_action(req.action, req.payload))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ServiceError as e:
        raise _http(e)


# ---------------------------------------------------------------- direct REST (frontend pages)
@app.get("/api/v1/leaves/balance/{employee_id}")
async def leave_balance(employee_id: str, year: Optional[int] = None):
    try:
        return await clients.get_leave_balance(employee_id, year)
    except ServiceError as e:
        raise _http(e)


@app.get("/api/v1/leaves/history/{employee_id}")
async def leave_history(
    employee_id: str,
    year: Optional[int] = None,
    leave_type: Optional[str] = None,
    status: Optional[str] = None,
):
    try:
        return await clients.get_leave_history(employee_id, year, leave_type, status)
    except ServiceError as e:
        raise _http(e)


@app.post("/api/v1/leaves/apply")
async def leave_apply(payload: Dict[str, Any] = Body(...)):
    try:
        return await clients.apply_leave(payload)
    except ServiceError as e:
        raise _http(e)


@app.post("/api/v1/leaves/{request_id}/cancel")
async def leave_cancel(request_id: int, payload: Optional[Dict[str, Any]] = Body(None)):
    try:
        return await clients.cancel_leave(request_id, (payload or {}).get("cancel_reason", ""))
    except ServiceError as e:
        raise _http(e)


@app.get("/api/v1/employees/{employee_id}")
async def employee_details(employee_id: str):
    """Full profile from the employee service plus leave summary from the leave service."""
    result: Dict[str, Any] = {"employee_id": employee_id}
    errors = []
    for key, fetch in (("profile", clients.get_employee_profile), ("leave", clients.get_leave_details)):
        try:
            result[key] = await fetch(employee_id)
        except ServiceError as e:
            result[key] = None
            errors.append(e)
    if len(errors) == 2:
        raise _http(errors[0])
    return result


@app.get("/api/v1/holidays")
async def holidays(
    year: Optional[int] = None,
    location: Optional[str] = None,
    holiday_type: Optional[str] = None,
    include_optional: Optional[bool] = None,
):
    try:
        return await clients.get_holidays(
            year=year,
            location=location,
            holiday_type=holiday_type,
            include_optional=None if include_optional is None else str(include_optional).lower(),
        )
    except ServiceError as e:
        raise _http(e)


# ---------------------------------------------------------------- health
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "llm_router": "enabled" if settings.use_llm_router and llm.available else "rules only",
        "services": await clients.service_health(),
    }
