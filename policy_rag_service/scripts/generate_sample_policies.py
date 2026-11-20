"""Generate FICTIONAL sample HR policy PDFs so you can test the pipeline."""
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

OUT = Path(__file__).resolve().parent.parent / "data" / "policies"

DOCS = {
    "leave_policy.pdf": [
        ("1. Annual (Privilege) Leave",
         "Every confirmed employee is entitled to 18 days of annual leave per calendar year, credited "
         "monthly at 1.5 days. Up to 10 unused annual leave days can be carried forward to the next year. "
         "Leave beyond the carry-forward limit lapses on 31 December. Annual leave requests of more than "
         "5 consecutive days must be approved by the reporting manager at least 14 days in advance."),
        ("2. Casual Leave",
         "Casual leave is meant for urgent personal matters. Employees receive 8 days of casual leave per "
         "year. Casual leave cannot be carried forward or encashed, and a maximum of 3 consecutive days "
         "can be taken at a time."),
        ("3. Sick Leave",
         "Employees are entitled to 10 days of paid sick leave per year. A medical certificate is "
         "mandatory if sick leave exceeds 2 consecutive days. Unused sick leave lapses at year end."),
        ("4. Maternity Leave",
         "Female employees who have completed at least 80 days of service in the 12 months preceding "
         "delivery are eligible for 26 weeks of paid maternity leave for the first two children and "
         "12 weeks for the third child onwards. Up to 8 weeks may be taken before the expected delivery date. "
         "Employees who adopt a child below three years are eligible for 12 weeks of leave."),
        ("5. Paternity Leave",
         "Male employees are entitled to 15 working days of paid paternity leave, which must be availed "
         "within 6 months of the child's birth."),
    ],
    "wfh_policy.pdf": [
        ("1. Hybrid Working",
         "Employees are expected to work from the office at least 3 days per week. Team leads decide the "
         "anchor days for their teams. Work from home beyond 2 days a week requires manager approval."),
        ("2. Remote Work Eligibility",
         "Employees must complete their probation period of 6 months before being eligible for any "
         "fully remote arrangement. Fully remote work is approved only by the department head and HR."),
        ("3. Equipment and Internet Allowance",
         "Employees working from home receive a monthly internet reimbursement of INR 1,000 on "
         "submission of the bill. Company laptops must be used for all official work."),
    ],
    "code_of_conduct.pdf": [
        ("1. Working Hours",
         "Standard working hours are 9:30 AM to 6:30 PM, Monday to Friday, with a one-hour lunch break. "
         "Core collaboration hours are 11:00 AM to 4:00 PM."),
        ("2. Dress Code",
         "The company follows a business-casual dress code. Formal attire is expected on client visit days."),
        ("3. Anti-Harassment",
         "The company has zero tolerance for harassment. Complaints can be raised with the Internal "
         "Complaints Committee at icc@example-company.com and are handled confidentially."),
    ],
}


def build(name, sections):
    styles = getSampleStyleSheet()
    story = [Paragraph(name.replace("_", " ").replace(".pdf", "").title(), styles["Title"]), Spacer(1, 12)]
    for i, (h, body) in enumerate(sections):
        if i and i % 2 == 0:
            story.append(PageBreak())  # forces multi-page PDFs so page citations are meaningful
        story += [Paragraph(h, styles["Heading2"]), Paragraph(body, styles["BodyText"]), Spacer(1, 14)]
    SimpleDocTemplate(str(OUT / name), pagesize=A4).build(story)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for n, s in DOCS.items():
        build(n, s)
        print("Created", OUT / n)
    sys.exit(0)
