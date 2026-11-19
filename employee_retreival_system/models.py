from flask_sqlalchemy import SQLAlchemy
from datetime import date

db = SQLAlchemy()

class Department(db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    code = db.Column(db.String(20), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)
    location = db.Column(db.String(150), nullable=True)

    employees = db.relationship('Employee', back_populates='department', foreign_keys='Employee.department_id')

    def to_dict(self):
        return {
            "department_id": self.id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "location": self.location,
            "total_employees": len(self.employees)
        }


class Employee(db.Model):
    __tablename__ = 'employees'

    id = db.Column(db.String(50), primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    
    designation = db.Column(db.String(100), nullable=False)
    grade = db.Column(db.String(50), nullable=False)
    
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    manager_id = db.Column(db.String(50), db.ForeignKey('employees.id'), nullable=True)
    
    employment_status = db.Column(db.String(50), nullable=False, default='Active')
    date_of_joining = db.Column(db.Date, nullable=False, default=date.today)
    work_location = db.Column(db.String(150), nullable=True)

    # Relationships
    department = db.relationship('Department', back_populates='employees', foreign_keys=[department_id])
    manager = db.relationship('Employee', remote_side=[id], backref=db.backref('direct_reports', lazy='dynamic'))

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def to_basic_info(self):
        return {
            "employee_id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone
        }

    def to_job_details(self):
        return {
            "employee_id": self.id,
            "designation": self.designation,
            "department": self.department.name if self.department else None,
            "department_code": self.department.code if self.department else None,
            "grade": self.grade,
            "work_location": self.work_location
        }

    def to_manager_info(self):
        if not self.manager:
            return {
                "employee_id": self.id,
                "has_manager": False,
                "manager": None,
                "message": "Employee reports directly to executive leadership / board."
            }
        return {
            "employee_id": self.id,
            "has_manager": True,
            "manager": {
                "manager_id": self.manager.id,
                "full_name": self.manager.full_name,
                "email": self.manager.email,
                "phone": self.manager.phone,
                "designation": self.manager.designation,
                "department": self.manager.department.name if self.manager.department else None
            }
        }

    def to_department_info(self):
        if not self.department:
            return {
                "employee_id": self.id,
                "department": None
            }
        return {
            "employee_id": self.id,
            "department_id": self.department.id,
            "department_name": self.department.name,
            "department_code": self.department.code,
            "location": self.department.location,
            "description": self.department.description,
            "total_department_members": len(self.department.employees)
        }

    def to_employment_status(self):
        return {
            "employee_id": self.id,
            "full_name": self.full_name,
            "employment_status": self.employment_status,
            "date_of_joining": self.date_of_joining.isoformat() if self.date_of_joining else None,
            "is_active": self.employment_status.lower() == 'active'
        }

    def to_full_profile(self):
        return {
            "basic_info": self.to_basic_info(),
            "job_details": self.to_job_details(),
            "department": self.to_department_info(),
            "manager": self.to_manager_info(),
            "employment_status": self.to_employment_status()
        }
