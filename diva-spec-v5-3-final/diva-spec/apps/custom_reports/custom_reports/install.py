"""Install/upgrade hooks for the Custom Reports app.

Two kinds of report print format live here:

* "Party Statement Print": the bespoke bilingual statement (ENH-E-01).
* One format named exactly like its report (for example "Trial Balance"), using
  the shared Diva template. Frappe falls back to a print format whose name
  equals the report name, so these formats are the default when the owner
  prints a report without choosing one (DEC-89).

Keeping them in Python (instead of a fixture) means `bench migrate` on any site
creates the formats if they are missing and refreshes them when the template
changes, without touching document print formats.
"""

from pathlib import Path

import frappe

PRINT_FORMAT_NAME = "Party Statement Print"
REPORT_NAME = "Party Statement"
PRINT_FORMAT_FOLDER = "print_format"

# Report name -> template file. The format is named after the report so Frappe
# picks it as that report's default print template.
REPORT_PRINT_FORMATS = {
    "Party Statement": "party_statement_print.html",
    "Accounts Receivable": "diva_report.html",
    "Accounts Payable": "diva_report.html",
    "General Ledger": "diva_report.html",
    "Trial Balance": "diva_report.html",
    "Profit and Loss Statement": "diva_report.html",
    "Balance Sheet": "diva_report.html",
    "Stock Balance": "diva_report.html",
    "Stock Ledger": "diva_report.html",
}


def _read_asset(filename: str) -> str:
    """Read a template file shipped with the app."""
    path = Path(frappe.get_app_path("custom_reports", PRINT_FORMAT_FOLDER, filename))
    return path.read_text(encoding="utf-8")


def _upsert_print_format(name: str, values: dict) -> None:
    """Create the print format, or update it only when something changed."""
    if frappe.db.exists("Print Format", name):
        current = frappe.db.get_value(
            "Print Format",
            name,
            [
                "module",
                "print_format_for",
                "report",
                "custom_format",
                "print_format_type",
                "disabled",
                "html",
                "css",
            ],
            as_dict=True,
        )
        if not current:
            return
        if current.get("module") != values["module"]:
            # Never replace a format this app does not own (DEC-89).
            frappe.log_error(
                title="Diva: report print format not overwritten",
                message=(
                    f"Print Format {name!r} belongs to module {current.get('module')!r}; "
                    "the Diva template was not applied."
                ),
            )
            return
        if all(current.get(key) == values[key] for key in current):
            return
        doc = frappe.get_doc("Print Format", name)
        doc.update(values)
    else:
        doc = frappe.new_doc("Print Format")
        doc.update({"name": name, **values})

    doc.flags.ignore_permissions = True
    doc.save(ignore_permissions=True)


def _format_values(report_name: str | None, html: str) -> dict:
    return {
        "print_format_for": "Report",
        "report": report_name,
        "doc_type": None,
        "module": "Custom Reports",
        "standard": "No",
        "custom_format": 1,
        "print_format_type": "JS",
        "disabled": 0,
        "html": html,
        "css": "",
    }


def sync_party_statement_print_format() -> None:
    """Create or update the bespoke Party Statement print format (idempotent)."""
    if not frappe.db.exists("Report", REPORT_NAME):
        # The report itself is synced by the framework from the .json file.
        # On a fresh install it can arrive after this hook; after_migrate runs
        # again, so silently skipping here is safe.
        return

    html = _read_asset("party_statement_print.html")
    _upsert_print_format(PRINT_FORMAT_NAME, _format_values(REPORT_NAME, html))


def sync_report_print_formats() -> None:
    """Create the default Diva print template for the main reports (DEC-89)."""
    templates: dict[str, str] = {}
    for report_name, filename in REPORT_PRINT_FORMATS.items():
        if not frappe.db.exists("Report", report_name):
            continue
        if filename not in templates:
            templates[filename] = _read_asset(filename)
        _upsert_print_format(report_name, _format_values(report_name, templates[filename]))


def after_install() -> None:
    sync_party_statement_print_format()
    sync_report_print_formats()


def after_migrate() -> None:
    sync_party_statement_print_format()
    sync_report_print_formats()
