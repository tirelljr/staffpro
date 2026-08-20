import click

from hrms.setup import after_install as setup


def after_install():
	try:
		print("Setting up Staff Pro BPO...")
		setup()
		from hrms.branding import apply_branding
		from hrms.hr.bpo_employee_labels import apply_bpo_employee_labels
		from hrms.patches.v16_0.disable_app_onboarding import execute as disable_app_onboarding

		apply_branding()
		apply_bpo_employee_labels()
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
