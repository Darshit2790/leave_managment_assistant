from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime

db = SQLAlchemy()


class LeaveBalance(db.Model):
    """Tracks annual leave entitlements and consumption per employee per year."""
    __tablename__ = 'leave_balances'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    employee_id = db.Column(db.String(50), nullable=False, index=True)
    year = db.Column(db.Integer, nullable=False, default=date.today().year)

    # Annual entitlement (days)
    annual_entitled = db.Column(db.Float, nullable=False, default=20.0)
    sick_entitled = db.Column(db.Float, nullable=False, default=10.0)
    casual_entitled = db.Column(db.Float, nullable=False, default=5.0)
    maternity_entitled = db.Column(db.Float, nullable=False, default=0.0)
    paternity_entitled = db.Column(db.Float, nullable=False, default=0.0)
    comp_off_entitled = db.Column(db.Float, nullable=False, default=0.0)

    # Used (days)
    annual_used = db.Column(db.Float, nullable=False, default=0.0)
    sick_used = db.Column(db.Float, nullable=False, default=0.0)
    casual_used = db.Column(db.Float, nullable=False, default=0.0)
    maternity_used = db.Column(db.Float, nullable=False, default=0.0)
    paternity_used = db.Column(db.Float, nullable=False, default=0.0)
    comp_off_used = db.Column(db.Float, nullable=False, default=0.0)

    # Carried forward from previous year
    carried_forward = db.Column(db.Float, nullable=False, default=0.0)

    __table_args__ = (db.UniqueConstraint('employee_id', 'year', name='uq_emp_year'),)

    def to_balance_summary(self):
        return {
            "employee_id": self.employee_id,
            "year": self.year,
            "balances": {
                "annual": {
                    "entitled": self.annual_entitled,
                    "used": self.annual_used,
                    "carried_forward": self.carried_forward,
                    "available": round(self.annual_entitled + self.carried_forward - self.annual_used, 1)
                },
                "sick": {
                    "entitled": self.sick_entitled,
                    "used": self.sick_used,
                    "available": round(self.sick_entitled - self.sick_used, 1)
                },
                "casual": {
                    "entitled": self.casual_entitled,
                    "used": self.casual_used,
                    "available": round(self.casual_entitled - self.casual_used, 1)
                },
                "maternity": {
                    "entitled": self.maternity_entitled,
                    "used": self.maternity_used,
                    "available": round(self.maternity_entitled - self.maternity_used, 1)
                },
                "paternity": {
                    "entitled": self.paternity_entitled,
                    "used": self.paternity_used,
                    "available": round(self.paternity_entitled - self.paternity_used, 1)
                },
                "comp_off": {
                    "entitled": self.comp_off_entitled,
                    "used": self.comp_off_used,
                    "available": round(self.comp_off_entitled - self.comp_off_used, 1)
                }
            },
            "total_available": round(
                (self.annual_entitled + self.carried_forward - self.annual_used) +
                (self.sick_entitled - self.sick_used) +
                (self.casual_entitled - self.casual_used) +
                (self.comp_off_entitled - self.comp_off_used), 1
            )
        }


class LeaveRequest(db.Model):
    """Individual leave request records."""
    __tablename__ = 'leave_requests'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    employee_id = db.Column(db.String(50), nullable=False, index=True)
    leave_type = db.Column(db.String(50), nullable=False)   # Annual, Sick, Casual, Maternity, Paternity, Comp Off
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days_requested = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(30), nullable=False, default='Pending')
    # Statuses: Pending, Approved, Rejected, Cancelled
    applied_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    approved_by = db.Column(db.String(50), nullable=True)   # manager employee_id
    approved_on = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.String(500), nullable=True)
    cancel_reason = db.Column(db.String(500), nullable=True)

    def to_dict(self):
        return {
            "request_id": self.id,
            "employee_id": self.employee_id,
            "leave_type": self.leave_type,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "days_requested": self.days_requested,
            "reason": self.reason,
            "status": self.status,
            "applied_on": self.applied_on.strftime("%Y-%m-%d %H:%M:%S") if self.applied_on else None,
            "approved_by": self.approved_by,
            "approved_on": self.approved_on.strftime("%Y-%m-%d %H:%M:%S") if self.approved_on else None,
            "rejection_reason": self.rejection_reason,
            "cancel_reason": self.cancel_reason
        }


class Holiday(db.Model):
    """Company-wide and location-specific public/company holidays."""
    __tablename__ = 'holidays'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(150), nullable=False)
    date = db.Column(db.Date, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    holiday_type = db.Column(db.String(50), nullable=False, default='Public')
    # Types: Public, Company, Optional, Regional
    location = db.Column(db.String(100), nullable=True)
    # None = all locations; "San Francisco", "New York", "Austin" = regional
    is_optional = db.Column(db.Boolean, nullable=False, default=False)
    description = db.Column(db.String(300), nullable=True)

    def to_dict(self):
        return {
            "holiday_id": self.id,
            "name": self.name,
            "date": self.date.isoformat(),
            "day": self.date.strftime("%A"),
            "year": self.year,
            "holiday_type": self.holiday_type,
            "location": self.location if self.location else "All Locations",
            "is_optional": self.is_optional,
            "description": self.description
        }
