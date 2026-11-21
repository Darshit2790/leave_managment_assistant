from datetime import date
from models import db, Department, Employee

def init_db(app):
    with app.app_context():
        db.create_all()
        # Check if already seeded
        if Department.query.first() is not None:
            return

        # 1. Departments
        eng = Department(
            id=1,
            name="Engineering",
            code="ENG",
            description="Core software engineering, platform infrastructure, and DevOps teams.",
            location="San Francisco HQ - Building 1, Floor 4"
        )
        hr = Department(
            id=2,
            name="Human Resources",
            code="HR",
            description="Talent acquisition, employee relations, total rewards, and HR operations.",
            location="San Francisco HQ - Building 1, Floor 2"
        )
        prod = Department(
            id=3,
            name="Product & Design",
            code="PD",
            description="Product management, UI/UX design, and user research.",
            location="San Francisco HQ - Building 1, Floor 3"
        )
        fin = Department(
            id=4,
            name="Finance & Accounting",
            code="FIN",
            description="Financial planning & analysis, payroll, corporate accounting, and audits.",
            location="New York Hub - Floor 6"
        )
        mkt = Department(
            id=5,
            name="Marketing & Growth",
            code="MKT",
            description="Brand marketing, demand generation, product marketing, and PR.",
            location="Austin Regional Office - Floor 2"
        )

        db.session.add_all([eng, hr, prod, fin, mkt])
        db.session.commit()

        # 2. Employees (Hierarchical dummy data)
        # Executive leadership
        emp001 = Employee(
            id="EMP1001",
            first_name="Alexander",
            last_name="Wright",
            email="alexander.wright@company.com",
            phone="+1 (415) 555-0100",
            designation="Chief Technology Officer",
            grade="E2",
            department_id=eng.id,
            manager_id=None,
            employment_status="Active",
            date_of_joining=date(2018, 1, 15),
            work_location="San Francisco, CA (Hybrid)"
        )

        emp002 = Employee(
            id="EMP1002",
            first_name="Elena",
            last_name="Rostova",
            email="elena.rostova@company.com",
            phone="+1 (415) 555-0102",
            designation="Chief People Officer",
            grade="E2",
            department_id=hr.id,
            manager_id=None,
            employment_status="Active",
            date_of_joining=date(2019, 3, 1),
            work_location="San Francisco, CA (Hybrid)"
        )

        emp003 = Employee(
            id="EMP1003",
            first_name="Marcus",
            last_name="Chen",
            email="marcus.chen@company.com",
            phone="+1 (212) 555-0105",
            designation="VP of Finance",
            grade="E1",
            department_id=fin.id,
            manager_id=None,
            employment_status="Active",
            date_of_joining=date(2019, 7, 22),
            work_location="New York, NY (Onsite)"
        )

        db.session.add_all([emp001, emp002, emp003])
        db.session.commit()

        # Managers & Leads
        emp004 = Employee(
            id="EMP1004",
            first_name="Sarah",
            last_name="Jenkins",
            email="sarah.jenkins@company.com",
            phone="+1 (415) 555-0114",
            designation="Engineering Director - Backend & Cloud",
            grade="M2",
            department_id=eng.id,
            manager_id="EMP1001",
            employment_status="Active",
            date_of_joining=date(2020, 2, 10),
            work_location="San Francisco, CA (Hybrid)"
        )

        emp005 = Employee(
            id="EMP1005",
            first_name="David",
            last_name="Kim",
            email="david.kim@company.com",
            phone="+1 (415) 555-0125",
            designation="HR Operations Manager",
            grade="M1",
            department_id=hr.id,
            manager_id="EMP1002",
            employment_status="Active",
            date_of_joining=date(2020, 8, 17),
            work_location="San Francisco, CA (Hybrid)"
        )

        emp006 = Employee(
            id="EMP1006",
            first_name="Priya",
            last_name="Sharma",
            email="priya.sharma@company.com",
            phone="+1 (415) 555-0136",
            designation="Principal Product Manager",
            grade="L6",
            department_id=prod.id,
            manager_id="EMP1001",
            employment_status="Active",
            date_of_joining=date(2021, 4, 5),
            work_location="San Francisco, CA (Remote)"
        )

        db.session.add_all([emp004, emp005, emp006])
        db.session.commit()

        # Individual Contributors with various employment statuses
        emp007 = Employee(
            id="EMP1007",
            first_name="John",
            last_name="Doe",
            email="john.doe@company.com",
            phone="+1 (415) 555-0147",
            designation="Senior Software Engineer",
            grade="L5",
            department_id=eng.id,
            manager_id="EMP1004",
            employment_status="Active",
            date_of_joining=date(2021, 6, 14),
            work_location="San Francisco, CA (Hybrid)"
        )

        emp008 = Employee(
            id="EMP1008",
            first_name="Emily",
            last_name="Watson",
            email="emily.watson@company.com",
            phone="+1 (415) 555-0158",
            designation="HR Operations Specialist",
            grade="L4",
            department_id=hr.id,
            manager_id="EMP1005",
            employment_status="Active",
            date_of_joining=date(2022, 1, 10),
            work_location="San Francisco, CA (Onsite)"
        )

        emp009 = Employee(
            id="EMP1009",
            first_name="Michael",
            last_name="Brown",
            email="michael.brown@company.com",
            phone="+1 (212) 555-0169",
            designation="Senior Financial Analyst",
            grade="L5",
            department_id=fin.id,
            manager_id="EMP1003",
            employment_status="On Notice",
            date_of_joining=date(2021, 9, 1),
            work_location="New York, NY (Hybrid)"
        )

        emp010 = Employee(
            id="EMP1010",
            first_name="Sophia",
            last_name="Martinez",
            email="sophia.martinez@company.com",
            phone="+1 (512) 555-0170",
            designation="Growth Marketing Lead",
            grade="L5",
            department_id=mkt.id,
            manager_id="EMP1002",
            employment_status="On Leave",
            date_of_joining=date(2022, 5, 18),
            work_location="Austin, TX (Remote)"
        )

        emp011 = Employee(
            id="EMP1011",
            first_name="James",
            last_name="Wilson",
            email="james.wilson@company.com",
            phone="+1 (415) 555-0181",
            designation="Software Engineer II",
            grade="L4",
            department_id=eng.id,
            manager_id="EMP1004",
            employment_status="Resigned",
            date_of_joining=date(2022, 8, 22),
            work_location="San Francisco, CA (Remote)"
        )

        emp012 = Employee(
            id="EMP1012",
            first_name="Rachel",
            last_name="Green",
            email="rachel.green@company.com",
            phone="+1 (415) 555-0192",
            designation="Associate QA Engineer",
            grade="L3",
            department_id=eng.id,
            manager_id="EMP1004",
            employment_status="Terminated",
            date_of_joining=date(2023, 2, 1),
            work_location="San Francisco, CA (Hybrid)"
        )

        db.session.add_all([emp007, emp008, emp009, emp010, emp011, emp012])
        db.session.commit()
