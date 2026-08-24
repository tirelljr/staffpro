import click

from hrms.setup import after_install as setup


def after_install():
	try:
		print("Setting up Staff Pro BPO...")
		setup()
		from hrms.branding import apply_branding
		from hrms.hr.bpo_bank_account import apply_bank_account_layout
		from hrms.hr.bpo_employee_labels import apply_bpo_employee_labels
		from hrms.patches.v16_0.disable_app_onboarding import execute as disable_app_onboarding
		from hrms.patches.v16_0.hide_cost_center import hide_cost_center_fields
		from hrms.payroll.bpo_client_accounts import setup_usd_client_billing
		from hrms.payroll.bpo_customer import apply_bpo_customer_layout
		from hrms.payroll.bpo_sales_invoice import apply_bpo_sales_invoice_layout

		apply_branding()
		apply_bpo_employee_labels()
		apply_bank_account_layout()
		apply_bpo_customer_layout()
		apply_bpo_sales_invoice_layout()
		setup_usd_client_billing()
		hide_cost_center_fields()
		disable_app_onboarding()

		click.secho("Thank you for installing Staff Pro BPO!", fg="green")

	except Exception as e:
		BUG_REPORT_URL = "https://github.com/frappe/hrms/issues/new"
		click.secho(
			"Installation for Staff Pro BPO failed due to an error."
			" Please try re-installing the app or"
			f" report the issue on {BUG_REPORT_URL} if not resolved.",
			fg="bright_red",
		)
		raise e
