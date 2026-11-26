import os
import requests

from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://localhost:8000"
)


class APIClient:

    def __init__(self):
        self.base_url = API_BASE_URL
        self.session = requests.Session()
        self.timeout = 60

    def _request(self, method, endpoint, **kwargs):

        url = f"{self.base_url}{endpoint}"

        response = self.session.request(
            method=method,
            url=url,
            timeout=self.timeout,
            **kwargs
        )

        if not response.ok:
            try:
                detail = response.json().get("detail")
            except ValueError:
                detail = None
            if detail:
                raise requests.HTTPError(
                    f"{response.status_code} error: {detail}",
                    response=response
                )

        response.raise_for_status()

        if response.status_code == 204:
            return {}

        return response.json()

    # -------------------------
    # CHAT ASSISTANT
    # -------------------------

    def send_chat_message(
        self,
        message,
        session_id,
        employee_id
    ):

        return self._request(
            "POST",
            "/api/v1/chat",
            json={
                "message": message,
                "session_id": session_id,
                "employee_id": employee_id
            }
        )

    # -------------------------
    # LEAVE BALANCE
    # -------------------------

    def get_leave_balance(self, employee_id):

        return self._request(
            "GET",
            f"/api/v1/leaves/balance/{employee_id}"
        )

    # -------------------------
    # APPLY LEAVE
    # -------------------------

    def apply_leave(self, payload):

        return self._request(
            "POST",
            "/api/v1/leaves/apply",
            json=payload
        )

    # -------------------------
    # LEAVE HISTORY
    # -------------------------

    def get_leave_history(self, employee_id):

        return self._request(
            "GET",
            f"/api/v1/leaves/history/{employee_id}"
        )

    # -------------------------
    # CANCEL LEAVE
    # -------------------------

    def cancel_leave(self, leave_id):

        return self._request(
            "POST",
            f"/api/v1/leaves/{leave_id}/cancel"
        )

    # -------------------------
    # EMPLOYEE DETAILS
    # -------------------------

    def get_employee_details(self, employee_id):

        return self._request(
            "GET",
            f"/api/v1/employees/{employee_id}"
        )

    # -------------------------
    # HOLIDAY CALENDAR
    # -------------------------

    def get_holidays(self):

        return self._request(
            "GET",
            "/api/v1/holidays"
        )

    # -------------------------
    # CONFIRM ACTION
    # -------------------------

    def confirm_action(self, action, payload):

        return self._request(
            "POST",
            "/api/v1/chat/confirm",
            json={
                "action": action,
                "payload": payload
            }
        )


# Shared API client instance

api_client = APIClient()


def send_chat_message(message, session_id, employee_id):

    return api_client.send_chat_message(
        message,
        session_id,
        employee_id
    )