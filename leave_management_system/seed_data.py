from datetime import date, datetime
from models import db, LeaveBalance, LeaveRequest, Holiday


def init_db(app):
    with app.app_context():
        db.create_all()
        if Holiday.query.first() is not None:
            return  # Already seeded

        # ----------------------------------------------------------------
        # 1. HOLIDAYS  (year 2026 - matches demo runtime year)
        # ----------------------------------------------------------------
        holidays = [
            # ---- All-company national/public holidays ----
            Holiday(name="New Year's Day",          date=date(2026, 1,  1),  year=2026, holiday_type="Public",  location=None,            is_optional=False, description="First day of the new year."),
            Holiday(name="Martin Luther King Jr. Day", date=date(2026, 1, 19), year=2026, holiday_type="Public",  location=None,            is_optional=False, description="Federal holiday honouring civil rights leader Dr. Martin Luther King Jr."),
            Holiday(name="Presidents' Day",         date=date(2026, 2, 16),  year=2026, holiday_type="Public",  location=None,            is_optional=False, description="Honours all U.S. presidents."),
            Holiday(name="Memorial Day",            date=date(2026, 5, 25),  year=2026, holiday_type="Public",  location=None,            is_optional=False, description="Honours military personnel who died in service."),
            Holiday(name="Independence Day",        date=date(2026, 7,  4),  year=2026, holiday_type="Public",  location=None,            is_optional=False, description="U.S. Independence Day."),
            Holiday(name="Labor Day",               date=date(2026, 9,  7),  year=2026, holiday_type="Public",  location=None,            is_optional=False, description="Celebrates the labour movement and working people."),
            Holiday(name="Thanksgiving Day",        date=date(2026, 11, 26), year=2026, holiday_type="Public",  location=None,            is_optional=False, description="National day of giving thanks."),
            Holiday(name="Christmas Day",           date=date(2026, 12, 25), year=2026, holiday_type="Public",  location=None,            is_optional=False, description="Christmas holiday."),

            # ---- Company-wide shutdown days ----
            Holiday(name="Company Foundation Day",  date=date(2026, 3, 15),  year=2026, holiday_type="Company", location=None,            is_optional=False, description="Anniversary of company founding. All offices closed."),
            Holiday(name="Summer Recess Day",       date=date(2026, 8, 14),  year=2026, holiday_type="Company", location=None,            is_optional=False, description="Annual company summer recess."),
            Holiday(name="Year-End Recess",         date=date(2026, 12, 26), year=2026, holiday_type="Company", location=None,            is_optional=False, description="Post-Christmas year-end company closure."),

            # ---- Optional / floating holidays ----
            Holiday(name="Diwali (Optional)",       date=date(2026, 10, 28), year=2026, holiday_type="Optional", location=None,           is_optional=True,  description="Festival of Lights — observed as an optional holiday for employees who celebrate."),
            Holiday(name="Eid al-Adha (Optional)",  date=date(2026, 6, 16),  year=2026, holiday_type="Optional", location=None,           is_optional=True,  description="Optional holiday for employees observing Eid al-Adha."),

            # ---- Regional holidays ----
            Holiday(name="César Chávez Day",        date=date(2026, 3, 31),  year=2026, holiday_type="Regional", location="San Francisco", is_optional=False, description="Observed in California to honour labour activist César Chávez."),
            Holiday(name="Juneteenth National Day", date=date(2026, 6, 19),  year=2026, holiday_type="Regional", location="Austin",        is_optional=False, description="Juneteenth — freedom day in Texas and federally recognised."),
            Holiday(name="Columbus Day",            date=date(2026, 10, 12), year=2026, holiday_type="Regional", location="New York",      is_optional=False, description="Observed in New York as a public holiday."),
        ]
        db.session.add_all(holidays)
        db.session.commit()

        # ----------------------------------------------------------------
        # 2. LEAVE BALANCES (2026)  — correlated to employee_retreival_system
        #    Employee IDs: EMP1001-EMP1012
        # ----------------------------------------------------------------

        # Tenure-based entitlements:
        #   E-grade (C-suite)  → 25 annual + 10 sick + 5 casual + 5 comp_off
        #   M-grade (managers) → 22 annual + 10 sick + 5 casual + 3 comp_off
        #   L6-L5              → 20 annual + 10 sick + 5 casual
        #   L4-L3              → 18 annual + 10 sick + 5 casual

        balances = [
            # EMP1001 – Alexander Wright, CTO (E2, joined 2018, SF)
            LeaveBalance(employee_id="EMP1001", year=2026,
                         annual_entitled=25, sick_entitled=10, casual_entitled=5, comp_off_entitled=5,
                         annual_used=4, sick_used=1, casual_used=1, comp_off_used=0,
                         carried_forward=3),

            # EMP1002 – Elena Rostova, CPO (E2, joined 2019, SF)
            LeaveBalance(employee_id="EMP1002", year=2026,
                         annual_entitled=25, sick_entitled=10, casual_entitled=5, comp_off_entitled=5,
                         annual_used=5, sick_used=2, casual_used=0, comp_off_used=1,
                         carried_forward=2),

            # EMP1003 – Marcus Chen, VP Finance (E1, joined 2019, NY)
            LeaveBalance(employee_id="EMP1003", year=2026,
                         annual_entitled=25, sick_entitled=10, casual_entitled=5, comp_off_entitled=5,
                         annual_used=6, sick_used=3, casual_used=1, comp_off_used=0,
                         carried_forward=4),

            # EMP1004 – Sarah Jenkins, Eng Director (M2, joined 2020, SF)
            LeaveBalance(employee_id="EMP1004", year=2026,
                         annual_entitled=22, sick_entitled=10, casual_entitled=5, comp_off_entitled=3,
                         annual_used=5, sick_used=2, casual_used=2, comp_off_used=1,
                         carried_forward=2),

            # EMP1005 – David Kim, HR Manager (M1, joined 2020, SF)
            LeaveBalance(employee_id="EMP1005", year=2026,
                         annual_entitled=22, sick_entitled=10, casual_entitled=5, comp_off_entitled=3,
                         annual_used=3, sick_used=1, casual_used=0, comp_off_used=0,
                         carried_forward=1),

            # EMP1006 – Priya Sharma, Principal PM (L6, joined 2021, SF remote)
            LeaveBalance(employee_id="EMP1006", year=2026,
                         annual_entitled=20, sick_entitled=10, casual_entitled=5, comp_off_entitled=0,
                         annual_used=7, sick_used=2, casual_used=1, comp_off_used=0,
                         carried_forward=0),

            # EMP1007 – John Doe, Sr SWE (L5, joined 2021, SF hybrid)
            LeaveBalance(employee_id="EMP1007", year=2026,
                         annual_entitled=20, sick_entitled=10, casual_entitled=5, comp_off_entitled=0,
                         annual_used=8, sick_used=3, casual_used=2, comp_off_used=0,
                         carried_forward=1),

            # EMP1008 – Emily Watson, HR Ops Specialist (L4, joined 2022, SF onsite)
            LeaveBalance(employee_id="EMP1008", year=2026,
                         annual_entitled=18, sick_entitled=10, casual_entitled=5, comp_off_entitled=0,
                         annual_used=4, sick_used=0, casual_used=1, comp_off_used=0,
                         carried_forward=0),

            # EMP1009 – Michael Brown, Sr Financial Analyst (L5, joined 2021, NY) – On Notice
            LeaveBalance(employee_id="EMP1009", year=2026,
                         annual_entitled=20, sick_entitled=10, casual_entitled=5, comp_off_entitled=0,
                         annual_used=12, sick_used=5, casual_used=3, comp_off_used=0,
                         carried_forward=0),

            # EMP1010 – Sophia Martinez, Growth Mktg Lead (L5, joined 2022, Austin) – On Leave
            LeaveBalance(employee_id="EMP1010", year=2026,
                         annual_entitled=20, sick_entitled=10, casual_entitled=5, maternity_entitled=90,
                         annual_used=2, sick_used=1, casual_used=0, maternity_used=45,
                         carried_forward=0),

            # EMP1011 – James Wilson, SWE II (L4, joined 2022, SF remote) – Resigned
            LeaveBalance(employee_id="EMP1011", year=2026,
                         annual_entitled=18, sick_entitled=10, casual_entitled=5, comp_off_entitled=0,
                         annual_used=18, sick_used=4, casual_used=5, comp_off_used=0,
                         carried_forward=0),

            # EMP1012 – Rachel Green, Assoc QA (L3, joined 2023, SF hybrid) – Terminated
            LeaveBalance(employee_id="EMP1012", year=2026,
                         annual_entitled=18, sick_entitled=10, casual_entitled=5, comp_off_entitled=0,
                         annual_used=18, sick_used=10, casual_used=5, comp_off_used=0,
                         carried_forward=0),
        ]
        db.session.add_all(balances)
        db.session.commit()

        # ----------------------------------------------------------------
        # 3. LEAVE REQUESTS (historical + current 2025-2026)
        # ----------------------------------------------------------------
        requests = [
            # -------- EMP1001 – Alexander Wright --------
            LeaveRequest(employee_id="EMP1001", leave_type="Annual",
                         start_date=date(2026, 1, 2), end_date=date(2026, 1, 3), days_requested=2,
                         reason="New Year holiday extension with family.", status="Approved",
                         applied_on=datetime(2025, 12, 20, 9, 0, 0), approved_by=None,
                         approved_on=datetime(2025, 12, 21, 11, 0, 0)),

            LeaveRequest(employee_id="EMP1001", leave_type="Annual",
                         start_date=date(2026, 4, 7), end_date=date(2026, 4, 9), days_requested=3,
                         reason="Spring vacation.", status="Pending",
                         applied_on=datetime(2026, 3, 25, 10, 15, 0)),

            # -------- EMP1002 – Elena Rostova --------
            LeaveRequest(employee_id="EMP1002", leave_type="Sick",
                         start_date=date(2026, 2, 3), end_date=date(2026, 2, 4), days_requested=2,
                         reason="Flu - doctor advised rest.", status="Approved",
                         applied_on=datetime(2026, 2, 3, 8, 30, 0), approved_by=None,
                         approved_on=datetime(2026, 2, 3, 9, 0, 0)),

            LeaveRequest(employee_id="EMP1002", leave_type="Annual",
                         start_date=date(2026, 3, 16), end_date=date(2026, 3, 20), days_requested=5,
                         reason="Annual leave — overseas travel.", status="Approved",
                         applied_on=datetime(2026, 2, 28, 14, 0, 0), approved_by=None,
                         approved_on=datetime(2026, 3, 1, 10, 0, 0)),

            # -------- EMP1003 – Marcus Chen --------
            LeaveRequest(employee_id="EMP1003", leave_type="Annual",
                         start_date=date(2026, 1, 26), end_date=date(2026, 1, 30), days_requested=5,
                         reason="Planned vacation — Q1 annual leave.", status="Approved",
                         applied_on=datetime(2026, 1, 10, 10, 0, 0), approved_by=None,
                         approved_on=datetime(2026, 1, 11, 9, 0, 0)),

            LeaveRequest(employee_id="EMP1003", leave_type="Sick",
                         start_date=date(2026, 3, 3), end_date=date(2026, 3, 5), days_requested=3,
                         reason="Acute back pain — medical treatment.", status="Approved",
                         applied_on=datetime(2026, 3, 3, 7, 45, 0), approved_by=None,
                         approved_on=datetime(2026, 3, 3, 9, 0, 0)),

            # -------- EMP1004 – Sarah Jenkins --------
            LeaveRequest(employee_id="EMP1004", leave_type="Casual",
                         start_date=date(2026, 2, 13), end_date=date(2026, 2, 14), days_requested=2,
                         reason="Valentine's weekend trip.", status="Approved",
                         applied_on=datetime(2026, 2, 5, 11, 0, 0), approved_by="EMP1001",
                         approved_on=datetime(2026, 2, 6, 10, 0, 0)),

            LeaveRequest(employee_id="EMP1004", leave_type="Annual",
                         start_date=date(2026, 4, 20), end_date=date(2026, 4, 24), days_requested=5,
                         reason="Spring break holiday.", status="Pending",
                         applied_on=datetime(2026, 4, 1, 9, 0, 0)),

            # -------- EMP1005 – David Kim --------
            LeaveRequest(employee_id="EMP1005", leave_type="Annual",
                         start_date=date(2026, 3, 9), end_date=date(2026, 3, 11), days_requested=3,
                         reason="Family event.", status="Approved",
                         applied_on=datetime(2026, 2, 20, 10, 0, 0), approved_by="EMP1002",
                         approved_on=datetime(2026, 2, 21, 9, 30, 0)),

            # -------- EMP1006 – Priya Sharma --------
            LeaveRequest(employee_id="EMP1006", leave_type="Annual",
                         start_date=date(2026, 2, 16), end_date=date(2026, 2, 20), days_requested=5,
                         reason="Vacation to India — family visit.", status="Approved",
                         applied_on=datetime(2026, 1, 25, 14, 30, 0), approved_by="EMP1001",
                         approved_on=datetime(2026, 1, 26, 10, 0, 0)),

            LeaveRequest(employee_id="EMP1006", leave_type="Sick",
                         start_date=date(2026, 4, 1), end_date=date(2026, 4, 2), days_requested=2,
                         reason="Severe migraine.", status="Approved",
                         applied_on=datetime(2026, 4, 1, 8, 0, 0), approved_by="EMP1001",
                         approved_on=datetime(2026, 4, 1, 9, 0, 0)),

            # -------- EMP1007 – John Doe --------
            LeaveRequest(employee_id="EMP1007", leave_type="Annual",
                         start_date=date(2026, 1, 5), end_date=date(2026, 1, 9), days_requested=5,
                         reason="New Year holiday vacation.", status="Approved",
                         applied_on=datetime(2025, 12, 15, 10, 0, 0), approved_by="EMP1004",
                         approved_on=datetime(2025, 12, 16, 11, 0, 0)),

            LeaveRequest(employee_id="EMP1007", leave_type="Sick",
                         start_date=date(2026, 2, 10), end_date=date(2026, 2, 12), days_requested=3,
                         reason="Viral fever.", status="Approved",
                         applied_on=datetime(2026, 2, 10, 9, 0, 0), approved_by="EMP1004",
                         approved_on=datetime(2026, 2, 10, 10, 30, 0)),

            LeaveRequest(employee_id="EMP1007", leave_type="Casual",
                         start_date=date(2026, 3, 27), end_date=date(2026, 3, 28), days_requested=2,
                         reason="Personal errand.", status="Approved",
                         applied_on=datetime(2026, 3, 20, 10, 0, 0), approved_by="EMP1004",
                         approved_on=datetime(2026, 3, 21, 9, 0, 0)),

            LeaveRequest(employee_id="EMP1007", leave_type="Annual",
                         start_date=date(2026, 5, 11), end_date=date(2026, 5, 15), days_requested=5,
                         reason="Summer vacation planned.", status="Pending",
                         applied_on=datetime(2026, 4, 25, 11, 0, 0)),

            # -------- EMP1008 – Emily Watson --------
            LeaveRequest(employee_id="EMP1008", leave_type="Annual",
                         start_date=date(2026, 1, 19), end_date=date(2026, 1, 22), days_requested=4,
                         reason="Short trip.", status="Approved",
                         applied_on=datetime(2026, 1, 8, 14, 0, 0), approved_by="EMP1005",
                         approved_on=datetime(2026, 1, 9, 10, 0, 0)),

            LeaveRequest(employee_id="EMP1008", leave_type="Casual",
                         start_date=date(2026, 3, 6), end_date=date(2026, 3, 6), days_requested=1,
                         reason="Parent-teacher meeting.", status="Approved",
                         applied_on=datetime(2026, 3, 4, 9, 0, 0), approved_by="EMP1005",
                         approved_on=datetime(2026, 3, 4, 11, 0, 0)),

            # -------- EMP1009 – Michael Brown (On Notice) --------
            LeaveRequest(employee_id="EMP1009", leave_type="Annual",
                         start_date=date(2026, 1, 12), end_date=date(2026, 1, 16), days_requested=5,
                         reason="Pre-planned annual leave.", status="Approved",
                         applied_on=datetime(2025, 12, 20, 10, 0, 0), approved_by="EMP1003",
                         approved_on=datetime(2025, 12, 22, 9, 30, 0)),

            LeaveRequest(employee_id="EMP1009", leave_type="Sick",
                         start_date=date(2026, 2, 17), end_date=date(2026, 2, 21), days_requested=5,
                         reason="Medical procedure and recovery.", status="Approved",
                         applied_on=datetime(2026, 2, 10, 9, 0, 0), approved_by="EMP1003",
                         approved_on=datetime(2026, 2, 11, 10, 0, 0)),

            LeaveRequest(employee_id="EMP1009", leave_type="Annual",
                         start_date=date(2026, 4, 6), end_date=date(2026, 4, 10), days_requested=5,
                         reason="Notice period encashment leave.", status="Pending",
                         applied_on=datetime(2026, 3, 28, 11, 0, 0)),

            # -------- EMP1010 – Sophia Martinez (On Leave — Maternity) --------
            LeaveRequest(employee_id="EMP1010", leave_type="Maternity",
                         start_date=date(2026, 3, 1), end_date=date(2026, 7, 31), days_requested=90,
                         reason="Maternity leave — birth of child.", status="Approved",
                         applied_on=datetime(2026, 2, 1, 10, 0, 0), approved_by="EMP1002",
                         approved_on=datetime(2026, 2, 3, 9, 0, 0)),

            LeaveRequest(employee_id="EMP1010", leave_type="Annual",
                         start_date=date(2026, 1, 26), end_date=date(2026, 1, 27), days_requested=2,
                         reason="Pre-maternity errands.", status="Approved",
                         applied_on=datetime(2026, 1, 20, 14, 0, 0), approved_by="EMP1002",
                         approved_on=datetime(2026, 1, 21, 9, 0, 0)),

            # -------- EMP1011 – James Wilson (Resigned) --------
            LeaveRequest(employee_id="EMP1011", leave_type="Annual",
                         start_date=date(2026, 1, 5), end_date=date(2026, 1, 9), days_requested=5,
                         reason="Leave before notice period start.", status="Approved",
                         applied_on=datetime(2025, 12, 20, 10, 0, 0), approved_by="EMP1004",
                         approved_on=datetime(2025, 12, 22, 9, 0, 0)),

            LeaveRequest(employee_id="EMP1011", leave_type="Sick",
                         start_date=date(2026, 2, 2), end_date=date(2026, 2, 5), days_requested=4,
                         reason="Stress-related sick leave during notice period.", status="Approved",
                         applied_on=datetime(2026, 2, 2, 8, 30, 0), approved_by="EMP1004",
                         approved_on=datetime(2026, 2, 2, 10, 0, 0)),

            LeaveRequest(employee_id="EMP1011", leave_type="Annual",
                         start_date=date(2026, 3, 16), end_date=date(2026, 3, 31), days_requested=12,
                         reason="Garden leave during final notice period.", status="Cancelled",
                         applied_on=datetime(2026, 3, 1, 9, 0, 0),
                         cancel_reason="Employment ended before leave start date."),

            # -------- EMP1012 – Rachel Green (Terminated) --------
            LeaveRequest(employee_id="EMP1012", leave_type="Sick",
                         start_date=date(2025, 12, 1), end_date=date(2025, 12, 5), days_requested=5,
                         reason="Extended sick leave — frequently absent.", status="Approved",
                         applied_on=datetime(2025, 11, 30, 10, 0, 0), approved_by="EMP1004",
                         approved_on=datetime(2025, 11, 30, 11, 30, 0)),

            LeaveRequest(employee_id="EMP1012", leave_type="Annual",
                         start_date=date(2026, 1, 12), end_date=date(2026, 1, 16), days_requested=5,
                         reason="Leave requested.", status="Rejected",
                         applied_on=datetime(2026, 1, 8, 9, 0, 0), approved_by="EMP1004",
                         approved_on=datetime(2026, 1, 8, 15, 0, 0),
                         rejection_reason="Employment was terminated before the requested leave dates."),
        ]
        db.session.add_all(requests)
        db.session.commit()
