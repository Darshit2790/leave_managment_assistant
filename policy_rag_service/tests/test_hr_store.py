import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from app.hr_store import HRStore, HRStoreError


def _next_weekday(offset=7):
    current = date(date.today().year + 1, 1, 5)
    while current.weekday() >= 5:
        current += timedelta(days=1)
    return current


def test_login_and_profile_exclude_password_fields(tmp_path):
    store = HRStore(tmp_path / "hr.json")
    profile = store.authenticate("EMP1007", "Welcome123!")
    assert profile["employee_id"] == "EMP1007"
    assert "password_hash" not in profile
    assert store.authenticate("EMP1007", "incorrect") is None


def test_pending_leave_reserves_balance_and_cancel_releases_it(tmp_path):
    store = HRStore(tmp_path / "hr.json")
    start = _next_weekday()
    end = start + timedelta(days=1)
    while end.weekday() >= 5:
        end += timedelta(days=1)

    before = store.get_balance("EMP1007", start.year)["leave_types"]["Annual"]["available"]
    request = store.apply_leave("EMP1007", "Annual", start, end, "Family trip")
    after = store.get_balance("EMP1007", start.year)["leave_types"]["Annual"]["available"]
    assert request["status"] == "Pending"
    assert after == before - request["days_requested"]
    assert len(store.get_history("EMP1007")) == 5

    store.cancel_leave("EMP1007", request["request_id"])
    restored = store.get_balance("EMP1007", start.year)["leave_types"]["Annual"]["available"]
    assert restored == before


def test_rejects_insufficient_balance_and_overlapping_dates(tmp_path):
    store = HRStore(tmp_path / "hr.json")
    start = _next_weekday()
    end = start + timedelta(days=1)
    while end.weekday() >= 5:
        end += timedelta(days=1)

    with pytest.raises(HRStoreError, match="Insufficient"):
        store.apply_leave("EMP1007", "Annual", start, start + timedelta(days=30))

    store.apply_leave("EMP1007", "Annual", start, end)
    with pytest.raises(HRStoreError, match="overlap"):
        store.apply_leave("EMP1007", "Sick", start, end)


def test_migration_adds_demo_history_without_replacing_existing_requests(tmp_path):
    path = tmp_path / "hr.json"
    original = HRStore(path)
    data = original._read()
    data["leave_requests"] = []
    data["next_request_id"] = 1
    data.pop("schema_version")
    original._write(data)

    migrated = HRStore(path)
    assert len(migrated.get_history("EMP1007")) == 4
    assert migrated._read()["next_request_id"] == 5

    data = migrated._read()
    data["leave_requests"].append({
        "request_id": 5,
        "employee_id": "EMP1007",
        "leave_type": "Annual",
        "leave_type_key": "annual",
        "start_date": "2027-01-11",
        "end_date": "2027-01-11",
        "days_requested": 1,
        "reason": "Existing request",
        "status": "Pending",
        "applied_at": "2026-11-27T12:00:00",
    })
    data.pop("schema_version")
    migrated._write(data)
    migrated_again = HRStore(path)
    assert len(migrated_again.get_history("EMP1007")) == 5
