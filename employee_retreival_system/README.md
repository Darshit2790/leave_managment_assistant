# HR Operations API Service

A lightweight, zero-configuration REST API service built with **Flask**, **SQLite**, and **SQLAlchemy** to power employee data retrieval operations for an AI-powered HR Assistant.

The database automatically initializes and populates realistic dummy employee and department records when the server starts up.

---

## Tech Stack

- **Framework**: Flask (Python)
- **Database**: SQLite (file-based, automatically created as `hr_operations.db`)
- **ORM**: SQLAlchemy / Flask-SQLAlchemy
- **API Documentation**: Swagger UI via Flasgger

---

## Database Architecture

### 1. `departments` Table
| Column | Type | Description |
|---|---|---|
| `id` | INTEGER | Primary Key (Auto-increment) |
| `name` | VARCHAR(100) | Department name (e.g., "Engineering", "Human Resources") |
| `code` | VARCHAR(20) | Department short code (e.g., "ENG", "HR", "FIN") |
| `description` | VARCHAR(255) | Department function description |
| `location` | VARCHAR(150) | Office floor / building location |

### 2. `employees` Table
| Column | Type | Description |
|---|---|---|
| `id` | VARCHAR(50) | Primary Key (e.g., "EMP1007") |
| `first_name` | VARCHAR(100) | Employee first name |
| `last_name` | VARCHAR(100) | Employee last name |
| `email` | VARCHAR(150) | Corporate email (Unique) |
| `phone` | VARCHAR(50) | Contact phone number |
| `designation` | VARCHAR(100) | Job title / designation |
| `grade` | VARCHAR(50) | Band / Grade level (e.g., "L3", "L4", "L5", "M1", "E2") |
| `department_id` | INTEGER | Foreign Key -> `departments.id` |
| `manager_id` | VARCHAR(50) | Foreign Key -> `employees.id` (Self-referential) |
| `employment_status`| VARCHAR(50) | Status: "Active", "On Notice", "Resigned", "Terminated", "On Leave" |
| `date_of_joining` | DATE | Date joined the organization |
| `work_location` | VARCHAR(150) | Work arrangement and office location |

---

## Quick Start Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Server
By default, the server runs on **port 9090**:
```bash
python app.py
```

### 3. Custom Port Configuration
You can configure the port using either the `--port` argument or the `PORT` environment variable:

```bash
# Using CLI argument
python app.py --port 8080

# Using environment variable
PORT=8080 python app.py
```

---

## Swagger API Documentation

Once the server is running, the interactive Swagger UI and OpenAPI specifications can be accessed at:

- **Swagger UI**: [http://localhost:9090/apidocs/](http://localhost:9090/apidocs/)
- **OpenAPI JSON Spec**: [http://localhost:9090/apispec.json](http://localhost:9090/apispec.json)

---

## Available API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/employees/{employeeId}` | Get complete employee profile |
| `GET` | `/employees/{employeeId}/basic-info` | Name, email, phone, employee ID |
| `GET` | `/employees/{employeeId}/job-details` | Designation, department, grade |
| `GET` | `/employees/{employeeId}/manager` | Reporting manager details |
| `GET` | `/employees/{employeeId}/department` | Department information |
| `GET` | `/employees/{employeeId}/employment-status` | Active, resigned, terminated, etc. |
| `GET` | `/employees` | List all employees (summary) |
| `GET` | `/` | Health check & quick links |

---

## Sample Dummy Data for Testing

| Employee ID | Name | Role | Department | Status |
|---|---|---|---|---|
| `EMP1001` | Alexander Wright | Chief Technology Officer | Engineering | Active (Exec) |
| `EMP1002` | Elena Rostova | Chief People Officer | Human Resources | Active (Exec) |
| `EMP1003` | Marcus Chen | VP of Finance | Finance & Accounting | Active (Exec) |
| `EMP1004` | Sarah Jenkins | Engineering Director | Engineering | Active (Manager) |
| `EMP1005` | David Kim | HR Operations Manager | Human Resources | Active (Manager) |
| `EMP1006` | Priya Sharma | Principal Product Manager | Product & Design | Active |
| `EMP1007` | John Doe | Senior Software Engineer | Engineering | Active |
| `EMP1008` | Emily Watson | HR Operations Specialist | Human Resources | Active |
| `EMP1009` | Michael Brown | Senior Financial Analyst | Finance & Accounting | On Notice |
| `EMP1010` | Sophia Martinez | Growth Marketing Lead | Marketing & Growth | On Leave |
| `EMP1011` | James Wilson | Software Engineer II | Engineering | Resigned |
| `EMP1012` | Rachel Green | Associate QA Engineer | Engineering | Terminated |

---

## Example Requests & Responses

### 1. Get Complete Profile
**Request:**
```bash
curl http://localhost:9090/employees/EMP1007
```
**Response (200 OK):**
```json
{
  "basic_info": {
    "email": "john.doe@company.com",
    "employee_id": "EMP1007",
    "first_name": "John",
    "full_name": "John Doe",
    "last_name": "Doe",
    "phone": "+1 (415) 555-0147"
  },
  "department": {
    "department_code": "ENG",
    "department_id": 1,
    "department_name": "Engineering",
    "description": "Core software engineering, platform infrastructure, and DevOps teams.",
    "employee_id": "EMP1007",
    "location": "San Francisco HQ - Building 1, Floor 4",
    "total_department_members": 5
  },
  "employment_status": {
    "date_of_joining": "2021-06-14",
    "employee_id": "EMP1007",
    "employment_status": "Active",
    "full_name": "John Doe",
    "is_active": true
  },
  "job_details": {
    "department": "Engineering",
    "department_code": "ENG",
    "designation": "Senior Software Engineer",
    "employee_id": "EMP1007",
    "grade": "L5",
    "work_location": "San Francisco, CA (Hybrid)"
  },
  "manager": {
    "employee_id": "EMP1007",
    "has_manager": true,
    "manager": {
      "department": "Engineering",
      "designation": "Engineering Director - Backend & Cloud",
      "email": "sarah.jenkins@company.com",
      "full_name": "Sarah Jenkins",
      "manager_id": "EMP1004",
      "phone": "+1 (415) 555-0114"
    }
  }
}
```

### 2. Get Basic Info
**Request:**
```bash
curl http://localhost:9090/employees/EMP1007/basic-info
```
**Response (200 OK):**
```json
{
  "email": "john.doe@company.com",
  "employee_id": "EMP1007",
  "first_name": "John",
  "full_name": "John Doe",
  "last_name": "Doe",
  "phone": "+1 (415) 555-0147"
}
```

### 3. Get Job Details
**Request:**
```bash
curl http://localhost:9090/employees/EMP1007/job-details
```
**Response (200 OK):**
```json
{
  "department": "Engineering",
  "department_code": "ENG",
  "designation": "Senior Software Engineer",
  "employee_id": "EMP1007",
  "grade": "L5",
  "work_location": "San Francisco, CA (Hybrid)"
}
```

### 4. Get Manager Details
**Request:**
```bash
curl http://localhost:9090/employees/EMP1007/manager
```
**Response (200 OK):**
```json
{
  "employee_id": "EMP1007",
  "has_manager": true,
  "manager": {
    "department": "Engineering",
    "designation": "Engineering Director - Backend & Cloud",
    "email": "sarah.jenkins@company.com",
    "full_name": "Sarah Jenkins",
    "manager_id": "EMP1004",
    "phone": "+1 (415) 555-0114"
  }
}
```

### 5. Get Department Details
**Request:**
```bash
curl http://localhost:9090/employees/EMP1007/department
```
**Response (200 OK):**
```json
{
  "department_code": "ENG",
  "department_id": 1,
  "department_name": "Engineering",
  "description": "Core software engineering, platform infrastructure, and DevOps teams.",
  "employee_id": "EMP1007",
  "location": "San Francisco HQ - Building 1, Floor 4",
  "total_department_members": 5
}
```

### 6. Get Employment Status
**Request:**
```bash
curl http://localhost:9090/employees/EMP1007/employment-status
```
**Response (200 OK):**
```json
{
  "date_of_joining": "2021-06-14",
  "employee_id": "EMP1007",
  "employment_status": "Active",
  "full_name": "John Doe",
  "is_active": true
}
```
