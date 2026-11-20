# Leave Management System

A Flask-based Leave Management REST API service, built as the companion microservice to the **Employee Retrieval System**. It shares the same employee IDs (`EMP1001`–`EMP1012`) to enable an integrated AI-powered HR assistant demo.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run on default port 9091
python app.py

# Custom port
python app.py --port 8080

# Debug mode
python app.py --debug
```

Swagger UI: **http://localhost:9091/apidocs/**

---

## API Endpoints

| Function | Method | URL | Description |
|---|---|---|---|
| `applyLeave()` | POST | `/leaves/apply` | Submit a new leave request |
| `cancelLeave()` | POST | `/leaves/<request_id>/cancel` | Cancel a pending or approved request |
| `getLeaveBalance()` | GET | `/employees/<employee_id>/leave-balance` | Check remaining leave by type |
| `getLeaveHistory()` | GET | `/employees/<employee_id>/leave-history` | Full leave request history with filters |
| `getEmployeeDetails()` | GET | `/employees/<employee_id>` | Employee summary with active/pending leave context |
| `getHolidayCalendar()` | GET | `/holidays` | Company holiday calendar with location/type filters |

---

## Sample Requests

### Apply for Leave
```bash
curl -X POST http://localhost:9091/leaves/apply \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "EMP1007",
    "leave_type": "Annual",
    "start_date": "2026-06-01",
    "end_date": "2026-06-05",
    "reason": "Summer vacation"
  }'
```

### Cancel a Leave Request
```bash
curl -X POST http://localhost:9091/leaves/4/cancel \
  -H "Content-Type: application/json" \
  -d '{"cancel_reason": "Plans changed."}'
```

### Check Leave Balance
```bash
curl http://localhost:9091/employees/EMP1007/leave-balance?year=2026
```

### View Leave History
```bash
# All history
curl http://localhost:9091/employees/EMP1007/leave-history

# Filter by year + status
curl "http://localhost:9091/employees/EMP1007/leave-history?year=2026&status=Approved"
```

### Get Employee Details (with leave context)
```bash
curl http://localhost:9091/employees/EMP1007
```

### Holiday Calendar
```bash
# All 2026 holidays
curl http://localhost:9091/holidays?year=2026

# San Francisco holidays only
curl "http://localhost:9091/holidays?year=2026&location=San+Francisco"

# Mandatory only (exclude optional/floating)
curl "http://localhost:9091/holidays?year=2026&include_optional=false"
```

---

## Database Schema

| Table | Description |
|---|---|
| `leave_balances` | Per-employee, per-year entitlement and usage for all leave types |
| `leave_requests` | Individual leave applications with status, dates, approval trail |
| `holidays` | Company + public + regional holiday calendar |

The SQLite database (`leave_management.db`) is **auto-created and seeded** on first run.

---

## Employee Correlation

All 12 employees match the **Employee Retrieval System** (`EMP1001`–`EMP1012`):

| ID | Name | Designation | Employment Status | Leave Notes |
|---|---|---|---|---|
| EMP1001 | Alexander Wright | CTO | Active | 25 days annual; 3 days CF |
| EMP1002 | Elena Rostova | Chief People Officer | Active | 25 days annual |
| EMP1003 | Marcus Chen | VP Finance | Active | 25 days annual; 4 days CF |
| EMP1004 | Sarah Jenkins | Engineering Director | Active | 22 days annual |
| EMP1005 | David Kim | HR Operations Manager | Active | 22 days annual |
| EMP1006 | Priya Sharma | Principal Product Manager | Active | 20 days annual |
| EMP1007 | John Doe | Senior Software Engineer | Active | 20 days annual; 1 day CF |
| EMP1008 | Emily Watson | HR Operations Specialist | Active | 18 days annual |
| EMP1009 | Michael Brown | Senior Financial Analyst | On Notice | Most leaves exhausted |
| EMP1010 | Sophia Martinez | Growth Marketing Lead | On Leave | On maternity leave (90 days) |
| EMP1011 | James Wilson | Software Engineer II | Resigned | All leaves exhausted |
| EMP1012 | Rachel Green | Associate QA Engineer | Terminated | All leaves exhausted |

---

## Leave Types Supported

- **Annual** — standard annual leave with carry-forward
- **Sick** — medical/sick days
- **Casual** — short personal leave
- **Maternity** — extended maternity leave (EMP1010)
- **Paternity** — paternity leave entitlement
- **Comp Off** — compensatory off for extra hours worked

---

## Running Both Services Together

```bash
# Terminal 1 — Employee Retrieval System (port 9090)
cd ../employee_retreival_system && python app.py

# Terminal 2 — Leave Management System (port 9091)
cd ../leave_management_system && python app.py
```
