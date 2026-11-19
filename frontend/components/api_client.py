import os
import requests

from typing import Optional, Dict, Any, List


class APIClient:

    def __init__(self, base_url=None, timeout=30):

        self.base_url = (
            base_url
            or os.getenv("BACKEND_URL", "http://localhost:8000")
        ).rstrip("/")

        self.timeout = timeout

        self.session = requests.Session()

        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

    # ---------------------------------------
    # Generic API Request Handler
    # ---------------------------------------

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        payload: Optional[Dict] = None
    ) -> Dict[str, Any]:

        url = f"{self.base_url}{endpoint}"

        try:

            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=payload,
                timeout=self.timeout
            )

            response.raise_for_status()

            if not response.content:
                return {"success": True}

            return response.json()

        except requests.exceptions.Timeout:

            return {
                "success": False,
                "error": "Request timed out. Please try again."
            }

        except requests.exceptions.ConnectionError:

            return {
                "success": False,
                "error": "Unable to connect to the backend server."
            }

        except requests.exceptions.HTTPError:

            try:
                error_data = response.json()
            except ValueError:
                error_data = {}

            return {
                "success": False,
                "error": error_data.get(
                    "detail",
                    f"HTTP Error: {response.status_code}"
                )
            }

        except requests.exceptions.RequestException as e:

            return {
                "success": False,
                "error": str(e)
            }

        except ValueError:

            return {
                "success": False,
                "error": "Invalid JSON response from backend."
            }

    # ---------------------------------------
    # 1. AI Chat Assistant
    # ---------------------------------------

    def send_chat_message(
        self,
        message: str,
        employee_id: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:

        payload = {
            "message": message,
            "employee_id": employee_id,
            "session_id": session_id
        }

        return self._request(
            method="POST",
            endpoint="/api/v1/chat",
            payload=payload
        )

    # ---------------------------------------
    # 2. Get Employee Leave Balance
    # ---------------------------------------

    def get_leave_balance(
        self,
        employee_id: str
    ) -> Dict[str, Any]:

        return self._request(
            method="GET",
            endpoint=f"/api/v1/leave/balance/{employee_id}"
        )

    # ---------------------------------------
    # 3. Apply for Leave
    # ---------------------------------------

    def apply_leave(
        self,
        employee_id: str,
        leave_type: str,
        start_date: str,
        end_date: str,
        reason: str
    ) -> Dict[str, Any]:

        payload = {
            "employee_id": employee_id,
            "leave_type": leave_type,
            "start_date": start_date,
            "end_date": end_date,
            "reason": reason
        }

        return self._request(
            method="POST",
            endpoint="/api/v1/leave/apply",
            payload=payload
        )

    # ---------------------------------------
    # 4. Get Leave Application History
    # ---------------------------------------

    def get_leave_history(
        self,
        employee_id: str
    ) -> Dict[str, Any]:

        return self._request(
            method="GET",
            endpoint=f"/api/v1/leave/history/{employee_id}"
        )

    # ---------------------------------------
    # 5. Cancel Leave Application
    # ---------------------------------------

    def cancel_leave(
        self,
        application_id: str,
        employee_id: str
    ) -> Dict[str, Any]:

        payload = {
            "employee_id": employee_id
        }

        return self._request(
            method="POST",
            endpoint=f"/api/v1/leave/{application_id}/cancel",
            payload=payload
        )

    # ---------------------------------------
    # 6. Search HR Leave Policies (RAG)
    # ---------------------------------------

    def search_leave_policy(
        self,
        question: str,
        employee_id: str
    ) -> Dict[str, Any]:

        payload = {
            "question": question,
            "employee_id": employee_id
        }

        return self._request(
            method="POST",
            endpoint="/api/v1/policies/search",
            payload=payload
        )

    # ---------------------------------------
    # 7. Get Employee Details
    # ---------------------------------------

    def get_employee_details(
        self,
        employee_id: str
    ) -> Dict[str, Any]:

        return self._request(
            method="GET",
            endpoint=f"/api/v1/employees/{employee_id}"
        )

    # ---------------------------------------
    # 8. Get Holidays
    # ---------------------------------------

    def get_holidays(self) -> Dict[str, Any]:

        return self._request(
            method="GET",
            endpoint="/api/v1/holidays"
        )

    # ---------------------------------------
    # Close HTTP Session
    # ---------------------------------------

    def close(self):

        self.session.close()


# ---------------------------------------
# Shared API Client Instance
# ---------------------------------------

api_client = APIClient()
