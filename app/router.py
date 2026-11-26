"""Intent routing: LLM-based extraction with a rule-based fallback."""
import json
import logging
import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.llm import LLMError, llm

log = logging.getLogger(__name__)

INTENTS = [
    "policy_query",
    "leave_balance",
    "leave_history",
    "holidays",
    "employee_info",
    "apply_leave",
    "cancel_leave",
    "policy_eligibility",
    "general",
    "out_of_scope",
]
INFO_TYPES = ["profile", "basic", "job", "manager", "department", "status"]
LEAVE_TYPES = ["Annual", "Sick", "Casual", "Maternity", "Paternity", "Comp Off"]
STATUSES = ["Pending", "Approved", "Rejected", "Cancelled"]
FIELDS = [
    "employee_info_type", "leave_type", "start_date", "end_date",
    "reason", "request_id", "status_filter", "year", "duration_days",
]

ROUTER_PROMPT = """You route messages for an HR assistant. Today is {today} ({weekday}).
Classify the user's message and extract details. Reply with ONLY a JSON object and no other text:
{{"intent": one of {intents},
 "employee_info_type": one of {info_types} or null,
 "leave_type": one of {leave_types} or null,
 "start_date": "YYYY-MM-DD" or null,
 "end_date": "YYYY-MM-DD" or null,
 "reason": string or null,
 "request_id": integer or null,
 "status_filter": one of {statuses} or null,
 "year": integer or null,
 "duration_days": integer or null}}
Intent guide:
- policy_query: rules, entitlements, eligibility or how a policy works ("How many annual leaves can I take?")
- leave_balance: the user's own remaining or available leave days
- leave_history: the user's own past or existing leave requests and their status
- holidays: the holiday calendar
- employee_info: the user's own profile, manager, department, designation, grade or employment status
- apply_leave: the user wants to apply for or book leave
- cancel_leave: the user wants to cancel a leave request
- policy_eligibility: a policy question combined with whether it applies to the user personally ("Explain maternity leave and my eligibility", "Am I eligible for paternity leave?")
- general: greetings, small talk, thanks, or questions about what the assistant can do
- out_of_scope: anything unrelated to HR, leave, policies, holidays or the user's employment (weather, news, sports, coding, general knowledge)
Resolve relative dates ("tomorrow", "next Monday") against today. For a single day set end_date = start_date.
duration_days is a stated length without an end date ("2 days leave" -> 2).
Only fill fields the user actually stated.{draft_note}"""

DRAFT_NOTE = """
The user has an unfinished leave application: {draft}.
If this message supplies missing details for it (dates, leave type, reason), use intent apply_leave."""

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

LEAVE_TYPE_WORDS = [
    (r"\bcomp(ensatory)?[\s-]?off\b", "Comp Off"),
    (r"\bmaternity\b", "Maternity"),
    (r"\bpaternity\b", "Paternity"),
    (r"\bsick\b|\bmedical\b|\bunwell\b|\bill\b", "Sick"),
    (r"\bcasual\b", "Casual"),
    (r"\bannual\b|\bvacation\b|\bearned\b|\bprivilege\b|\bholiday leave\b", "Annual"),
]


# ---------------------------------------------------------------- dates
def _safe_date(y: int, m: int, d: int) -> Optional[date]:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _upcoming(m: int, d: int, today: date, year: Optional[str]) -> Optional[date]:
    if year:
        return _safe_date(int(year), m, d)
    found = _safe_date(today.year, m, d)
    if found and found < today - timedelta(days=30):
        found = _safe_date(today.year + 1, m, d)
    return found


def extract_dates(text: str, today: date) -> List[date]:
    """Find dates in order of appearance."""
    t = text.lower()
    found: List[Tuple[int, date]] = []

    for m in re.finditer(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", t):
        d = _safe_date(int(m[1]), int(m[2]), int(m[3]))
        if d:
            found.append((m.start(), d))
    for m in re.finditer(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b", t):  # dd/mm/yyyy
        d = _safe_date(int(m[3]), int(m[2]), int(m[1]))
        if d:
            found.append((m.start(), d))
    for m in re.finditer(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?([a-z]{3})[a-z]*\.?,?(?:\s+(\d{4}))?\b", t
    ):
        if m[2] in MONTHS:
            d = _upcoming(MONTHS[m[2]], int(m[1]), today, m[3])
            if d:
                found.append((m.start(), d))
    for m in re.finditer(
        r"\b([a-z]{3})[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b,?(?:\s+(\d{4}))?", t
    ):
        if m[1] in MONTHS:
            d = _upcoming(MONTHS[m[1]], int(m[2]), today, m[3])
            if d:
                found.append((m.start(), d))

    relative = {
        r"\bday after tomorrow\b": today + timedelta(days=2),
        r"\btomorrow\b": today + timedelta(days=1),
        r"\btoday\b": today,
    }
    for pattern, d in relative.items():
        m = re.search(pattern, t)
        if m:
            found.append((m.start(), d))
            t = t[: m.start()] + " " * (m.end() - m.start()) + t[m.end():]

    for m in re.finditer(r"\b(next|this|coming)?\s*(" + "|".join(WEEKDAYS) + r")\b", t):
        delta = (WEEKDAYS.index(m[2]) - today.weekday()) % 7 or 7  # the coming <weekday>
        found.append((m.start(), today + timedelta(days=delta)))

    found.sort(key=lambda x: x[0])
    seen, ordered = set(), []
    for _, d in found:
        if d not in seen:
            seen.add(d)
            ordered.append(d)
    return ordered


def add_working_days(start: date, days: int) -> date:
    """End date covering `days` working days (Mon-Fri) starting at `start`."""
    current, counted = start, 0
    while True:
        if current.weekday() < 5:
            counted += 1
            if counted >= days:
                return current
        current += timedelta(days=1)


def working_days(start: date, end: date) -> int:
    return sum(1 for i in range((end - start).days + 1) if (start + timedelta(i)).weekday() < 5)


# ---------------------------------------------------------------- rules
def _rule_fields(text: str, today: date) -> Dict[str, Any]:
    t = text.lower()
    fields: Dict[str, Any] = {k: None for k in FIELDS}

    for pattern, value in LEAVE_TYPE_WORDS:
        if re.search(pattern, t):
            fields["leave_type"] = value
            break

    dates = extract_dates(text, today)
    if dates:
        fields["start_date"] = dates[0].isoformat()
        if len(dates) > 1:
            fields["end_date"] = dates[1].isoformat()
    span = re.search(r"\b(\d{1,2}|one|two|three|four|five)\s+(?:working\s+|business\s+)?days?\b", t)
    if span:
        n = NUMBER_WORDS.get(span[1]) or int(span[1])
        fields["duration_days"] = n
        if len(dates) == 1:
            fields["end_date"] = add_working_days(dates[0], n).isoformat()

    reason = re.search(r"(?:because(?: of)?|due to|reason\s*[:\-]?\s*(?:is)?)\s+(.+)$", text, re.I)
    if reason:
        fields["reason"] = reason[1].strip().rstrip(".")

    req = re.search(r"(?:#|request\s*(?:id|no\.?|number)?\s*#?\s*|\bid\s*)(\d+)\b", t)
    if req:
        fields["request_id"] = int(req[1])
    elif re.search(r"\bcancel\b", t) and not dates:
        bare = re.search(r"\b(\d{1,6})\b", t)
        if bare and not re.fullmatch(r"20\d{2}", bare[1]):
            fields["request_id"] = int(bare[1])

    for status in STATUSES:
        if status.lower() in t:
            fields["status_filter"] = status
            break

    year = re.search(r"\b(20\d{2})\b", t)
    if year and not dates:
        fields["year"] = int(year[1])

    info_map = [
        (r"manager|report(ing)? to|reports? to|supervisor|boss", "manager"),
        (r"department|team\b", "department"),
        (r"designation|job title|role|grade|position|work location", "job"),
        (r"employment status|joining|joined|active employee|tenure", "status"),
        (r"\bemail\b|\bphone\b|contact|my name", "basic"),
    ]
    for pattern, kind in info_map:
        if re.search(pattern, t):
            fields["employee_info_type"] = kind
            break
    return fields


HR_WORDS = re.compile(
    r"leave|polic|holiday|salary|payroll|manager|department|employee|hr\b|attendance|work from home|wfh|"
    r"benefit|insurance|notice period|probation|resign|appraisal|grade|designation|joining|office|maternity|paternity")
OFF_TOPIC = re.compile(
    r"weather|temperature|rain|news|cricket|football|match|score|movie|song|music|recipe|stock|bitcoin|crypto|"
    r"joke|capital of|president|prime minister|python|code|program|translate|travel|flight|restaurant|game")


def rule_intent(text: str, has_draft: bool = False) -> str:
    t = text.lower().strip()

    if re.fullmatch(r"(hi|hello|hey|hii+|good (morning|afternoon|evening)|thanks?( you)?|thank you|ok(ay)?|bye|never ?mind|no|nope|cool|great|help)[!. ]*", t):
        return "general"
    if re.search(r"\bhow are you\b|\bwho are you\b|\bwhat can you do\b|^(hi|hello|hey)\b[^?]{0,25}$", t):
        return "general"
    if OFF_TOPIC.search(t) and not HR_WORDS.search(t):
        return "out_of_scope"
    if re.search(r"\b(my|me|i|am i|i'm)\b", t) and re.search(r"\beligib|\bentitled\b|\bqualify\b|\bapplies to me\b", t):
        return "policy_eligibility"
    if re.search(r"\bcancel\b|\bwithdraw\b|\brevoke\b", t) and re.search(r"leave|request|#?\d+|application", t):
        return "cancel_leave"
    if re.search(
        r"\b(apply|book|submit|raise)\b.*\b(leave|off|day)|"
        r"\bi (want|need|would like|wish) to (take|apply|go on)\b|"
        r"\b(take|need|want) (a |an |the )?(day|days|leave|time) off\b|"
        r"\bi('m| am) (sick|unwell|ill)\b.*\b(today|tomorrow)\b",
        t,
    ):
        return "apply_leave"
    if re.search(r"\b(take|book|need|want) (a |some )?leave\b", t) and not re.search(r"\bcan i\b|\bhow\b|\bpolicy\b|\ballowed\b", t):
        return "apply_leave"
    if has_draft and (extract_dates(text, date.today()) or any(re.search(p, t) for p, _ in LEAVE_TYPE_WORDS)
                      or re.search(r"because|due to|reason", t)):
        return "apply_leave"
    if re.search(r"\bhow (much|many) (\w+ )?leaves? (do|have) i\b|\bleaves? (do|have) i (have|got)( left)?\b", t):
        return "leave_balance"
    if re.search(r"\b(balance|remaining|left|available|how many .* (do i have|have i got))\b", t) and \
            re.search(r"\bmy\b|\bi\b|\bleft\b|\bremaining\b|\bbalance\b", t) and \
            not re.search(r"\b(policy|allowed|entitled to|eligible|can i take)\b", t):
        return "leave_balance"
    if re.search(r"\bhistory\b|\bpast leaves?\b|\bprevious leaves?\b|\bmy (leave )?(requests|applications)\b|"
                 r"\bstatus of my\b|\bmy (pending|approved|rejected|cancelled) leaves?\b|\bshow my leaves?\b", t):
        return "leave_history"
    if re.search(r"\bholidays?\b|\bholiday calendar\b|\bpublic holiday", t) and "policy" not in t:
        return "holidays"
    if re.search(r"\b(my|i)\b", t) and re.search(
        r"manager|report(ing)? to|supervisor|department|designation|job title|grade|profile|"
        r"my details|employment status|joining date|date of joining|work location|my email|my phone", t
    ):
        return "employee_info"
    return "policy_query"


# ---------------------------------------------------------------- llm
def _parse_json(text: str) -> Optional[Dict[str, Any]]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _clean(raw: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {k: None for k in FIELDS}
    out["intent"] = raw.get("intent") if raw.get("intent") in INTENTS else None
    if raw.get("employee_info_type") in INFO_TYPES:
        out["employee_info_type"] = raw["employee_info_type"]
    if raw.get("leave_type") in LEAVE_TYPES:
        out["leave_type"] = raw["leave_type"]
    if raw.get("status_filter") in STATUSES:
        out["status_filter"] = raw["status_filter"]
    for key in ("start_date", "end_date"):
        try:
            out[key] = date.fromisoformat(str(raw.get(key))).isoformat()
        except ValueError:
            pass
    for key in ("request_id", "year", "duration_days"):
        try:
            out[key] = int(raw[key]) if raw.get(key) is not None else None
        except (TypeError, ValueError):
            pass
    if isinstance(raw.get("reason"), str) and raw["reason"].strip():
        out["reason"] = raw["reason"].strip()
    return out


async def _llm_route(text: str, today: date, draft: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not (settings.use_llm_router and llm.available):
        return None
    prompt = ROUTER_PROMPT.format(
        today=today.isoformat(),
        weekday=today.strftime("%A"),
        intents=json.dumps(INTENTS),
        info_types=json.dumps(INFO_TYPES),
        leave_types=json.dumps(LEAVE_TYPES),
        statuses=json.dumps(STATUSES),
        draft_note=DRAFT_NOTE.format(draft=json.dumps(draft)) if draft is not None else "",
    )
    try:
        reply = await llm.chat(
            [{"role": "system", "content": prompt}, {"role": "user", "content": f"{text}\n/no_think"}]
        )
    except LLMError as e:
        log.warning("LLM router failed, using rules: %s", e)
        return None
    parsed = _parse_json(reply)
    if not parsed:
        log.warning("LLM router returned non-JSON, using rules: %r", reply[:200])
        return None
    cleaned = _clean(parsed)
    return cleaned if cleaned["intent"] else None


async def route(text: str, draft: Optional[Dict[str, Any]] = None, today: Optional[date] = None) -> Dict[str, Any]:
    """Return {"intent", "router", <extracted fields>}."""
    today = today or date.today()
    rules = _rule_fields(text, today)
    llm_result = await _llm_route(text, today, draft)

    if llm_result:
        result = llm_result
        for key in FIELDS:  # rules fill anything the LLM left empty
            if result.get(key) is None and rules.get(key) is not None:
                result[key] = rules[key]
        result["router"] = "llm"
    else:
        result = {**rules, "intent": rule_intent(text, has_draft=draft is not None), "router": "rules"}

    if result["start_date"] and not result["end_date"]:
        result["end_date"] = (
            add_working_days(date.fromisoformat(result["start_date"]), result["duration_days"]).isoformat()
            if result.get("duration_days") else result["start_date"]
        )
    return result
