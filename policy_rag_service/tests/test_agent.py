import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent import route_message
from app.hr_store import HRStore


def test_balance_intent_uses_employee_store(tmp_path):
    reply = route_message("How much annual leave do I have left?", "EMP1007", HRStore(tmp_path / "hr.json"))
    assert "13 available" in reply.text


def test_leave_application_routes_to_confirmation_without_mutating_data(tmp_path):
    store = HRStore(tmp_path / "hr.json")
    history_before = store.get_history("EMP1007")
    reply = route_message(
        "Apply for annual leave from 2027-01-11 to 2027-01-12 because family trip",
        "EMP1007",
        store,
    )
    assert reply.action == {
        "kind": "apply_leave",
        "leave_type": "Annual",
        "start_date": "2027-01-11",
        "end_date": "2027-01-12",
        "reason": "family trip",
    }
    assert store.get_history("EMP1007") == history_before


def test_employee_profile_and_out_of_scope_intents(tmp_path):
    store = HRStore(tmp_path / "hr.json")
    assert "EMP1007" in route_message("What is my employee ID?", "EMP1007", store).text
    assert "outside my HR services" in route_message("What is the weather?", "EMP1007", store).text
