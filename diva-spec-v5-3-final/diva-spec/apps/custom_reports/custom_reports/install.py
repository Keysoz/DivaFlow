"""Install/upgrade hooks for the Custom Reports app.

The only piece of configuration this app owns is the report print format.
Keeping it in Python (instead of a fixture) means `bench migrate` on any site
creates the format if it is missing and refreshes it when the template changes,
without touching document print formats.
"""

from pathlib import Path

import frappe

PRINT_FORMAT_NAME = "Party Statement Print"
REPORT_NAME = "Party Statement"
PRINT_FORMAT_FOLDER = "print_format"


def _read_asset(filename: str) -> str:
    """Read a template file shipped with the app."""
    path = Path(frappe.get_app_path("custom_reports", PRINT_FORMAT_FOLDER, filename))
    return path.read_text(encoding="utf-8")


def sync_party_statement_print_format() -> None:
    """Create or update the report print format (idempotent)."""
    if not frappe.db.exists("Report", REPORT_NAME):
        # The report itself is synced by the framework from the .json file.
        # On a fresh install it can arrive after this hook; after_migrate runs
        # again, so silently skipping here is safe.
        return

    html = _read_asset("party_statement_print.html")
    css = ""

    values = {
        "print_format_for": "Report",
        "report": REPORT_NAME,
        "doc_type": None,
        "module": "Custom Reports",
        "standard": "No",
        "custom_format": 1,
        "print_format_type": "JS",
        "disabled": 0,
        "html": html,
        "css": css,
    }

    if frappe.db.exists("Print Format", PRINT_FORMAT_NAME):
        current = frappe.db.get_value(
            "Print Format",
            PRINT_FORMAT_NAME,
            ["print_format_for", "report", "custom_format", "print_format_type", "html", "css"],
            as_dict=True,
        )
        if current and all(current.get(key) == values[key] for key in current):
            return

        doc = frappe.get_doc("Print Format", PRINT_FORMAT_NAME)
        doc.update(values)
    else:
        doc = frappe.new_doc("Print Format")
        doc.update({"name": PRINT_FORMAT_NAME, **values})

    doc.flags.ignore_permissions = True
    doc.save(ignore_permissions=True)


def after_install() -> None:
    sync_party_statement_print_format()


def after_migrate() -> None:
    sync_party_statement_print_format()
