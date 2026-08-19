"""Lucide icon assignments for Staff Pro BPO workspace sidebar items."""

from __future__ import annotations

import re

# Section headers (collapsible groups)
SECTION_ICON_BY_LABEL = {
	"access": "users",
	"accounting": "coins",
	"admin": "settings",
	"audit logs": "scroll-text",
	"customization": "sliders",
	"integrations": "cable",
	"leave admin": "sliders-horizontal",
	"overtime": "calendar-clock",
	"payables": "arrow-up-right",
	"payments": "credit-card",
	"planning": "align-start-horizontal",
	"receivables": "arrow-down-left",
	"reports": "notepad-text",
	"setup": "database",
	"tax & benefits": "badge-alert",
	"social security": "shield",
	"other statutory": "landmark",
	"travel": "plane",
}

# Submenu / child links keyed by lower-case label
ICON_BY_LABEL = {
	"access log": "eye",
	"accounts settings": "settings",
	"accounts payable": "arrow-up-right",
	"activity log": "activity",
	"audit trail": "file-search",
	"accounts receivable": "arrow-down-left",
	"accrued earnings report": "bar-chart-2",
	"activity type": "tag",
	"additional salary": "piggy-bank",
	"appointment letter": "file-text",
	"appointment letter template": "file-text",
	"appraisal": "arrow-up",
	"appraisal cycle": "orbit",
	"appraisal overview": "bar-chart-2",
	"appraisal template": "file-text",
	"bank reconciliation tool": "landmark",
	"benefit application": "heart",
	"benefit claim": "heart",
	"branch": "git-branch",
	"chart of accounts": "book",
	"company": "building",
	"connected app": "cable",
	"credit note": "file-text",
	"customer": "user",
	"customize form": "sliders",
	"data analytics": "bar-chart-2",
	"debit note": "file-text",
	"department": "network",
	"designation": "badge",
	"driver": "user",
	"email account": "mail",
	"error log": "triangle-alert",
	"employee advance": "upload",
	"employee analytics": "bar-chart-2",
	"employee birthday": "cake",
	"employee exits": "log-out",
	"employee feedback criteria": "list",
	"employee grade": "layers",
	"employee group": "users",
	"employee hours utilization": "timer",
	"employee information": "file-text",
	"employee performance feedback": "trending-up",
	"employee promotion": "graduation-cap",
	"employee referral": "user-plus",
	"employee skill map": "map",
	"employees working on a holiday": "sun",
	"exemption category": "tag",
	"exemption declaration": "file-text",
	"exemption proof submission": "upload",
	"expense claim type": "tag",
	"general ledger": "book-open",
	"google settings": "globe",
	"integration request": "radio",
	"ldap settings": "network",
	"oauth client": "lock",
	"permission log": "shield",
	"grievance type": "flag",
	"holiday list": "calendar",
	"holiday list assignment": "calendar-plus",
	"income tax computation": "calculator",
	"income tax deductions": "minus-circle",
	"income tax slab": "layers",
	"in / out today": "log-in",
	"interview type": "video",
	"job applicant": "circle-user-round",
	"job offer term template": "file-text",
	"job opening template": "file-text",
	"job portal": "globe",
	"job requisition": "file-plus",
	"journal entry": "book-open",
	"kra": "target",
	"leave allocation": "pie-chart",
	"leave block list": "slash",
	"leave balance": "calendar-check",
	"leave balance summary": "calendar-range",
	"leave control panel": "sliders",
	"leave period": "clock",
	"leave policy": "file-check",
	"leave policy assignment": "user-check",
	"leave type": "tag",
	"monthly attendance sheet": "calendar",
	"overtime slip": "file-text",
	"overtime type": "timer",
	"payment entry": "credit-card",
	"print format": "printer",
	"professional tax deductions": "minus-circle",
	"profit and loss statement": "bar-chart-2",
	"project profitability": "trending-up",
	"purchase invoice": "file-text",
	"purpose of travel": "map-pin",
	"recruitment analytics": "bar-chart-2",
	"role": "shield",
	"role permission manager": "key",
	"salary component": "coins",
	"salary register": "book",
	"salary structure": "layers",
	"salary withholding": "banknote-x",
	"sales invoice": "file-text",
	"supplier": "building",
	"social security": "shield",
	"social security deductions": "shield",
	"ss contribution table": "shield",
	"social security contribution table": "shield",
	"shift attendance": "clock",
	"shift location": "map-pin",
	"shift schedule": "calendar-range",
	"shift type": "layers",
	"social login key": "key",
	"staffing plan": "users",
	"system settings": "settings",
	"timesheet": "clock",
	"training event": "calendar",
	"training feedback": "message-square",
	"training program": "graduation-cap",
	"training result": "check-circle",
	"travel request": "plane",
	"trial balance": "scale",
	"unpaid expense claim": "alert-circle",
	"user": "user",
	"vehicle": "car",
	"vehicle expenses": "car",
	"vehicle log": "truck",
	"website settings": "globe",
	"webhook": "webhook",
}

KEYWORD_ICON_RULES: list[tuple[re.Pattern[str], str]] = [
	(re.compile(r"account|ledger|journal", re.I), "book-open"),
	(re.compile(r"payment|bank|wallet|salary|payroll|pay", re.I), "credit-card"),
	(re.compile(r"report|analytic|overview", re.I), "bar-chart-2"),
	(re.compile(r"user|employee|driver", re.I), "user"),
	(re.compile(r"setting|setup", re.I), "settings"),
	(re.compile(r"template|letter|policy", re.I), "file-text"),
	(re.compile(r"calendar|holiday|leave|shift|roster", re.I), "calendar"),
	(re.compile(r"travel|plane", re.I), "plane"),
	(re.compile(r"vehicle|car", re.I), "car"),
	(re.compile(r"tax|benefit|exemption", re.I), "tag"),
	(re.compile(r"goal|appraisal|kra", re.I), "target"),
	(re.compile(r"job|interview|recruit", re.I), "briefcase"),
	(re.compile(r"department|branch|company", re.I), "building"),
	(re.compile(r"type|category|component", re.I), "tag"),
	(re.compile(r"dashboard", re.I), "layout-dashboard"),
	(re.compile(r"attendance|checkin|time", re.I), "clock"),
	(re.compile(r"expense|claim|advance", re.I), "receipt"),
]


def icon_for_label(label: str, *, is_section: bool = False) -> str:
	key = (label or "").strip().lower()
	if not key:
		return "file-text"
	if is_section and key in SECTION_ICON_BY_LABEL:
		return SECTION_ICON_BY_LABEL[key]
	if key in ICON_BY_LABEL:
		return ICON_BY_LABEL[key]
	for pattern, icon in KEYWORD_ICON_RULES:
		if pattern.search(label):
			return icon
	if is_section:
		return "folder"
	return "file-text"


def apply_icons_to_rows(rows: list[dict]) -> list[dict]:
	updated: list[dict] = []
	for row in rows:
		row = dict(row)
		label = row.get("label") or ""
		row_type = row.get("type")
		if row_type == "Section Break":
			if not row.get("icon"):
				row["icon"] = icon_for_label(label, is_section=True)
		elif row.get("child") or row_type in ("Link", "Route"):
			if not row.get("icon"):
				row["icon"] = icon_for_label(label)
		updated.append(row)
	return updated
