"""JSON-backed employee, authentication, and leave operations for the demo app."""
import base64
import hashlib
import hmac
import json
import os
import tempfile
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATABASE_PATH = Path(os.getenv("HR_DATABASE_PATH", str(DATA_DIR / "hr_database.json"))).expanduser()
SEED_PATH = DATA_DIR / "hr_seed.json"
DEMO_PASSWORD = os.getenv("HR_DEMO_PASSWORD", "Welcome123!")
PASSWORD_ITERATIONS = 260_000
LEAVE_TYPES = {
    "annual": "Annual",
    "sick": "Sick",
    "casual": "Casual",
    "maternity": "Maternity",
    "paternity": "Paternity",
    "comp_off": "Comp Off",
}


class HRStoreError(ValueError):
    """Raised when a requested HR operation violates its business rules."""


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS).hex()


def _date(value: Any) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise HRStoreError("Use dates in YYYY-MM-DD format.") from exc


def _business_days(start: date, end: date, holidays: set[date]) -> int:
    days = 0
    current = start
    while current <= end:
        if current.weekday() < 5 and current not in holidays:
            days += 1
        current += timedelta(days=1)
    return days


class HRStore:
    """Small local JSON store. Use a database server for multi-user production deployments."""

    _lock = threading.RLock()

    def __init__(self, path: Path = DATABASE_PATH, seed_path: Path = SEED_PATH):
        self.path = Path(path)
        self.seed_path = Path(seed_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._initialize()
        else:
            self._migrate()

    def _initialize(self) -> None:
        if not self.seed_path.exists():
            raise FileNotFoundError(f"HR seed data not found: {self.seed_path}")
        with self.seed_path.open("r", encoding="utf-8") as source:
            data = json.load(source)
        for employee in data["employees"]:
            salt = os.urandom(16)
            employee["password_salt"] = base64.b64encode(salt).decode("ascii")
            employee["password_hash"] = _hash_password(DEMO_PASSWORD, salt)
        data.setdefault("leave_requests", [])
        data.setdefault("holidays", [])
        data["next_request_id"] = max(
            (int(item["request_id"]) for item in data["leave_requests"]), default=0
        ) + 1
        data["schema_version"] = 1
        self._write(data)

    def _migrate(self) -> None:
        data = self._read()
        if int(data.get("schema_version", 0)) >= 1:
            return
        with self.seed_path.open("r", encoding="utf-8") as source:
            seed = json.load(source)
        if not data.get("leave_requests"):
            data["leave_requests"] = seed.get("leave_requests", [])
        data.setdefault("holidays", seed.get("holidays", []))
        for employee in data.get("employees", []):
            if "password_hash" not in employee or "password_salt" not in employee:
                salt = os.urandom(16)
                employee["password_salt"] = base64.b64encode(salt).decode("ascii")
                employee["password_hash"] = _hash_password(DEMO_PASSWORD, salt)
        max_id = max(
            (int(item["request_id"]) for item in data["leave_requests"]), default=0
        )
        data["next_request_id"] = max(int(data.get("next_request_id", 1)), max_id + 1)
        data["schema_version"] = 1
        self._write(data)

    def _read(self) -> Dict[str, Any]:
        try:
            with self.path.open("r", encoding="utf-8") as source:
                return json.load(source)
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Unable to read HR data file {self.path}: {exc}") from exc

    def _write(self, data: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_name: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.path.parent, delete=False, suffix=".tmp"
            ) as output:
                temp_name = output.name
                json.dump(data, output, ensure_ascii=False, indent=2)
                output.write("\n")
                output.flush()
                os.fsync(output.fileno())
            os.replace(temp_name, self.path)
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)

    @staticmethod
    def _employee(data: Dict[str, Any], employee_id: str) -> Dict[str, Any]:
        employee = next(
            (item for item in data["employees"] if item["employee_id"].casefold() == employee_id.strip().casefold()),
            None,
        )
        if employee is None:
            raise HRStoreError("I couldn't find that employee ID.")
        return employee

    def authenticate(self, employee_id: str, password: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            data = self._read()
            try:
                employee = self._employee(data, employee_id)
            except HRStoreError:
                return None
            if employee.get("employment_status") != "Active":
                return None
            try:
                salt = base64.b64decode(employee["password_salt"])
                expected = employee["password_hash"]
            except (KeyError, ValueError):
                return None
            if not hmac.compare_digest(_hash_password(password, salt), expected):
                return None
            return self.get_profile(employee["employee_id"])

    def get_profile(self, employee_id: str) -> Dict[str, Any]:
        with self._lock:
            data = self._read()
            employee = dict(self._employee(data, employee_id))
            employee.pop("password_salt", None)
            employee.pop("password_hash", None)
            manager_id = employee.get("manager_id")
            manager = next(
                (item for item in data["employees"] if item["employee_id"] == manager_id),
                None,
            )
            employee["manager"] = (
                {
                    "employee_id": manager["employee_id"],
                    "full_name": f"{manager['first_name']} {manager['last_name']}",
                    "email": manager["email"],
                    "designation": manager["designation"],
                    "department": manager["department"],
                }
                if manager
                else None
            )
            return employee

    def _balance_for(self, employee: Dict[str, Any], year: int) -> Dict[str, Any]:
        balances = employee.setdefault("leave_balances", {})
        key = str(year)
        if key not in balances:
            grade = employee.get("grade", "L3")
            annual = 25 if grade.startswith("E") else 22 if grade.startswith("M") else 20 if grade in {"L5", "L6"} else 18
            balances[key] = {
                "annual": {"entitled": annual, "used": 0, "carried_forward": 0},
                "sick": {"entitled": 10, "used": 0},
                "casual": {"entitled": 5, "used": 0},
                "maternity": {"entitled": 0, "used": 0},
                "paternity": {"entitled": 0, "used": 0},
                "comp_off": {"entitled": 0, "used": 0},
            }
        return balances[key]

    def get_balance(self, employee_id: str, year: Optional[int] = None) -> Dict[str, Any]:
        year = year or date.today().year
        with self._lock:
            data = self._read()
            employee = self._employee(data, employee_id)
            balances = self._balance_for(employee, year)
            pending: Dict[str, float] = {key: 0.0 for key in LEAVE_TYPES}
            for request in data["leave_requests"]:
                if (
                    request["employee_id"] == employee["employee_id"]
                    and request["status"] == "Pending"
                    and int(request["start_date"][:4]) == year
                ):
                    type_key = request["leave_type_key"]
                    pending[type_key] += float(request["days_requested"])
            summary: Dict[str, Any] = {"year": year, "leave_types": {}}
            for key, label in LEAVE_TYPES.items():
                item = balances.get(key, {"entitled": 0, "used": 0})
                carried = float(item.get("carried_forward", 0))
                entitled = float(item.get("entitled", 0))
                used = float(item.get("used", 0))
                reserved = pending[key]
                summary["leave_types"][label] = {
                    "entitled": entitled,
                    "carried_forward": carried,
                    "used": used,
                    "pending": reserved,
                    "available": round(entitled + carried - used - reserved, 1),
                }
            summary["total_available"] = round(
                sum(item["available"] for item in summary["leave_types"].values()), 1
            )
            return summary

    def get_history(self, employee_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            data = self._read()
            employee = self._employee(data, employee_id)
            records = [
                dict(item)
                for item in data["leave_requests"]
                if item["employee_id"] == employee["employee_id"]
            ]
            return sorted(records, key=lambda item: item["applied_at"], reverse=True)

    def get_holidays(self, year: int, location: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            data = self._read()
            items = [item for item in data["holidays"] if int(item["date"][:4]) == year]
            if location:
                items = [item for item in items if item["location"] == "All Locations" or item["location"].casefold() == location.casefold()]
            return sorted(items, key=lambda item: item["date"])

    def _holidays_for_location(self, data: Dict[str, Any], year: int, employee: Dict[str, Any]) -> set[date]:
        location = employee.get("work_location", "")
        dates = set()
        for item in data["holidays"]:
            if int(item["date"][:4]) != year:
                continue
            if item["location"] == "All Locations" or item["location"].casefold() in location.casefold():
                dates.add(date.fromisoformat(item["date"]))
        return dates

    def apply_leave(
        self,
        employee_id: str,
        leave_type: str,
        start_date: Any,
        end_date: Any,
        reason: str = "",
    ) -> Dict[str, Any]:
        start = _date(start_date)
        end = _date(end_date)
        if end < start:
            raise HRStoreError("The end date must be on or after the start date.")
        if start < date.today():
            raise HRStoreError("Leave applications cannot start in the past.")
        if start.year != end.year:
            raise HRStoreError("For this demo, a leave request must stay within one calendar year.")
        type_key = next((key for key, label in LEAVE_TYPES.items() if label.casefold() == leave_type.strip().casefold()), None)
        if type_key is None:
            raise HRStoreError(f"Choose a leave type from: {', '.join(LEAVE_TYPES.values())}.")
        if len(reason.strip()) > 500:
            raise HRStoreError("Please keep the reason under 500 characters.")

        with self._lock:
            data = self._read()
            employee = self._employee(data, employee_id)
            if employee["employment_status"] != "Active":
                raise HRStoreError("Only active employees can apply for leave.")
            for request in data["leave_requests"]:
                if request["employee_id"] != employee["employee_id"] or request["status"] not in {"Pending", "Approved"}:
                    continue
                existing_start = date.fromisoformat(request["start_date"])
                existing_end = date.fromisoformat(request["end_date"])
                if start <= existing_end and end >= existing_start:
                    raise HRStoreError(f"These dates overlap with leave request #{request['request_id']}.")

            requested = _business_days(start, end, self._holidays_for_location(data, start.year, employee))
            if requested <= 0:
                raise HRStoreError("The selected dates contain no working days after weekends and holidays are excluded.")
            balances = self._balance_for(employee, start.year)
            entitlement = balances.get(type_key, {"entitled": 0, "used": 0})
            carry = float(entitlement.get("carried_forward", 0)) if type_key == "annual" else 0.0
            used = float(entitlement.get("used", 0))
            already_pending = sum(
                float(item["days_requested"])
                for item in data["leave_requests"]
                if item["employee_id"] == employee["employee_id"]
                and item["leave_type_key"] == type_key
                and item["status"] == "Pending"
                and int(item["start_date"][:4]) == start.year
            )
            available = float(entitlement.get("entitled", 0)) + carry - used - already_pending
            if requested > available:
                raise HRStoreError(f"Insufficient {LEAVE_TYPES[type_key]} balance: {available:g} available, {requested} requested.")

            request = {
                "request_id": int(data.get("next_request_id", 1)),
                "employee_id": employee["employee_id"],
                "leave_type": LEAVE_TYPES[type_key],
                "leave_type_key": type_key,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "days_requested": requested,
                "reason": reason.strip(),
                "status": "Pending",
                "applied_at": datetime.now().isoformat(timespec="seconds"),
            }
            data["leave_requests"].append(request)
            data["next_request_id"] = request["request_id"] + 1
            self._write(data)
            return dict(request)

    def cancel_leave(self, employee_id: str, request_id: int) -> Dict[str, Any]:
        with self._lock:
            data = self._read()
            employee = self._employee(data, employee_id)
            request = next(
                (item for item in data["leave_requests"] if item["request_id"] == int(request_id) and item["employee_id"] == employee["employee_id"]),
                None,
            )
            if request is None:
                raise HRStoreError("I couldn't find that leave request in your history.")
            if request["status"] != "Pending":
                raise HRStoreError("Only pending leave requests can be cancelled in this demo.")
            request["status"] = "Cancelled"
            request["cancelled_at"] = datetime.now().isoformat(timespec="seconds")
            self._write(data)
            return dict(request)
