import os
import argparse
from datetime import date, datetime
from flask import Flask, jsonify, request
from flasgger import Swagger
from models import db, LeaveBalance, LeaveRequest, Holiday
from seed_data import init_db


def create_app(test_config=None):
    app = Flask(__name__)

    base_dir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(base_dir, 'leave_management.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if test_config:
        app.config.update(test_config)

    # ── Swagger / Flasgger ──────────────────────────────────────────────
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec',
                "route": '/apispec.json',
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/apidocs/"
    }

    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "Leave Management API",
            "description": (
                "Leave Management Service for AI-Powered HR Assistant. "
                "Supports applying for leave, cancellations, balance enquiries, "
                "leave history, employee details proxy, and the company holiday calendar."
            ),
            "version": "1.0.0",
            "contact": {
                "name": "HR Operations Team",
                "email": "hr-ops@company.internal"
            }
        },
        "tags": [
            {
                "name": "Leave Operations",
                "description": "Apply, cancel, and query employee leave requests"
            },
            {
                "name": "Leave Balances",
                "description": "Check remaining leave entitlements"
            },
            {
                "name": "Employee Info",
                "description": "Lightweight employee details (name, department, manager) from the leave service"
            },
            {
                "name": "Holiday Calendar",
                "description": "Company and public holiday calendar"
            }
        ],
        "schemes": ["http", "https"]
    }

    Swagger(app, config=swagger_config, template=swagger_template)

    db.init_app(app)
    init_db(app)

    # ── Helper ─────────────────────────────────────────────────────────
    VALID_LEAVE_TYPES = {"Annual", "Sick", "Casual", "Maternity", "Paternity", "Comp Off"}
    VALID_STATUSES = {"Pending", "Approved", "Rejected", "Cancelled"}

    def _business_days(start: date, end: date) -> float:
        """Count weekday (Mon-Fri) days between start and end inclusive."""
        total = 0
        current = start
        from datetime import timedelta
        while current <= end:
            if current.weekday() < 5:
                total += 1
            current += timedelta(days=1)
        return float(total)

    # ── Root ────────────────────────────────────────────────────────────

    @app.route('/', methods=['GET'])
    def root():
        """Root endpoint with service status and navigation links"""
        return jsonify({
            "service": "Leave Management API",
            "status": "online",
            "swagger_docs": "/apidocs/",
            "sample_employees": [
                "EMP1001", "EMP1002", "EMP1003", "EMP1004",
                "EMP1005", "EMP1006", "EMP1007", "EMP1008",
                "EMP1009", "EMP1010", "EMP1011", "EMP1012"
            ],
            "endpoints": {
                "applyLeave":        "POST /leaves/apply",
                "cancelLeave":       "POST /leaves/{request_id}/cancel",
                "getLeaveBalance":   "GET  /employees/{employee_id}/leave-balance",
                "getLeaveHistory":   "GET  /employees/{employee_id}/leave-history",
                "getEmployeeDetails":"GET  /employees/{employee_id}",
                "getHolidayCalendar":"GET  /holidays"
            }
        }), 200

    # ================================================================
    # applyLeave  –  POST /leaves/apply
    # ================================================================
    @app.route('/leaves/apply', methods=['POST'])
    def apply_leave():
        """
        Apply for leave
        ---
        tags:
          - Leave Operations
        summary: applyLeave() — Submit a new leave request
        description: >
          Submit a leave application for a specific employee. The API validates
          that the requested leave type has sufficient balance before creating
          the request (status = Pending). Weekends are automatically excluded
          from days_requested when it is omitted.
        consumes:
          - application/json
        parameters:
          - in: body
            name: body
            required: true
            schema:
              type: object
              required:
                - employee_id
                - leave_type
                - start_date
                - end_date
              properties:
                employee_id:
                  type: string
                  example: "EMP1007"
                  description: Employee ID from the HR system
                leave_type:
                  type: string
                  example: "Annual"
                  enum: [Annual, Sick, Casual, Maternity, Paternity, Comp Off]
                start_date:
                  type: string
                  format: date
                  example: "2026-05-11"
                end_date:
                  type: string
                  format: date
                  example: "2026-05-15"
                reason:
                  type: string
                  example: "Summer vacation with family."
        responses:
          201:
            description: Leave request submitted successfully
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Leave request submitted successfully."
                request_id:
                  type: integer
                  example: 15
                employee_id:
                  type: string
                  example: "EMP1007"
                leave_type:
                  type: string
                  example: "Annual"
                start_date:
                  type: string
                  example: "2026-05-11"
                end_date:
                  type: string
                  example: "2026-05-15"
                days_requested:
                  type: number
                  example: 5
                status:
                  type: string
                  example: "Pending"
          400:
            description: Validation error (missing fields, bad dates, insufficient balance)
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Insufficient Annual leave balance. Available: 3.0 days, Requested: 5.0 days."
          404:
            description: Leave balance record not found for employee/year
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "No leave balance record found for EMP9999 in 2026."
        """
        data = request.get_json(silent=True) or {}

        # Required fields
        for field in ('employee_id', 'leave_type', 'start_date', 'end_date'):
            if not data.get(field):
                return jsonify({"error": f"Missing required field: '{field}'."}), 400

        employee_id = data['employee_id'].strip()
        leave_type = data['leave_type'].strip()
        reason = data.get('reason', '').strip()

        if leave_type not in VALID_LEAVE_TYPES:
            return jsonify({"error": f"Invalid leave_type '{leave_type}'. Must be one of: {sorted(VALID_LEAVE_TYPES)}."}), 400

        try:
            start_date = date.fromisoformat(data['start_date'])
            end_date = date.fromisoformat(data['end_date'])
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

        if end_date < start_date:
            return jsonify({"error": "end_date cannot be before start_date."}), 400

        days_requested = _business_days(start_date, end_date)
        if days_requested == 0:
            return jsonify({"error": "The selected date range contains no working days (Mon–Fri)."}), 400

        year = start_date.year
        balance = LeaveBalance.query.filter_by(employee_id=employee_id, year=year).first()
        if not balance:
            return jsonify({"error": f"No leave balance record found for {employee_id} in {year}."}), 404

        # Balance check
        type_map = {
            "Annual":    (balance.annual_entitled + balance.carried_forward - balance.annual_used),
            "Sick":      (balance.sick_entitled - balance.sick_used),
            "Casual":    (balance.casual_entitled - balance.casual_used),
            "Maternity": (balance.maternity_entitled - balance.maternity_used),
            "Paternity": (balance.paternity_entitled - balance.paternity_used),
            "Comp Off":  (balance.comp_off_entitled - balance.comp_off_used),
        }
        available = type_map.get(leave_type, 0)
        if days_requested > available:
            return jsonify({
                "error": f"Insufficient {leave_type} leave balance. Available: {round(available, 1)} days, Requested: {days_requested} days."
            }), 400

        # Create request
        lr = LeaveRequest(
            employee_id=employee_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            days_requested=days_requested,
            reason=reason,
            status="Pending",
            applied_on=datetime.utcnow()
        )
        db.session.add(lr)
        db.session.commit()

        return jsonify({
            "message": "Leave request submitted successfully.",
            "request_id": lr.id,
            "employee_id": lr.employee_id,
            "leave_type": lr.leave_type,
            "start_date": lr.start_date.isoformat(),
            "end_date": lr.end_date.isoformat(),
            "days_requested": lr.days_requested,
            "status": lr.status
        }), 201

    # ================================================================
    # cancelLeave  –  POST /leaves/<request_id>/cancel
    # ================================================================
    @app.route('/leaves/<int:request_id>/cancel', methods=['POST'])
    def cancel_leave(request_id):
        """
        Cancel a leave request
        ---
        tags:
          - Leave Operations
        summary: cancelLeave() — Cancel a pending or approved leave request
        description: >
          Cancel an existing leave request by its request_id. Only requests
          with status 'Pending' or 'Approved' can be cancelled. When an
          Approved leave is cancelled, the used balance is credited back
          automatically.
        parameters:
          - name: request_id
            in: path
            type: integer
            required: true
            description: The unique request ID returned when the leave was applied
            example: 4
          - in: body
            name: body
            schema:
              type: object
              properties:
                cancel_reason:
                  type: string
                  example: "Plans changed — no longer travelling."
        responses:
          200:
            description: Leave request cancelled successfully
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Leave request #4 cancelled successfully."
                request_id:
                  type: integer
                  example: 4
                employee_id:
                  type: string
                  example: "EMP1007"
                previous_status:
                  type: string
                  example: "Approved"
                new_status:
                  type: string
                  example: "Cancelled"
                balance_restored:
                  type: boolean
                  example: true
                days_restored:
                  type: number
                  example: 5.0
          400:
            description: Leave request cannot be cancelled (already cancelled/rejected)
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Leave request #4 has status 'Cancelled' and cannot be cancelled again."
          404:
            description: Leave request not found
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Leave request with ID 999 not found."
        """
        lr = LeaveRequest.query.get(request_id)
        if not lr:
            return jsonify({"error": f"Leave request with ID {request_id} not found."}), 404

        if lr.status in ('Cancelled', 'Rejected'):
            return jsonify({"error": f"Leave request #{request_id} has status '{lr.status}' and cannot be cancelled."}), 400

        data = request.get_json(silent=True) or {}
        cancel_reason = data.get('cancel_reason', '').strip()

        previous_status = lr.status
        balance_restored = False
        days_restored = 0.0

        # If Approved, restore the balance
        if lr.status == 'Approved':
            balance = LeaveBalance.query.filter_by(
                employee_id=lr.employee_id, year=lr.start_date.year
            ).first()
            if balance:
                type_field_map = {
                    "Annual":    'annual_used',
                    "Sick":      'sick_used',
                    "Casual":    'casual_used',
                    "Maternity": 'maternity_used',
                    "Paternity": 'paternity_used',
                    "Comp Off":  'comp_off_used',
                }
                field = type_field_map.get(lr.leave_type)
                if field:
                    current_val = getattr(balance, field)
                    setattr(balance, field, max(0.0, current_val - lr.days_requested))
                    days_restored = lr.days_requested
                    balance_restored = True

        lr.status = 'Cancelled'
        lr.cancel_reason = cancel_reason or None
        db.session.commit()

        return jsonify({
            "message": f"Leave request #{request_id} cancelled successfully.",
            "request_id": request_id,
            "employee_id": lr.employee_id,
            "previous_status": previous_status,
            "new_status": "Cancelled",
            "balance_restored": balance_restored,
            "days_restored": days_restored
        }), 200

    # ================================================================
    # getLeaveBalance  –  GET /employees/<employee_id>/leave-balance
    # ================================================================
    @app.route('/employees/<employee_id>/leave-balance', methods=['GET'])
    def get_leave_balance(employee_id):
        """
        Check leave balance for an employee
        ---
        tags:
          - Leave Balances
        summary: getLeaveBalance() — Get remaining leave balances
        description: >
          Returns the full leave balance breakdown for the requested year
          (defaults to current year). Shows entitled, used, carried-forward,
          and available days per leave type.
        parameters:
          - name: employee_id
            in: path
            type: string
            required: true
            description: Employee ID (e.g., EMP1007)
          - name: year
            in: query
            type: integer
            required: false
            description: Year to query (defaults to current year)
            example: 2026
        responses:
          200:
            description: Leave balance summary
            schema:
              type: object
              properties:
                employee_id:
                  type: string
                  example: "EMP1007"
                year:
                  type: integer
                  example: 2026
                balances:
                  type: object
                  properties:
                    annual:
                      type: object
                      properties:
                        entitled:
                          type: number
                          example: 20
                        used:
                          type: number
                          example: 8
                        carried_forward:
                          type: number
                          example: 1
                        available:
                          type: number
                          example: 13
                    sick:
                      type: object
                      properties:
                        entitled:
                          type: number
                          example: 10
                        used:
                          type: number
                          example: 3
                        available:
                          type: number
                          example: 7
                    casual:
                      type: object
                      properties:
                        entitled:
                          type: number
                          example: 5
                        used:
                          type: number
                          example: 2
                        available:
                          type: number
                          example: 3
                    maternity:
                      type: object
                    paternity:
                      type: object
                    comp_off:
                      type: object
                total_available:
                  type: number
                  example: 23
          404:
            description: No balance record found
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "No leave balance found for EMP9999 in year 2026."
        """
        year_param = request.args.get('year', date.today().year)
        try:
            year = int(year_param)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid 'year' query parameter. Must be an integer."}), 400

        balance = LeaveBalance.query.filter_by(employee_id=employee_id, year=year).first()
        if not balance:
            return jsonify({"error": f"No leave balance found for {employee_id} in year {year}."}), 404

        return jsonify(balance.to_balance_summary()), 200

    # ================================================================
    # getLeaveHistory  –  GET /employees/<employee_id>/leave-history
    # ================================================================
    @app.route('/employees/<employee_id>/leave-history', methods=['GET'])
    def get_leave_history(employee_id):
        """
        View leave history for an employee
        ---
        tags:
          - Leave Operations
        summary: getLeaveHistory() — Retrieve all leave requests for an employee
        description: >
          Returns all leave requests for an employee, optionally filtered by
          year, leave_type, or status. Results are sorted with the most
          recent first.
        parameters:
          - name: employee_id
            in: path
            type: string
            required: true
            description: Employee ID (e.g., EMP1007)
          - name: year
            in: query
            type: integer
            required: false
            description: Filter by leave start year (e.g., 2026)
          - name: leave_type
            in: query
            type: string
            required: false
            description: "Filter by leave type: Annual | Sick | Casual | Maternity | Paternity | Comp Off"
            example: "Annual"
          - name: status
            in: query
            type: string
            required: false
            description: "Filter by status: Pending | Approved | Rejected | Cancelled"
            example: "Approved"
        responses:
          200:
            description: Paginated leave history
            schema:
              type: object
              properties:
                employee_id:
                  type: string
                  example: "EMP1007"
                total_records:
                  type: integer
                  example: 4
                filters_applied:
                  type: object
                  properties:
                    year:
                      type: integer
                      example: 2026
                    leave_type:
                      type: string
                      example: "Annual"
                    status:
                      type: string
                      example: "Approved"
                leave_history:
                  type: array
                  items:
                    type: object
                    properties:
                      request_id:
                        type: integer
                        example: 1
                      leave_type:
                        type: string
                        example: "Annual"
                      start_date:
                        type: string
                        example: "2026-01-05"
                      end_date:
                        type: string
                        example: "2026-01-09"
                      days_requested:
                        type: number
                        example: 5
                      reason:
                        type: string
                        example: "New Year holiday vacation."
                      status:
                        type: string
                        example: "Approved"
                      applied_on:
                        type: string
                        example: "2025-12-15 10:00:00"
                      approved_by:
                        type: string
                        example: "EMP1004"
        """
        query = LeaveRequest.query.filter_by(employee_id=employee_id)

        filters_applied = {}
        year_param = request.args.get('year')
        if year_param:
            try:
                year = int(year_param)
                query = query.filter(
                    db.extract('year', LeaveRequest.start_date) == year
                )
                filters_applied['year'] = year
            except ValueError:
                return jsonify({"error": "Invalid 'year' parameter."}), 400

        leave_type_param = request.args.get('leave_type')
        if leave_type_param:
            query = query.filter_by(leave_type=leave_type_param)
            filters_applied['leave_type'] = leave_type_param

        status_param = request.args.get('status')
        if status_param:
            if status_param not in VALID_STATUSES:
                return jsonify({"error": f"Invalid status '{status_param}'. Must be one of: {sorted(VALID_STATUSES)}."}), 400
            query = query.filter_by(status=status_param)
            filters_applied['status'] = status_param

        records = query.order_by(LeaveRequest.applied_on.desc()).all()

        return jsonify({
            "employee_id": employee_id,
            "total_records": len(records),
            "filters_applied": filters_applied,
            "leave_history": [r.to_dict() for r in records]
        }), 200

    # ================================================================
    # getEmployeeDetails  –  GET /employees/<employee_id>
    # ================================================================
    @app.route('/employees/<employee_id>', methods=['GET'])
    def get_employee_details(employee_id):
        """
        Get employee details (Leave service view)
        ---
        tags:
          - Employee Info
        summary: getEmployeeDetails() — Get employee summary from leave service
        description: >
          Returns lightweight employee details (name, department, designation,
          manager) stored within the leave service, along with their current-year
          leave balance summary and any active/pending leave requests.
          For the full employee profile, use the HR Operations service.
        parameters:
          - name: employee_id
            in: path
            type: string
            required: true
            description: Employee ID (e.g., EMP1007)
        responses:
          200:
            description: Employee summary with leave context
            schema:
              type: object
              properties:
                employee_id:
                  type: string
                  example: "EMP1007"
                leave_balance_year:
                  type: integer
                  example: 2026
                current_balance:
                  type: object
                  description: Same structure as getLeaveBalance response
                active_leave:
                  type: object
                  nullable: true
                  description: Currently active (Approved, in-progress) leave request if any
                pending_requests:
                  type: array
                  description: All pending leave requests awaiting approval
                  items:
                    type: object
          404:
            description: No leave data found for this employee
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "No leave records found for employee EMP9999."
        """
        year = date.today().year
        balance = LeaveBalance.query.filter_by(employee_id=employee_id, year=year).first()
        all_requests = LeaveRequest.query.filter_by(employee_id=employee_id).order_by(
            LeaveRequest.applied_on.desc()
        ).all()

        if not balance and not all_requests:
            return jsonify({"error": f"No leave records found for employee {employee_id}."}), 404

        today = date.today()
        active_leave = None
        for lr in all_requests:
            if lr.status == 'Approved' and lr.start_date <= today <= lr.end_date:
                active_leave = lr.to_dict()
                break

        pending_requests = [lr.to_dict() for lr in all_requests if lr.status == 'Pending']

        return jsonify({
            "employee_id": employee_id,
            "leave_balance_year": year,
            "current_balance": balance.to_balance_summary() if balance else None,
            "active_leave": active_leave,
            "pending_requests": pending_requests,
            "total_requests_on_record": len(all_requests)
        }), 200

    # ================================================================
    # getHolidayCalendar  –  GET /holidays
    # ================================================================
    @app.route('/holidays', methods=['GET'])
    def get_holiday_calendar():
        """
        Get company holiday calendar
        ---
        tags:
          - Holiday Calendar
        summary: getHolidayCalendar() — Retrieve the company holiday calendar
        description: >
          Returns all company and public holidays. Can be filtered by year,
          location, and holiday_type. Optional holidays (Diwali, Eid) are
          flagged separately. Location filter accepts: 'San Francisco',
          'New York', 'Austin', or 'All' (default — returns all including
          location-specific ones).
        parameters:
          - name: year
            in: query
            type: integer
            required: false
            description: Filter by year (defaults to current year)
            example: 2026
          - name: location
            in: query
            type: string
            required: false
            description: "Filter by location: San Francisco | New York | Austin | All"
            example: "San Francisco"
          - name: holiday_type
            in: query
            type: string
            required: false
            description: "Filter by type: Public | Company | Optional | Regional"
            example: "Public"
          - name: include_optional
            in: query
            type: boolean
            required: false
            description: "Set to false to exclude optional/floating holidays (default: true)"
            example: true
        responses:
          200:
            description: List of holidays matching the filter
            schema:
              type: object
              properties:
                year:
                  type: integer
                  example: 2026
                total_holidays:
                  type: integer
                  example: 11
                mandatory_holidays:
                  type: integer
                  example: 10
                optional_holidays:
                  type: integer
                  example: 2
                filters_applied:
                  type: object
                holidays:
                  type: array
                  items:
                    type: object
                    properties:
                      holiday_id:
                        type: integer
                        example: 1
                      name:
                        type: string
                        example: "New Year's Day"
                      date:
                        type: string
                        example: "2026-01-01"
                      day:
                        type: string
                        example: "Thursday"
                      year:
                        type: integer
                        example: 2026
                      holiday_type:
                        type: string
                        example: "Public"
                      location:
                        type: string
                        example: "All Locations"
                      is_optional:
                        type: boolean
                        example: false
                      description:
                        type: string
                        example: "First day of the new year."
        """
        year_param = request.args.get('year', date.today().year)
        try:
            year = int(year_param)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid 'year' query parameter."}), 400

        location_param = request.args.get('location', 'All')
        holiday_type_param = request.args.get('holiday_type')
        include_optional_param = request.args.get('include_optional', 'true').lower()
        include_optional = include_optional_param != 'false'

        query = Holiday.query.filter_by(year=year)

        # Location filter: show all-location holidays; also show regional ones
        # matching the requested location
        if location_param and location_param.lower() != 'all':
            query = query.filter(
                (Holiday.location == None) | (Holiday.location == location_param)
            )

        if holiday_type_param:
            query = query.filter_by(holiday_type=holiday_type_param)

        if not include_optional:
            query = query.filter_by(is_optional=False)

        holidays = query.order_by(Holiday.date.asc()).all()

        filters_applied = {"year": year}
        if location_param and location_param.lower() != 'all':
            filters_applied['location'] = location_param
        if holiday_type_param:
            filters_applied['holiday_type'] = holiday_type_param
        if not include_optional:
            filters_applied['include_optional'] = False

        mandatory = [h for h in holidays if not h.is_optional]
        optional = [h for h in holidays if h.is_optional]

        return jsonify({
            "year": year,
            "total_holidays": len(holidays),
            "mandatory_holidays": len(mandatory),
            "optional_holidays": len(optional),
            "filters_applied": filters_applied,
            "holidays": [h.to_dict() for h in holidays]
        }), 200

    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Leave Management Service")
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', 9091)),
                        help="Port to run the Leave Management server on (default: 9091 or PORT env var)")
    parser.add_argument('--host', type=str, default=os.environ.get('HOST', '0.0.0.0'),
                        help="Host to run the server on (default: 0.0.0.0)")
    parser.add_argument('--debug', action='store_true', default=False,
                        help="Run in debug mode")

    args = parser.parse_args()

    app = create_app()
    print(f"\n=======================================================")
    print(f" Leave Management API Service Started")
    print(f" Base URL:    http://localhost:{args.port}/")
    print(f" Swagger UI:  http://localhost:{args.port}/apidocs/")
    print(f" SQLite DB:   leave_management.db (auto-seeded)")
    print(f"=======================================================\n")
    app.run(host=args.host, port=args.port, debug=args.debug)
