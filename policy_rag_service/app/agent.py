"""Deterministic intent routing for the local HR assistant MVP."""
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

from app.hr_store import HRStore, LEAVE_TYPES


@dataclass
class AgentReply:
    text: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    action: Optional[Dict[str, Any]] = None


def _leave_type(text: str) -> Optional[str]:
    value = text.casefold().replace("compensatory off", "comp off")
    for key, label in LEAVE_TYPES.items():
        if re.search(rf"\b{re.escape(label.casefold())}\b", value):
            return label
    if re.search(r"\b(earned|vacation) leave\b", value):
        return "Annual"
    if re.search(r"\bmedical leave\b", value):
        return "Sick"
    return None


def _date_values(text: str) -> List[str]:
    return re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text)


def _reason(text: str) -> str:
    match = re.search(r"\b(?:because|reason\s*(?:is|:)?)\s+(.+)$", text, re.IGNORECASE)
    return match.group(1).strip(" .") if match else ""


def _balance_reply(store: HRStore, employee_id: str) -> str:
    summary = store.get_balance(employee_id)
    rows = [f"**Leave balance for {summary['year']}**"]
    for label, item in summary["leave_types"].items():
        if item["entitled"] or item["carried_forward"] or item["used"] or item["pending"]:
            rows.append(
                f"- **{label}:** {item['available']:g} available; "
                f"{item['used']:g} used, {item['pending']:g} pending"
            )
    rows.append("Pending requests reserve days from your available balance.")
    return "\n".join(rows)


def route_message(message: str, employee_id: str, store: HRStore) -> AgentReply:
    text = message.strip()
    normalized = text.casefold()
    if not text:
        return AgentReply("Tell me what you need help with.")

    if re.fullmatch(r"(?:hi|hello|hey|good morning|good afternoon|good evening)[!. ]*", normalized):
        return AgentReply("Hello. I can help with company policies, your profile, leave balances, leave history, and leave requests.")

    if any(word in normalized for word in ("weather", "football", "stock price", "write code", "recipe")):
        return AgentReply("That’s outside my HR services. I can help with company policies, employee information, leave balances, history, and leave requests.")

    apply_intent = re.search(r"\b(?:apply|submit|request|book)\b.*\bleave\b", normalized)
    if not apply_intent:
        apply_intent = re.search(r"\bi need\b.*\bleave\b", normalized)
    if apply_intent:
        dates = _date_values(text)
        action = {
            "kind": "apply_leave",
            "leave_type": _leave_type(text),
            "start_date": dates[0] if dates else None,
            "end_date": dates[1] if len(dates) > 1 else None,
            "reason": _reason(text),
        }
        return AgentReply(
            "I’ve prepared a leave request. Review the type and dates below, then confirm before it is submitted.",
            action=action,
        )

    cancel_match = re.search(r"\bcancel\b.*\bleave\b|\bcancel\s+(?:request\s*)?#?(\d+)", normalized)
    if cancel_match:
        id_match = re.search(r"\b(?:request\s*)?#?(\d+)\b", normalized)
        return AgentReply(
            "Choose the pending request you want to cancel, then confirm.",
            action={"kind": "cancel_leave", "request_id": int(id_match.group(1)) if id_match else None},
        )

    if any(phrase in normalized for phrase in ("balance", "available leave", "leave left", "do i have", "how much leave", "how many leaves have i", "remaining leave")):
        return AgentReply(_balance_reply(store, employee_id))

    if any(word in normalized for word in ("history", "requests have i", "leaves have i applied", "leave applications")):
        history = store.get_history(employee_id)
        if not history:
            return AgentReply("You don’t have any leave requests in your history yet.")
        rows = ["**Your leave requests**"]
        for item in history[:10]:
            rows.append(
                f"- #{item['request_id']} · {item['leave_type']} · {item['start_date']} to "
                f"{item['end_date']} · {item['days_requested']:g} day(s) · {item['status']}"
            )
        return AgentReply("\n".join(rows))

    profile_words = ("employee id", "my id", "my profile", "my details", "my email", "my phone", "my manager", "who is my manager", "job details", "my department", "my designation", "employment status")
    if any(phrase in normalized for phrase in profile_words):
        profile = store.get_profile(employee_id)
        if "manager" in normalized:
            manager = profile.get("manager")
            answer = (
                f"Your manager is **{manager['full_name']}**, {manager['designation']} "
                f"({manager['department']})."
                if manager
                else "Your profile does not list a reporting manager."
            )
        elif "employee id" in normalized or "my id" in normalized:
            answer = f"Your employee ID is **{profile['employee_id']}**."
        elif "email" in normalized:
            answer = f"Your work email is **{profile['email']}**."
        elif "phone" in normalized:
            answer = f"Your work phone is **{profile['phone']}**."
        else:
            answer = (
                f"**{profile['first_name']} {profile['last_name']}** · {profile['employee_id']}\n\n"
                f"{profile['designation']} · {profile['department']} ({profile['grade']})\n\n"
                f"Manager: {profile['manager']['full_name'] if profile['manager'] else 'Not listed'}\n\n"
                f"Status: {profile['employment_status']} · {profile['work_location']}"
            )
        return AgentReply(answer)

    if "holiday" in normalized or "calendar" in normalized:
        profile = store.get_profile(employee_id)
        location = profile["work_location"].split(",", 1)[0]
        holidays = store.get_holidays(date.today().year, location)
        if not holidays:
            return AgentReply(f"I don’t have holidays loaded for {date.today().year} yet.")
        lines = [f"**{date.today().year} holidays for {location}**"]
        lines.extend(f"- {item['date']} · {item['name']} ({item['type']})" for item in holidays)
        return AgentReply("\n".join(lines))

    if any(word in normalized for word in ("policy", "leave", "maternity", "paternity", "parental", "eligibility", "carry forward", "carry-forward", "insurance", "harassment", "remote work", "work from home", "vacation")):
        try:
            from app.rag import PolicyRAG

            result = PolicyRAG().answer(text)
            return AgentReply(result.answer, result.sources)
        except Exception:
            return AgentReply(
                "I can’t generate a policy answer right now. Check that the local policy index is built and the LLM API key and CA certificate are configured."
            )

    return AgentReply("I can help with HR policies, your employee profile, leave balances, leave history, holiday dates, and leave applications. What would you like to check?")
