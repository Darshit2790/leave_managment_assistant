"""LangGraph agent: route the message, then run one specialist node."""
import re
from datetime import date
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from app import clients
from app.clients import ServiceError
from app.config import settings
import asyncio

from app.llm import LLMError, llm
from app.router import add_working_days, route, working_days
from app.sessions import Session

CANCELLABLE = {"Pending", "Approved"}
BALANCE_KEYS = {
    "Annual": "annual", "Sick": "sick", "Casual": "casual",
    "Maternity": "maternity", "Paternity": "paternity", "Comp Off": "comp_off",
}
ACKNOWLEDGEMENT = re.compile(r"(thanks?( you)?|thank you|ok(ay)?|bye|never ?mind|no|nope|cool|great)[.! ]*", re.I)
DISCARD_DRAFT = re.compile(r"(cancel|never ?mind|stop|forget (it|that)|abort|no|nope)[.! ]*", re.I)


class AgentState(TypedDict, total=False):
    message: str
    employee_id: str
    session: Session
    route: Dict[str, Any]
    result: Dict[str, Any]


# ---------------------------------------------------------------- helpers
def reply(
    answer: str,
    agent: str,
    tool: Optional[str] = None,
    source_type: str = "hr_system",
    **extra: Any,
) -> Dict[str, Any]:
    return {
        "answer": answer,
        "agent": agent,
        "tool_used": tool,
        "source_type": source_type,
        "sources": extra.pop("sources", []),
        "requires_confirmation": extra.pop("requires_confirmation", False),
        "action": extra.pop("action", None),
        "action_payload": extra.pop("action_payload", None),
        "data": extra.pop("data", None),
    }


def service_failure(e: ServiceError, agent: str, employee_id: str) -> Dict[str, Any]:
    if e.status_code == 503:
        answer = f"The {e.service.lower()} isn't reachable right now. Please make sure it's running and try again."
    elif e.status_code == 404:
        answer = (f"I couldn't find that record for employee **{employee_id}** ({e.message}) "
                  "Please check the Employee ID in the sidebar.")
    else:
        answer = f"{e.service} returned an error: {e.message}"
    return reply(answer, agent, source_type="error")


def fmt_date(value: str) -> str:
    return date.fromisoformat(value).strftime("%a, %d %b %Y")


def days(value: float) -> str:
    return f"{value:g} day" + ("" if value == 1 else "s")


# ---------------------------------------------------------------- nodes
async def route_node(state: AgentState) -> AgentState:
    session = state["session"]
    if session.draft is not None and DISCARD_DRAFT.fullmatch(state["message"].strip()):
        session.draft = None
        return {"route": {"intent": "draft_discarded", "router": "rules"}}
    return {"route": await route(state["message"], draft=session.draft)}


async def policy_node(state: AgentState) -> AgentState:
    agent = "Policy Agent"
    try:
        res = await clients.query_policy(
            state["message"], state["session"].policy_history()
        )
    except ServiceError as e:
        return {"result": service_failure(e, agent, state["employee_id"])}

    sources = [
        {
            "document": s.get("source"),
            "page": s.get("page"),
            "content": f"Relevance score: {s.get('score')}",
            "score": s.get("score"),
        }
        for s in res.get("sources", [])
    ]
    return {"result": reply(
        res.get("answer", ""), agent, "policy_rag.query", "policy_documents",
        sources=sources, data={"found": res.get("found")},
    )}


async def employee_node(state: AgentState) -> AgentState:
    agent, emp = "Employee Info Agent", state["employee_id"]
    kind = state["route"].get("employee_info_type") or "profile"
    try:
        if kind == "profile":
            data = await clients.get_employee_profile(emp)
            answer = format_profile(data)
        else:
            data = await clients.get_employee_section(emp, kind)
            answer = SECTION_FORMATTERS[kind](data)
    except ServiceError as e:
        return {"result": service_failure(e, agent, emp)}
    return {"result": reply(answer, agent, f"employee_service.{kind}", data=data)}


async def balance_node(state: AgentState) -> AgentState:
    agent, emp, r = "Leave Agent", state["employee_id"], state["route"]
    try:
        data = await clients.get_leave_balance(emp, r.get("year"))
    except ServiceError as e:
        return {"result": service_failure(e, agent, emp)}

    balances = data.get("balances", {})
    only = BALANCE_KEYS.get(r.get("leave_type") or "")
    lines = []
    for label, key in BALANCE_KEYS.items():
        b = balances.get(key)
        if not b or (only and key != only) or (not only and not b["entitled"] and not b["used"]):
            continue
        extra = f", {days(b['carried_forward'])} carried forward" if b.get("carried_forward") else ""
        lines.append(f"- **{label}:** {days(b['available'])} available "
                     f"(entitled {b['entitled']:g}, used {b['used']:g}{extra})")

    header = f"**Leave balance for {data.get('year')}**"
    if not only:
        header += f" — {days(data.get('total_available', 0))} available in total"
    answer = header + "\n\n" + ("\n".join(lines) or "No balance recorded for that leave type.")
    return {"result": reply(answer, agent, "leave_service.leave_balance", data=data)}


async def history_node(state: AgentState) -> AgentState:
    agent, emp, r = "Leave Agent", state["employee_id"], state["route"]
    try:
        data = await clients.get_leave_history(
            emp, year=r.get("year"), leave_type=r.get("leave_type"), status=r.get("status_filter")
        )
    except ServiceError as e:
        return {"result": service_failure(e, agent, emp)}

    rows: List[Dict[str, Any]] = data.get("leave_history", [])
    if not rows:
        answer = "No leave requests found" + (" for those filters." if data.get("filters_applied") else ".")
    else:
        shown = rows[: settings.max_history_rows]
        lines = [
            f"- **#{x['request_id']}** · {x['leave_type']} · {fmt_date(x['start_date'])} → "
            f"{fmt_date(x['end_date'])} ({days(x['days_requested'])}) · **{x['status']}**"
            for x in shown
        ]
        answer = f"**Your leave requests** ({len(rows)} found)\n\n" + "\n".join(lines)
        if len(rows) > len(shown):
            answer += f"\n\n_Showing the latest {len(shown)}._"
    return {"result": reply(answer, agent, "leave_service.leave_history", data=data)}


async def holidays_node(state: AgentState) -> AgentState:
    agent, r, today = "Leave Agent", state["route"], date.today()
    try:
        if r.get("year"):
            data = await clients.get_holidays(year=r["year"])
            items, title = data.get("holidays", []), f"**Holidays in {r['year']}**"
        else:
            data = await clients.get_holidays(year=today.year)
            items = [h for h in data.get("holidays", []) if h["date"] >= today.isoformat()]
            if len(items) < settings.max_holiday_rows:
                try:
                    nxt = await clients.get_holidays(year=today.year + 1)
                    items += nxt.get("holidays", [])
                except ServiceError:
                    pass
            title = "**Upcoming holidays**"
    except ServiceError as e:
        return {"result": service_failure(e, agent, state["employee_id"])}

    items = sorted(items, key=lambda h: h["date"])[: settings.max_holiday_rows]
    lines = []
    for h in items:
        notes = [h["holiday_type"]]
        if h.get("location") and h["location"] != "All Locations":
            notes.append(h["location"] + " only")
        if h.get("is_optional"):
            notes.append("optional")
        lines.append(f"- **{fmt_date(h['date'])}** — {h['name']} ({', '.join(notes)})")
    answer = title + "\n\n" + ("\n".join(lines) or "No holidays found.")
    return {"result": reply(answer, agent, "leave_service.holidays", data={"holidays": items})}


async def apply_node(state: AgentState) -> AgentState:
    agent, emp, r, session = "Leave Agent", state["employee_id"], state["route"], state["session"]
    draft = dict(session.draft or {})
    for key in ("leave_type", "start_date", "end_date", "reason", "duration_days"):
        if r.get(key):
            draft[key] = r[key]
    if draft.get("start_date"):
        start_d, n = date.fromisoformat(draft["start_date"]), draft.get("duration_days")
        if n and (not draft.get("end_date") or draft["end_date"] == draft["start_date"]):
            draft["end_date"] = add_working_days(start_d, n).isoformat()
        draft.setdefault("end_date", draft["start_date"])

    missing = []
    if not draft.get("leave_type"):
        missing.append("the **leave type** (Annual, Sick, Casual, Maternity, Paternity or Comp Off)")
    if not draft.get("start_date"):
        missing.append("the **start date** (e.g. 2026-12-01 or 'tomorrow')" if draft.get("duration_days")
                       else "the **dates** (e.g. 2026-12-01 to 2026-12-03, or 'tomorrow')")
    if missing:
        session.draft = draft
        return {"result": reply(
            "Sure, I can apply for "
            + (f"{days(draft['duration_days'])} of leave" if draft.get("duration_days") else "leave")
            + ". Please tell me " + " and ".join(missing) + ".",
            agent, source_type="conversation",
        )}

    start, end = date.fromisoformat(draft["start_date"]), date.fromisoformat(draft["end_date"])
    if end < start:
        draft.pop("start_date"), draft.pop("end_date")
        session.draft = draft
        return {"result": reply("The end date is before the start date. Please give the dates again.",
                                agent, source_type="conversation")}
    n_days = working_days(start, end)
    if n_days == 0:
        draft.pop("start_date"), draft.pop("end_date")
        session.draft = draft
        return {"result": reply("Those dates fall on a weekend, so no leave is needed. "
                                "Please pick working days (Mon–Fri).", agent, source_type="conversation")}

    balance_line = ""
    try:
        bal = await clients.get_leave_balance(emp, start.year)
        available = bal["balances"][BALANCE_KEYS[draft["leave_type"]]]["available"]
        if n_days > available:
            leave_type = draft.pop("leave_type")
            session.draft = draft
            return {"result": reply(
                f"You only have **{days(available)}** of {leave_type} leave available, "
                f"but this request needs {days(n_days)}. Which other leave type would you like to use?",
                agent, "leave_service.leave_balance", source_type="hr_system",
            )}
        balance_line = f"\n- **Balance after this request:** {days(available - n_days)}"
    except ServiceError as e:
        if e.status_code in (404, 503):
            return {"result": service_failure(e, agent, emp)}
    except KeyError:
        pass

    session.draft = None
    payload = {
        "employee_id": emp,
        "leave_type": draft["leave_type"],
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "reason": draft.get("reason") or "",
    }
    answer = (
        "Please confirm this leave application:\n\n"
        f"- **Type:** {payload['leave_type']}\n"
        f"- **From:** {fmt_date(payload['start_date'])}\n"
        f"- **To:** {fmt_date(payload['end_date'])}\n"
        f"- **Working days:** {n_days}\n"
        f"- **Reason:** {payload['reason'] or '—'}"
        f"{balance_line}"
    )
    return {"result": reply(answer, agent, "leave_service.apply_leave",
                            requires_confirmation=True, action="apply_leave", action_payload=payload)}


async def cancel_node(state: AgentState) -> AgentState:
    agent, emp, r = "Leave Agent", state["employee_id"], state["route"]
    try:
        history = (await clients.get_leave_history(emp)).get("leave_history", [])
    except ServiceError as e:
        return {"result": service_failure(e, agent, emp)}

    open_requests = [x for x in history if x["status"] in CANCELLABLE]
    rid = r.get("request_id")
    if rid is None:
        if not open_requests:
            return {"result": reply("You have no pending or approved leave requests to cancel.", agent,
                                    "leave_service.leave_history")}
        lines = [f"- **#{x['request_id']}** · {x['leave_type']} · {fmt_date(x['start_date'])} → "
                 f"{fmt_date(x['end_date'])} · {x['status']}" for x in open_requests]
        return {"result": reply("Which request would you like to cancel? Reply with its ID, "
                                "e.g. *cancel request #12*.\n\n" + "\n".join(lines),
                                agent, "leave_service.leave_history")}

    match = next((x for x in history if x["request_id"] == rid), None)
    if not match:
        return {"result": reply(f"Request **#{rid}** isn't one of your leave requests.", agent,
                                "leave_service.leave_history")}
    if match["status"] not in CANCELLABLE:
        return {"result": reply(f"Request **#{rid}** is already **{match['status']}** and can't be cancelled.",
                                agent, "leave_service.leave_history")}

    payload = {"employee_id": emp, "request_id": rid, "cancel_reason": r.get("reason") or ""}
    answer = (
        "Please confirm you want to cancel this leave request:\n\n"
        f"- **Request:** #{rid} ({match['status']})\n"
        f"- **Type:** {match['leave_type']}\n"
        f"- **Dates:** {fmt_date(match['start_date'])} → {fmt_date(match['end_date'])} "
        f"({days(match['days_requested'])})"
    )
    return {"result": reply(answer, agent, "leave_service.cancel_leave",
                            requires_confirmation=True, action="cancel_leave", action_payload=payload)}


async def general_node(state: AgentState) -> AgentState:
    if state["route"]["intent"] == "draft_discarded":
        return {"result": reply("Okay, I've discarded that leave application.", "HR Assistant",
                                source_type="conversation")}
    if ACKNOWLEDGEMENT.fullmatch(state["message"].strip()):
        return {"result": reply("No problem. Let me know if you need anything else.", "HR Assistant",
                                source_type="conversation")}
    small_talk = re.search(r"how are you|how's it going|how are things", state["message"], re.I)
    answer = ("I'm doing well, thanks for asking! " if small_talk else "Hello! ") + (
        "I'm your HR assistant. I can help you with:\n\n"
        "- **HR policies** — e.g. *How many casual leaves can I take?*\n"
        "- **Leave balance and history** — e.g. *What is my remaining leave balance?*\n"
        "- **Applying for or cancelling leave** — e.g. *Apply sick leave for tomorrow*\n"
        "- **Your details** — e.g. *Who is my reporting manager?*\n"
        "- **Holidays** — e.g. *What are the upcoming holidays?*"
    )
    return {"result": reply(answer, "HR Assistant", source_type="conversation")}


async def out_of_scope_node(state: AgentState) -> AgentState:
    answer = (
        "Sorry, that's outside what I can help with. I'm an HR assistant, so I can only answer questions "
        "about HR policies, your leave (balance, history, applying or cancelling), holidays and your "
        "employee details."
    )
    return {"result": reply(answer, "HR Assistant", source_type="out_of_scope")}


ELIGIBILITY_PROMPT = """You are an HR assistant checking an employee's eligibility.
Use ONLY the policy text and employee details below. Give a clear verdict first
(Eligible / Not eligible / Can't determine), then 2-4 short bullet points explaining why,
quoting the specific policy conditions you compared against. If the policy needs information
that is not in the employee details (for example gender or number of children), say exactly
what is missing instead of guessing. Do not invent rules."""


def _tenure(joined: Optional[str]) -> str:
    if not joined:
        return "unknown"
    start, today = date.fromisoformat(joined), date.today()
    months = (today.year - start.year) * 12 + today.month - start.month - (today.day < start.day)
    return f"{months // 12} years {months % 12} months"


async def eligibility_node(state: AgentState) -> AgentState:
    """Policy (RAG) + employee data + leave balance, then an eligibility check."""
    agent, emp, r = "Eligibility Agent", state["employee_id"], state["route"]
    policy, profile, balance = await asyncio.gather(
        clients.query_policy(state["message"], state["session"].policy_history()),
        clients.get_employee_profile(emp),
        clients.get_leave_balance(emp),
        return_exceptions=True,
    )
    if isinstance(policy, Exception):
        if isinstance(policy, ServiceError):
            return {"result": service_failure(policy, agent, emp)}
        raise policy
    if isinstance(profile, ServiceError):
        return {"result": service_failure(profile, agent, emp)}

    job, status = profile["job_details"], profile["employment_status"]
    facts = [
        f"- **Employment status:** {status['employment_status']}",
        f"- **Date of joining:** {fmt_date(status['date_of_joining']) if status.get('date_of_joining') else '—'} "
        f"(tenure {_tenure(status.get('date_of_joining'))})",
        f"- **Designation / grade:** {job['designation']} / {job['grade']}",
        f"- **Work location:** {job.get('work_location') or '—'}",
    ]
    key = BALANCE_KEYS.get(r.get("leave_type") or "")
    if isinstance(balance, dict) and key and key in balance.get("balances", {}):
        b = balance["balances"][key]
        facts.append(f"- **{r['leave_type']} leave balance:** {days(b['available'])} available "
                     f"(entitled {b['entitled']:g}, used {b['used']:g})")
    facts_text = "\n".join(facts)

    verdict = None
    if policy.get("found") and llm.available:
        try:
            verdict = await llm.chat([
                {"role": "system", "content": ELIGIBILITY_PROMPT},
                {"role": "user", "content": (
                    f"Question: {state['message']}\n\nPolicy:\n{policy.get('answer', '')}\n\n"
                    f"Employee details:\n{facts_text.replace('**', '')}\n/no_think")},
            ], max_tokens=400)
        except LLMError:
            verdict = None

    answer = f"**Policy**\n\n{policy.get('answer', '')}\n\n**Your details**\n\n{facts_text}"
    if verdict:
        answer += f"\n\n**Your eligibility**\n\n{verdict}"
    elif policy.get("found"):
        answer += "\n\n_Compare the conditions above with your details to check eligibility._"

    sources = [
        {"document": s.get("source"), "page": s.get("page"),
         "content": f"Relevance score: {s.get('score')}", "score": s.get("score")}
        for s in policy.get("sources", [])
    ]
    return {"result": reply(
        answer, agent, "policy_rag.query + employee_service.profile + leave_service.leave_balance",
        "policy_documents+hr_system", sources=sources,
        data={"profile": profile, "balance": balance if isinstance(balance, dict) else None},
    )}


# ---------------------------------------------------------------- formatters
def format_basic(d: Dict[str, Any]) -> str:
    return (f"**{d['full_name']}** ({d['employee_id']})\n\n"
            f"- **Email:** {d['email']}\n- **Phone:** {d['phone']}")


def format_job(d: Dict[str, Any]) -> str:
    return (f"- **Designation:** {d['designation']}\n- **Department:** {d['department']}\n"
            f"- **Grade:** {d['grade']}\n- **Work location:** {d.get('work_location') or '—'}")


def format_manager(d: Dict[str, Any]) -> str:
    if not d.get("has_manager"):
        return "You don't have a reporting manager on record — you report directly to executive leadership."
    m = d["manager"]
    return (f"Your reporting manager is **{m['full_name']}** ({m['manager_id']}), "
            f"{m['designation']} in {m['department']}.\n\n- **Email:** {m['email']}\n- **Phone:** {m['phone']}")


def format_department(d: Dict[str, Any]) -> str:
    if not d.get("department_name"):
        return "No department is on record for you."
    return (f"You're in **{d['department_name']}** ({d['department_code']}).\n\n"
            f"- **Location:** {d.get('location') or '—'}\n"
            f"- **Members:** {d.get('total_department_members')}\n"
            f"- **About:** {d.get('description') or '—'}")


def format_status(d: Dict[str, Any]) -> str:
    joined = fmt_date(d["date_of_joining"]) if d.get("date_of_joining") else "—"
    return (f"**{d['full_name']}** — employment status: **{d['employment_status']}**\n\n"
            f"- **Date of joining:** {joined}")


def format_profile(d: Dict[str, Any]) -> str:
    return "\n\n".join([
        format_basic(d["basic_info"]),
        "**Job**\n\n" + format_job(d["job_details"]),
        "**Manager**\n\n" + format_manager(d["manager"]),
        "**Status**\n\n" + format_status(d["employment_status"]),
    ])


SECTION_FORMATTERS = {
    "basic": format_basic,
    "job": format_job,
    "manager": format_manager,
    "department": format_department,
    "status": format_status,
}


# ---------------------------------------------------------------- graph
NODES = {
    "policy_query": policy_node,
    "employee_info": employee_node,
    "leave_balance": balance_node,
    "leave_history": history_node,
    "holidays": holidays_node,
    "apply_leave": apply_node,
    "cancel_leave": cancel_node,
    "policy_eligibility": eligibility_node,
    "general": general_node,
    "out_of_scope": out_of_scope_node,
}


def _next(state: AgentState) -> str:
    intent = state["route"]["intent"]
    return intent if intent in NODES else "general"


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("route", route_node)
    for name, fn in NODES.items():
        g.add_node(name, fn)
        g.add_edge(name, END)
    g.set_entry_point("route")
    g.add_conditional_edges("route", _next, {name: name for name in NODES})
    return g.compile()


agent_graph = build_graph()


# ---------------------------------------------------------------- confirmed actions
async def execute_action(action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run an action the user confirmed in the UI. Raises ValueError / ServiceError."""
    payload = payload or {}
    emp = str(payload.get("employee_id") or "").strip()
    if not emp:
        raise ValueError("employee_id is required.")

    if action == "apply_leave":
        body = {k: payload.get(k) for k in ("employee_id", "leave_type", "start_date", "end_date", "reason")}
        body["reason"] = body["reason"] or ""
        res = await clients.apply_leave(body)
        message = (f"Leave request #{res['request_id']} submitted: {days(res['days_requested'])} of "
                   f"{res['leave_type']} leave, {fmt_date(res['start_date'])} → {fmt_date(res['end_date'])}. "
                   f"Status: {res['status']}.")
        return {"success": True, "message": message, "data": res}

    if action == "cancel_leave":
        try:
            rid = int(payload.get("request_id"))
        except (TypeError, ValueError):
            raise ValueError("A valid request_id is required.")
        history = (await clients.get_leave_history(emp)).get("leave_history", [])
        if not any(x["request_id"] == rid for x in history):
            raise ValueError(f"Request #{rid} does not belong to employee {emp}.")
        res = await clients.cancel_leave(rid, payload.get("cancel_reason") or "")
        message = res.get("message", f"Leave request #{rid} cancelled.")
        if res.get("balance_restored"):
            message += f" {days(res.get('days_restored', 0))} returned to your balance."
        return {"success": True, "message": message, "data": res}

    raise ValueError(f"Unknown action '{action}'.")
