"""Streamlit front end for the HR policy and employee assistant."""
from datetime import date, timedelta
from typing import Any, Dict, Optional

import streamlit as st

from app.agent import route_message
from app.hr_store import DEMO_PASSWORD, HRStore, HRStoreError, LEAVE_TYPES


st.set_page_config(page_title="People Desk | HR Assistant", page_icon="P", layout="wide")


@st.cache_resource
def get_store() -> HRStore:
    return HRStore()


def _apply_styles() -> None:
    st.markdown(
        """
        <style>
        :root { --ink: #172b2a; --muted: #62706d; --line: #dce5df; --paper: #f5f8f5; --green: #176b55; --mint: #e4f1e9; }
        .stApp { background: var(--paper); color: var(--ink); font-family: Aptos, "Segoe UI", sans-serif; }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stSidebar"] { background: #eaf1ec; border-right: 1px solid var(--line); }
        .block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 3rem; }
        h1, h2, h3 { color: var(--ink); letter-spacing: 0; }
        div[data-testid="stMetric"] { background: #fff; border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px; }
        div[data-testid="stMetricLabel"] { color: var(--muted); }
        .eyebrow { color: var(--green); font-size: .78rem; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; }
        .login-panel { background: white; border: 1px solid var(--line); border-radius: 8px; padding: 1.5rem; }
        div.stButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"] { background: var(--green); border-color: var(--green); }
        div[data-testid="stChatMessage"] { border: 1px solid var(--line); border-radius: 8px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _append_message(role: str, content: str, sources: Optional[list] = None) -> None:
    st.session_state.messages.append({"role": role, "content": content, "sources": sources or []})


def _login(store: HRStore) -> None:
    left, center, right = st.columns([1, 1.15, 1])
    with center:
        st.markdown('<p class="eyebrow">People Desk · Employee services</p>', unsafe_allow_html=True)
        st.title("Your HR, in one conversation.")
        st.caption("Sign in with your employee account to view your information and manage leave.")
        with st.container(border=True):
            with st.form("login_form"):
                employee_id = st.text_input("Employee ID", value="EMP1007", placeholder="EMP1007")
                password = st.text_input("Password", type="password", placeholder="Your password")
                submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
            if submitted:
                profile = store.authenticate(employee_id, password)
                if profile:
                    st.session_state.employee_id = profile["employee_id"]
                    st.session_state.messages = [{
                        "role": "assistant",
                        "content": f"Welcome back, {profile['first_name']}. What can I help you with?",
                        "sources": [],
                    }]
                    st.session_state.pending_action = None
                    st.rerun()
                st.error("We couldn’t sign you in. Check your employee ID and password.")
        st.caption(f"Local demo account: EMP1007 · password: {DEMO_PASSWORD}")
        st.caption("Demo authentication only. Do not use real employee credentials in this prototype.")


def _next_weekday(offset: int = 7) -> date:
    value = date.today() + timedelta(days=offset)
    while value.weekday() >= 5:
        value += timedelta(days=1)
    return value


def _render_pending_action(store: HRStore, employee_id: str) -> None:
    action = st.session_state.get("pending_action")
    if not action:
        return
    kind = action.get("kind")
    with st.container(border=True):
        if kind == "apply_leave":
            st.subheader("Review leave application")
            leave_labels = list(LEAVE_TYPES.values())
            suggested_type = action.get("leave_type")
            type_index = leave_labels.index(suggested_type) if suggested_type in leave_labels else 0
            default_start = date.fromisoformat(action["start_date"]) if action.get("start_date") else _next_weekday()
            default_end = date.fromisoformat(action["end_date"]) if action.get("end_date") else default_start + timedelta(days=1)
            with st.form("confirm_leave_form"):
                leave_type = st.selectbox("Leave type", leave_labels, index=type_index)
                start_date = st.date_input("First day", value=default_start)
                end_date = st.date_input("Last day", value=default_end)
                reason = st.text_input("Reason (optional)", value=action.get("reason", ""), max_chars=500)
                available = store.get_balance(employee_id, start_date.year)["leave_types"][leave_type]["available"]
                st.caption(f"Available before this request: {available:g} {leave_type.lower()} day(s). Weekends and listed holidays are excluded.")
                confirmed = st.form_submit_button("Confirm and apply", type="primary")
            if confirmed:
                try:
                    request = store.apply_leave(employee_id, leave_type, start_date, end_date, reason)
                    _append_message(
                        "assistant",
                        f"Leave request **#{request['request_id']}** submitted for {request['days_requested']:g} {leave_type.lower()} day(s), {request['start_date']} to {request['end_date']}. It is **Pending** and has been reserved from your available balance.",
                    )
                    st.session_state.pending_action = None
                    st.rerun()
                except HRStoreError as exc:
                    st.error(str(exc))
        elif kind == "cancel_leave":
            pending = [item for item in store.get_history(employee_id) if item["status"] == "Pending"]
            st.subheader("Review cancellation")
            if not pending:
                st.info("You don’t have any pending requests to cancel.")
                if st.button("Close", key="close_cancel"):
                    st.session_state.pending_action = None
                    st.rerun()
                return
            labels = {
                item["request_id"]: f"#{item['request_id']} · {item['leave_type']} · {item['start_date']} to {item['end_date']} ({item['days_requested']:g} days)"
                for item in pending
            }
            requested_id = action.get("request_id")
            ids = list(labels)
            selected_index = ids.index(requested_id) if requested_id in ids else 0
            with st.form("confirm_cancel_form"):
                request_id = st.selectbox("Pending request", ids, index=selected_index, format_func=lambda value: labels[value])
                confirmed = st.form_submit_button("Confirm cancellation", type="primary")
            if confirmed:
                try:
                    request = store.cancel_leave(employee_id, request_id)
                    _append_message("assistant", f"Request **#{request['request_id']}** has been cancelled. Its reserved days are available again.")
                    st.session_state.pending_action = None
                    st.rerun()
                except HRStoreError as exc:
                    st.error(str(exc))


def _render_chat(store: HRStore, employee_id: str) -> None:
    st.markdown('<p class="eyebrow">HR assistant</p>', unsafe_allow_html=True)
    st.subheader("Ask, check, or request")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            for source in message.get("sources", []):
                st.caption(f"Source: {source['source']} · page {source['page']}")

    prompt = st.chat_input("Ask about a policy, your leave, or employee details…")
    if prompt:
        _append_message("user", prompt)
        reply = route_message(prompt, employee_id, store)
        _append_message("assistant", reply.text, reply.sources)
        st.session_state.pending_action = reply.action
        st.rerun()
    _render_pending_action(store, employee_id)


def _render_leave(store: HRStore, employee_id: str) -> None:
    summary = store.get_balance(employee_id)
    st.markdown('<p class="eyebrow">My time away</p>', unsafe_allow_html=True)
    st.subheader(f"Leave balance · {summary['year']}")
    items = list(summary["leave_types"].items())
    for offset in range(0, len(items), 3):
        columns = st.columns(3)
        for column, (label, balance) in zip(columns, items[offset : offset + 3]):
            with column:
                st.metric(f"{label} available", f"{balance['available']:g} days", delta=f"{balance['pending']:g} pending" if balance["pending"] else None)
                st.caption(f"{balance['used']:g} used of {balance['entitled'] + balance['carried_forward']:g} total")

    st.divider()
    st.subheader("Leave history")
    history = store.get_history(employee_id)
    if history:
        rows = [{key: item[key] for key in ("request_id", "leave_type", "start_date", "end_date", "days_requested", "status", "reason")} for item in history]
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.caption("No leave requests yet.")

    st.divider()
    profile = store.get_profile(employee_id)
    holidays = store.get_holidays(date.today().year, profile["work_location"].split(",", 1)[0])
    st.subheader(f"Holiday calendar · {date.today().year}")
    if holidays:
        st.dataframe(holidays, hide_index=True, width="stretch")
    else:
        st.caption("No holiday dates loaded for this year.")


def _render_profile(store: HRStore, employee_id: str) -> None:
    profile = store.get_profile(employee_id)
    st.markdown('<p class="eyebrow">Employee record</p>', unsafe_allow_html=True)
    st.subheader(f"{profile['first_name']} {profile['last_name']}")
    st.caption(f"{profile['designation']} · {profile['department']}")
    left, right = st.columns(2)
    with left:
        st.write("**Employee ID**", profile["employee_id"])
        st.write("**Work email**", profile["email"])
        st.write("**Phone**", profile["phone"])
        st.write("**Employment status**", profile["employment_status"])
    with right:
        st.write("**Grade**", profile["grade"])
        st.write("**Department**", f"{profile['department']} ({profile['department_code']})")
        st.write("**Work location**", profile["work_location"])
        manager = profile.get("manager")
        st.write("**Manager**", f"{manager['full_name']} · {manager['designation']}" if manager else "Not listed")


def main() -> None:
    _apply_styles()
    store = get_store()
    if not st.session_state.get("employee_id"):
        _login(store)
        return

    employee_id = st.session_state.employee_id
    profile = store.get_profile(employee_id)
    balance = store.get_balance(employee_id)
    st.sidebar.markdown('<p class="eyebrow">People Desk</p>', unsafe_allow_html=True)
    st.sidebar.subheader(f"{profile['first_name']} {profile['last_name']}")
    st.sidebar.caption(f"{profile['employee_id']} · {profile['department']}")
    st.sidebar.metric("Annual leave available", f"{balance['leave_types']['Annual']['available']:g} days")
    st.sidebar.caption(f"{profile['designation']} · {profile['employment_status']}")
    if st.sidebar.button("Sign out", use_container_width=True):
        for key in ("employee_id", "messages", "pending_action"):
            st.session_state.pop(key, None)
        st.rerun()

    st.markdown('<p class="eyebrow">Employee self-service</p>', unsafe_allow_html=True)
    st.title("People Desk")
    st.caption("Policies, employee information, and leave operations in one place.")
    annual = balance["leave_types"]["Annual"]
    pending_days = sum(item["pending"] for item in balance["leave_types"].values())
    metrics = st.columns(3)
    metrics[0].metric("Annual available", f"{annual['available']:g} days")
    metrics[1].metric("Annual used", f"{annual['used']:g} days")
    metrics[2].metric("Leave pending", f"{pending_days:g} days")

    chat_tab, leave_tab, profile_tab = st.tabs(["Assistant", "Leave & holidays", "My profile"])
    with chat_tab:
        _render_chat(store, employee_id)
    with leave_tab:
        _render_leave(store, employee_id)
    with profile_tab:
        _render_profile(store, employee_id)


if __name__ == "__main__":
    main()
