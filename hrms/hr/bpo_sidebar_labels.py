"""Display labels for workspace sidebar items — BPO call center terminology."""

# Maps link_to (DocType, Page, Report, Dashboard) to user-facing label.
LINK_LABELS: dict[str, str] = {
	"Employee": "Agents",
	"Data Analytics": "Data Analytics",
	"in-out-today": "In / Out today",
	"organizational-chart": "Team Structure",
	"Employee Onboarding": "New Hire Onboarding",
	"Employee Separation": "Offboarding",
	"Employee Grievance": "Concerns & Escalations",
	"Employee Exits": "Agent Exits",
	"Employee Birthday": "Team Birthdays",
	"Employee Information": "Agent Directory",
	"Employee Analytics": "Headcount Analytics",
	"Employee Group": "Team Groups",
	"Employee Grade": "Agent Levels",
	"Employee Skill Map": "Skills & Certifications",
	"Grievance Type": "Concern Types",
	"Training Program": "Training Programs",
	"Training Event": "Training Sessions",
	"Training Feedback": "Training Evaluations",
	"Training Result": "Training Results",
	"Designation": "Roles",
	"Employee Checkin": "Clock In/Out",
	"Attendance Request": "Schedule Correction",
	"Shift Request": "Shift Swap",
	"Employee Attendance Tool": "Bulk Attendance",
	"Leave Application": "Time Off Request",
	"Leave Encashment": "PTO Cash-out",
	"Leave Control Panel": "Time Off Control",
	"Leave Policy Assignment": "PTO Policy Setup",
	"Leave Allocation": "PTO Allocation",
	"Overtime Type": "OT Types",
	"Overtime Slip": "OT Records",
	"Monthly Attendance Sheet": "Monthly Attendance",
	"Shift Attendance": "Shift Coverage",
	"Employee Leave Balance": "PTO Balance",
	"Employee Leave Balance Summary": "PTO Summary",
	"Employees working on a holiday": "Holiday Coverage",
	"Employee Hours Utilization Based On Timesheet": "Agent Utilization",
	"Job Opening": "Open Positions",
	"Job Applicant": "Candidates",
	"Interview": "Interviews",
	"Job Offer": "Offer Letters",
	"Appointment Letter": "Hire Letters",
	"Goal": "Performance Goals",
	"Appraisal Cycle": "Review Cycle",
	"Appraisal": "Performance Reviews",
	"Employee Performance Feedback": "QA Feedback",
	"Employee Promotion": "Promotions",
	"Job Requisition": "Headcount Request",
	"Staffing Plan": "Workforce Plan",
	"Employee Referral": "Refer a Candidate",
	"Recruitment Analytics": "Hiring Analytics",
	"Appraisal Overview": "Review Overview",
	"Payroll Entry": "Run Payroll",
	"Salary Structure Assignment": "Pay Rate Setup",
	"Salary Slip": "Pay Stubs",
	"Additional Salary": "Bonuses & Adjustments",
	"Salary Withholding": "Pay Holds",
	"Expense Claim": "Reimbursements",
	"Employee Advance": "Cash Advances",
	"Shift Assignment": "Shift Schedule",
	"Shift Type": "Shift Templates",
	"Shift Location": "Work Site",
	"Shift Schedule": "Shift Patterns",
	"Employee Incentive": "Incentives",
	"Salary Structure": "Pay Structure",
	"Salary Component": "Pay Components",
	"Salary Register": "Pay Register",
	"Interview Type": "Interview Types",
	"Job Opening Template": "Position Templates",
	"Appointment Letter Template": "Hire Letter Templates",
	"Job Offer Term Template": "Offer Term Templates",
	"Appraisal Template": "Review Templates",
	"Employee Feedback Criteria": "QA Scorecard Criteria",
	"Employee Lifecycle": "Agent Lifecycle",
	"Employee CTC Break-up": "Agent CTC Breakdown",
	"Provident Fund Deductions": "Provident Fund",
	"Employee Tax Exemption Sub Category": "Exemption Sub Category",
	"Employee Tax Adjustment": "Tax Period Adjustments",
	"Employee Tax Exemption Proof Submission": "Tax Exemption Proof",
	"Employee Tax Exemption Declaration": "Tax Exemption Declaration",
	"Employee Benefit Application": "Benefits Enrollment",
	"Employee Benefit Claim": "Benefits Claims",
}

# Section headers and items keyed by their current sidebar label.
LABEL_LABELS: dict[str, str] = {
	"Leave Admin": "Time Off Admin",
	"Overtime": "Extra Hours",
	"Planning": "Workforce Planning",
	"Leave Balance": "PTO Balance",
	"Leave Balance Summary": "PTO Summary",
	"Employees Working on a Holiday": "Holiday Coverage",
	"Employee Hours Utilization": "Agent Utilization",
	"Job Portal": "Careers Portal",
	"Organizational Chart": "Team Structure",
	"Exemption Declaration": "Tax Exemption Declaration",
	"Exemption Submission Proof": "Tax Exemption Proof",
	"Exemption Proof Submission": "Tax Exemption Proof",
	"Benefit Application": "Benefits Enrollment",
	"Benefit Claim": "Benefits Claims",
	"Tax & Benefits": "Tax & Benefits",
	"Accounting Entries": "Accounting",
	"Unpaid Expense Claim": "Unpaid Reimbursements",
	"Income Tax Computation": "Tax Computation",
	"Income Tax Deductions": "Tax Deductions",
	"Professional Tax Deductions": "Professional Tax",
	"Social Security Deductions": "Social Security",
	"Social Security Contribution Table": "SS Contribution Table",
	"Vehicle Expenses": "Fleet Expenses",
	"Purpose of Travel": "Travel Purpose",
	"Travel Request": "Travel Requests",
	"Vehicle Log": "Fleet Logs",
	"Expense Claim Type": "Reimbursement Types",
	"Accrued Earnings Report": "Accrued Earnings",
}


def apply_bpo_label(row: dict) -> dict:
	"""Return a copy of a sidebar row with BPO-friendly label when mapped."""
	data = dict(row)
	link_to = (data.get("link_to") or "").strip()
	label = (data.get("label") or "").strip()

	if link_to and link_to in LINK_LABELS:
		data["label"] = LINK_LABELS[link_to]
	elif label in LABEL_LABELS:
		data["label"] = LABEL_LABELS[label]

	return data


def apply_bpo_labels(rows: list[dict]) -> list[dict]:
	return [apply_bpo_label(row) for row in rows]


def get_sidebar_label_maps() -> dict[str, dict[str, str]]:
	"""Maps consumed by desk JS to rewrite sidebar labels at runtime."""
	by_label = dict(LABEL_LABELS)
	for link_to, new_label in LINK_LABELS.items():
		by_label.setdefault(link_to, new_label)
	return {"by_link": LINK_LABELS, "by_label": by_label}
