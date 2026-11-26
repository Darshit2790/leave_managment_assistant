"""HTTP clients for the employee, leave and policy (RAG) services."""
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import httpx

from app.config import settings


class ServiceError(Exception):
    def __init__(self, service: str, status_code: int, message: str):
        super().__init__(message)
        self.service = service
        self.status_code = status_code
        self.message = message


class ServiceClient:
    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url

    async def request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url, timeout=settings.service_timeout
            ) as client:
                r = await client.request(method, path, **kwargs)
        except httpx.HTTPError:
            raise ServiceError(self.name, 503, f"{self.name} is unreachable at {self.base_url}.")

        try:
            data = r.json()
        except ValueError:
            data = {"error": r.text[:300]}

        if r.status_code >= 400:
            message = data.get("error") or data.get("detail") or str(data)
            raise ServiceError(self.name, r.status_code, str(message))
        return data


employee_service = ServiceClient("Employee service", settings.employee_service_url)
leave_service = ServiceClient("Leave service", settings.leave_service_url)
policy_service = ServiceClient("Policy service", settings.policy_service_url)

EMPLOYEE_SECTIONS = {
    "basic": "basic-info",
    "job": "job-details",
    "manager": "manager",
    "department": "department",
    "status": "employment-status",
}


def _id(value: Any) -> str:
    return quote(str(value).strip(), safe="")


def _params(**kwargs) -> Dict[str, Any]:
    return {k: v for k, v in kwargs.items() if v is not None}


# ---------- employee service ----------
async def get_employee_profile(employee_id: str) -> Dict[str, Any]:
    return await employee_service.request("GET", f"/employees/{_id(employee_id)}")


async def get_employee_section(employee_id: str, section: str) -> Dict[str, Any]:
    path = EMPLOYEE_SECTIONS[section]
    return await employee_service.request("GET", f"/employees/{_id(employee_id)}/{path}")


# ---------- leave service ----------
async def get_leave_balance(employee_id: str, year: Optional[int] = None) -> Dict[str, Any]:
    return await leave_service.request(
        "GET", f"/employees/{_id(employee_id)}/leave-balance", params=_params(year=year)
    )


async def get_leave_history(
    employee_id: str,
    year: Optional[int] = None,
    leave_type: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    return await leave_service.request(
        "GET",
        f"/employees/{_id(employee_id)}/leave-history",
        params=_params(year=year, leave_type=leave_type, status=status),
    )


async def get_leave_details(employee_id: str) -> Dict[str, Any]:
    return await leave_service.request("GET", f"/employees/{_id(employee_id)}")


async def get_holidays(**filters) -> Dict[str, Any]:
    return await leave_service.request("GET", "/holidays", params=_params(**filters))


async def apply_leave(payload: Dict[str, Any]) -> Dict[str, Any]:
    return await leave_service.request("POST", "/leaves/apply", json=payload)


async def cancel_leave(request_id: int, cancel_reason: str = "") -> Dict[str, Any]:
    return await leave_service.request(
        "POST", f"/leaves/{int(request_id)}/cancel", json={"cancel_reason": cancel_reason}
    )


# ---------- policy (RAG) service ----------
async def query_policy(question: str, history: List[Tuple[str, str]]) -> Dict[str, Any]:
    return await policy_service.request(
        "POST",
        "/policies/query",
        json={
            "question": question,
            "history": [{"question": q, "answer": a} for q, a in history],
        },
    )


async def service_health() -> Dict[str, str]:
    checks = {
        "employee_service": (employee_service, "/"),
        "leave_service": (leave_service, "/"),
        "policy_service": (policy_service, "/health"),
    }
    result = {}
    for key, (client, path) in checks.items():
        try:
            await client.request("GET", path)
            result[key] = "ok"
        except ServiceError as e:
            result[key] = f"error: {e.message}"
    return result
