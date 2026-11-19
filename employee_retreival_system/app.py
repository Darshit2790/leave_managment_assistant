import os
import argparse
from flask import Flask, jsonify, request
from flasgger import Swagger
from models import db, Employee, Department
from seed_data import init_db

def create_app(test_config=None):
    app = Flask(__name__)
    
    # Database Configuration (SQLite file-based database)
    base_dir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(base_dir, 'hr_operations.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if test_config:
        app.config.update(test_config)

    # Flasgger / Swagger Configuration
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
            "title": "HR Operations API",
            "description": "HR Retrieval & Employee Operations Service for AI-Powered HR Assistant",
            "version": "1.0.0",
            "contact": {
                "name": "HR Operations Team",
                "email": "hr-ops@company.internal"
            }
        },
        "tags": [
            {
                "name": "Employee Operations",
                "description": "Endpoints to retrieve employee profile and operational data"
            }
        ],
        "schemes": ["http", "https"]
    }

    Swagger(app, config=swagger_config, template=swagger_template)

    # Initialize SQLAlchemy & Seed Data
    db.init_app(app)
    init_db(app)

    # ------------------ API Endpoints ------------------

    @app.route('/', methods=['GET'])
    def root():
        """Root endpoint with service status and links"""
        return jsonify({
            "service": "HR Operations API",
            "status": "online",
            "swagger_docs": "/apidocs/",
            "sample_employees": ["EMP1001", "EMP1004", "EMP1007", "EMP1008", "EMP1009", "EMP1010", "EMP1011", "EMP1012"]
        }), 200

    @app.route('/employees', methods=['GET'])
    def list_employees():
        """
        List all employees with summary info
        ---
        tags:
          - Employee Operations
        summary: List all employees
        description: Retrieve a list of all employees in the organization
        responses:
          200:
            description: List of employee summaries
            schema:
              type: array
              items:
                type: object
                properties:
                  employee_id:
                    type: string
                    example: "EMP1007"
                  full_name:
                    type: string
                    example: "John Doe"
                  designation:
                    type: string
                    example: "Senior Software Engineer"
                  department:
                    type: string
                    example: "Engineering"
                  employment_status:
                    type: string
                    example: "Active"
        """
        employees = Employee.query.all()
        return jsonify([
            {
                "employee_id": emp.id,
                "full_name": emp.full_name,
                "email": emp.email,
                "designation": emp.designation,
                "department": emp.department.name if emp.department else None,
                "employment_status": emp.employment_status
            }
            for emp in employees
        ]), 200

    @app.route('/employees/<employee_id>', methods=['GET'])
    def get_employee_full_profile(employee_id):
        """
        Get complete employee profile
        ---
        tags:
          - Employee Operations
        summary: Get complete employee profile
        description: Retrieve full employee record including basic info, job details, department info, manager info, and employment status
        parameters:
          - name: employee_id
            in: path
            type: string
            required: true
            description: The unique identifier of the employee (e.g., EMP1007)
        responses:
          200:
            description: Complete employee profile object
            schema:
              type: object
              properties:
                basic_info:
                  type: object
                  properties:
                    employee_id:
                      type: string
                      example: "EMP1007"
                    first_name:
                      type: string
                      example: "John"
                    last_name:
                      type: string
                      example: "Doe"
                    full_name:
                      type: string
                      example: "John Doe"
                    email:
                      type: string
                      example: "john.doe@company.com"
                    phone:
                      type: string
                      example: "+1 (415) 555-0147"
                job_details:
                  type: object
                  properties:
                    employee_id:
                      type: string
                      example: "EMP1007"
                    designation:
                      type: string
                      example: "Senior Software Engineer"
                    department:
                      type: string
                      example: "Engineering"
                    department_code:
                      type: string
                      example: "ENG"
                    grade:
                      type: string
                      example: "L5"
                    work_location:
                      type: string
                      example: "San Francisco, CA (Hybrid)"
                department:
                  type: object
                  properties:
                    employee_id:
                      type: string
                      example: "EMP1007"
                    department_id:
                      type: integer
                      example: 1
                    department_name:
                      type: string
                      example: "Engineering"
                    department_code:
                      type: string
                      example: "ENG"
                    location:
                      type: string
                      example: "San Francisco HQ - Building 1, Floor 4"
                    description:
                      type: string
                      example: "Core software engineering, platform infrastructure, and DevOps teams."
                    total_department_members:
                      type: integer
                      example: 4
                manager:
                  type: object
                  properties:
                    employee_id:
                      type: string
                      example: "EMP1007"
                    has_manager:
                      type: boolean
                      example: true
                    manager:
                      type: object
                      properties:
                        manager_id:
                          type: string
                          example: "EMP1004"
                        full_name:
                          type: string
                          example: "Sarah Jenkins"
                        email:
                          type: string
                          example: "sarah.jenkins@company.com"
                        phone:
                          type: string
                          example: "+1 (415) 555-0114"
                        designation:
                          type: string
                          example: "Engineering Director - Backend & Cloud"
                        department:
                          type: string
                          example: "Engineering"
                employment_status:
                  type: object
                  properties:
                    employee_id:
                      type: string
                      example: "EMP1007"
                    full_name:
                      type: string
                      example: "John Doe"
                    employment_status:
                      type: string
                      example: "Active"
                    date_of_joining:
                      type: string
                      example: "2021-06-14"
                    is_active:
                      type: boolean
                      example: true
          404:
            description: Employee not found
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Employee not found with ID: EMP9999"
        """
        emp = Employee.query.get(employee_id)
        if not emp:
            return jsonify({"error": f"Employee not found with ID: {employee_id}"}), 404
        return jsonify(emp.to_full_profile()), 200

    @app.route('/employees/<employee_id>/basic-info', methods=['GET'])
    def get_employee_basic_info(employee_id):
        """
        Get employee basic information
        ---
        tags:
          - Employee Operations
        summary: Get basic info (Name, email, phone, employee ID)
        description: Retrieve personal contact and identification details for an employee
        parameters:
          - name: employee_id
            in: path
            type: string
            required: true
            description: The unique identifier of the employee (e.g., EMP1007)
        responses:
          200:
            description: Basic employee information
            schema:
              type: object
              properties:
                employee_id:
                  type: string
                  example: "EMP1007"
                first_name:
                  type: string
                  example: "John"
                last_name:
                  type: string
                  example: "Doe"
                full_name:
                  type: string
                  example: "John Doe"
                email:
                  type: string
                  example: "john.doe@company.com"
                phone:
                  type: string
                  example: "+1 (415) 555-0147"
          404:
            description: Employee not found
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Employee not found with ID: EMP9999"
        """
        emp = Employee.query.get(employee_id)
        if not emp:
            return jsonify({"error": f"Employee not found with ID: {employee_id}"}), 404
        return jsonify(emp.to_basic_info()), 200

    @app.route('/employees/<employee_id>/job-details', methods=['GET'])
    def get_employee_job_details(employee_id):
        """
        Get employee job details
        ---
        tags:
          - Employee Operations
        summary: Get job details (Designation, department, grade)
        description: Retrieve designation, department name/code, grade, and work location
        parameters:
          - name: employee_id
            in: path
            type: string
            required: true
            description: The unique identifier of the employee (e.g., EMP1007)
        responses:
          200:
            description: Employee job details
            schema:
              type: object
              properties:
                employee_id:
                  type: string
                  example: "EMP1007"
                designation:
                  type: string
                  example: "Senior Software Engineer"
                department:
                  type: string
                  example: "Engineering"
                department_code:
                  type: string
                  example: "ENG"
                grade:
                  type: string
                  example: "L5"
                work_location:
                  type: string
                  example: "San Francisco, CA (Hybrid)"
          404:
            description: Employee not found
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Employee not found with ID: EMP9999"
        """
        emp = Employee.query.get(employee_id)
        if not emp:
            return jsonify({"error": f"Employee not found with ID: {employee_id}"}), 404
        return jsonify(emp.to_job_details()), 200

    @app.route('/employees/<employee_id>/manager', methods=['GET'])
    def get_employee_manager(employee_id):
        """
        Get employee reporting manager details
        ---
        tags:
          - Employee Operations
        summary: Get reporting manager details
        description: Retrieve reporting manager ID, name, email, phone, designation, and department
        parameters:
          - name: employee_id
            in: path
            type: string
            required: true
            description: The unique identifier of the employee (e.g., EMP1007)
        responses:
          200:
            description: Reporting manager details
            schema:
              type: object
              properties:
                employee_id:
                  type: string
                  example: "EMP1007"
                has_manager:
                  type: boolean
                  example: true
                manager:
                  type: object
                  properties:
                    manager_id:
                      type: string
                      example: "EMP1004"
                    full_name:
                      type: string
                      example: "Sarah Jenkins"
                    email:
                      type: string
                      example: "sarah.jenkins@company.com"
                    phone:
                      type: string
                      example: "+1 (415) 555-0114"
                    designation:
                      type: string
                      example: "Engineering Director - Backend & Cloud"
                    department:
                      type: string
                      example: "Engineering"
          404:
            description: Employee not found
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Employee not found with ID: EMP9999"
        """
        emp = Employee.query.get(employee_id)
        if not emp:
            return jsonify({"error": f"Employee not found with ID: {employee_id}"}), 404
        return jsonify(emp.to_manager_info()), 200

    @app.route('/employees/<employee_id>/department', methods=['GET'])
    def get_employee_department(employee_id):
        """
        Get employee department information
        ---
        tags:
          - Employee Operations
        summary: Get department information
        description: Retrieve department details including name, code, office location, and description
        parameters:
          - name: employee_id
            in: path
            type: string
            required: true
            description: The unique identifier of the employee (e.g., EMP1007)
        responses:
          200:
            description: Department details
            schema:
              type: object
              properties:
                employee_id:
                  type: string
                  example: "EMP1007"
                department_id:
                  type: integer
                  example: 1
                department_name:
                  type: string
                  example: "Engineering"
                department_code:
                  type: string
                  example: "ENG"
                location:
                  type: string
                  example: "San Francisco HQ - Building 1, Floor 4"
                description:
                  type: string
                  example: "Core software engineering, platform infrastructure, and DevOps teams."
                total_department_members:
                  type: integer
                  example: 4
          404:
            description: Employee not found
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Employee not found with ID: EMP9999"
        """
        emp = Employee.query.get(employee_id)
        if not emp:
            return jsonify({"error": f"Employee not found with ID: {employee_id}"}), 404
        return jsonify(emp.to_department_info()), 200

    @app.route('/employees/<employee_id>/employment-status', methods=['GET'])
    def get_employee_employment_status(employee_id):
        """
        Get employee employment status
        ---
        tags:
          - Employee Operations
        summary: Get employment status (Active, resigned, terminated, etc.)
        description: Retrieve current employment status, date of joining, and active flag
        parameters:
          - name: employee_id
            in: path
            type: string
            required: true
            description: The unique identifier of the employee (e.g., EMP1007)
        responses:
          200:
            description: Employment status details
            schema:
              type: object
              properties:
                employee_id:
                  type: string
                  example: "EMP1007"
                full_name:
                  type: string
                  example: "John Doe"
                employment_status:
                  type: string
                  example: "Active"
                date_of_joining:
                  type: string
                  example: "2021-06-14"
                is_active:
                  type: boolean
                  example: true
          404:
            description: Employee not found
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Employee not found with ID: EMP9999"
        """
        emp = Employee.query.get(employee_id)
        if not emp:
            return jsonify({"error": f"Employee not found with ID: {employee_id}"}), 404
        return jsonify(emp.to_employment_status()), 200

    return app

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="HR Operations Service")
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', 9090)),
                        help="Port to run the HR Operations server on (default: 9090 or PORT env var)")
    parser.add_argument('--host', type=str, default=os.environ.get('HOST', '0.0.0.0'),
                        help="Host to run the server on (default: 0.0.0.0)")
    parser.add_argument('--debug', action='store_true', default=False,
                        help="Run in debug mode")

    args = parser.parse_args()

    app = create_app()
    print(f"\n=======================================================")
    print(f" HR Operations API Service Started")
    print(f" Base URL:    http://localhost:{args.port}/")
    print(f" Swagger UI:  http://localhost:{args.port}/apidocs/")
    print(f" SQLite DB:   hr_operations.db (auto-seeded)")
    print(f"=======================================================\n")
    app.run(host=args.host, port=args.port, debug=args.debug)
