"""Party Statement Script Report (Customer or Supplier).

The report is a *statement of account* for one party: opening balance,
invoices, credit/debit notes, payments and unallocated (advance) payments.

Design notes
------------
* Every database read goes through ``frappe.get_all`` with parameterised
  filters; there is no string-formatted SQL anywhere in this file.
* Only submitted documents are used unless the user enables *Show Cancelled*.
  Cancelled rows are displayed for traceability but never add to the totals.
* The opening balance and the closing cross-check are read from ``GL Entry``
  (Receivable for customers, Payable for suppliers), so the statement can be
  reconciled against the ledger.
* Money is handled with ``Decimal`` inside this module; floats are produced
  only at the report boundary where Frappe expects numbers.
* The result is a flat list of rows. The ``section`` key tells the report
  print format how to group rows into separate tables; ``type_label`` is the
  translated label shown in the on-screen grid.
"""

from collections.abc import Iterable
from decimal import Decimal

import frappe
from erpnext.accounts.utils import get_fiscal_year
from frappe import _
from frappe.utils import add_months, flt, getdate, today

# Section identifiers shared with the print format.
SECTION_OPENING = "opening"
SECTION_INVOICE = "invoice"
SECTION_NOTE = "note"
SECTION_PAYMENT = "payment"
SECTION_ADVANCE = "advance"


def _type_label(section: str) -> str:
    """Translated label for a section, resolved per request (never at import)."""
    return {
        SECTION_OPENING: _("Opening"),
        SECTION_INVOICE: _("Invoice"),
        SECTION_NOTE: _("Credit/Debit Note"),
        SECTION_PAYMENT: _("Payment"),
        SECTION_ADVANCE: _("Advance"),
    }.get(section, section)


# ---------------------------------------------------------------------------
# Small numeric helpers
# ---------------------------------------------------------------------------
def _dec(value: object) -> Decimal:
    """Convert a value from the database to Decimal without binary floats."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(flt(value)))


def _q(value: Decimal) -> float:
    """Round to two decimals and return a float for the report boundary."""
    return float(value.quantize(Decimal("0.01")))


def _sum(rows: Iterable[dict], field: str) -> Decimal:
    return sum((_dec(row.get(field)) for row in rows), Decimal("0"))


def _money(value: Decimal, currency: str) -> str:
    return frappe.utils.fmt_money(value, currency=currency)


# ---------------------------------------------------------------------------
# Party / company / permission helpers
# ---------------------------------------------------------------------------
def _party_config(party_type: str) -> tuple[str, str, str]:
    """Return (invoice doctype, party field, GL account type)."""
    if party_type == "Customer":
        return "Sales Invoice", "customer", "Receivable"
    if party_type == "Supplier":
        return "Purchase Invoice", "supplier", "Payable"
    frappe.throw(_("Party Type must be Customer or Supplier"))


def _check_permissions(party_type: str, party: str, invoice_doctype: str) -> None:
    """Fail early with a readable message instead of returning partial data."""
    for doctype in (invoice_doctype, "Payment Entry", "GL Entry", party_type):
        if not frappe.has_permission(doctype, "read"):
            frappe.throw(
                _("You do not have permission to read {0}").format(_(doctype)),
                frappe.PermissionError,
            )
    if not frappe.has_permission(party_type, "read", party):
        frappe.throw(_("You do not have permission to view this party"), frappe.PermissionError)


def _address_lines(address_name: str | None) -> tuple[str, str]:
    """Return a printable address block and the address phone number."""
    if not address_name:
        return "", ""
    address = frappe.db.get_value(
        "Address",
        address_name,
        ["address_line1", "address_line2", "city", "state", "country", "pincode", "phone"],
        as_dict=True,
    )
    if not address:
        return "", ""
    city_line = " ".join(part for part in [address.city, address.state, address.pincode] if part)
    lines = [address.address_line1, address.address_line2, city_line, address.country]
    return "\n".join(line for line in lines if line), address.phone or ""


def _party_meta(party_type: str, party: str) -> dict[str, str]:
    name_field = "customer_name" if party_type == "Customer" else "supplier_name"
    address_field = (
        "customer_primary_address" if party_type == "Customer" else "supplier_primary_address"
    )
    doc = (
        frappe.db.get_value(
            party_type,
            party,
            ["name", "tax_id", "mobile_no", "email_id", name_field, address_field],
            as_dict=True,
        )
        or frappe._dict()
    )
    address, address_phone = _address_lines(doc.get(address_field))
    return {
        "party_name": doc.get(name_field) or party,
        "party_id": party,
        "party_tax_id": doc.get("tax_id") or "",
        "party_phone": doc.get("mobile_no") or address_phone or "",
        "party_email": doc.get("email_id") or "",
        "party_address": address,
    }


def _company_meta(company: str) -> dict[str, str]:
    doc = (
        frappe.db.get_value(
            "Company",
            company,
            ["company_name", "company_logo", "phone_no", "email", "tax_id", "default_currency"],
            as_dict=True,
        )
        or frappe._dict()
    )
    logo = doc.get("company_logo") or ""
    return {
        "company": doc.get("company_name") or company,
        "company_logo": frappe.utils.get_url(logo) if logo else "",
        "company_phone": doc.get("phone_no") or "",
        "company_email": doc.get("email") or "",
        "company_tax_id": doc.get("tax_id") or "",
        "company_currency": doc.get("default_currency") or "EGP",
    }


def _letter_head_header(letter_head: str | None, company: str) -> str:
    """Render the selected Letter Head header on the server.

    Report print formats are evaluated in the browser, where fetching a Letter
    Head is not possible. Rendering it here keeps the print format simple and
    lets the report use the same header as document prints.
    """
    if not letter_head:
        return ""
    try:
        from frappe.utils.print_format import render_letterhead_for_print

        rendered = render_letterhead_for_print(letter_head, {"company": company})
        return rendered.get("header") or ""
    except Exception:
        # A missing/renamed letter head must not break the report itself.
        frappe.log_error(
            title="Party Statement: letter head rendering failed",
            message=frappe.get_traceback(),
        )
        return ""


# ---------------------------------------------------------------------------
# Ledger helpers
# ---------------------------------------------------------------------------
def _party_accounts(company: str, account_type: str) -> list[str]:
    return frappe.get_all(
        "Account",
        filters={"company": company, "account_type": account_type, "is_group": 0},
        pluck="name",
        limit_page_length=0,
    )


def _gl_balance(
    company: str,
    party_type: str,
    party: str,
    accounts: list[str],
    *,
    before: str | None = None,
    through: str | None = None,
) -> Decimal:
    """Return the party balance normalised to "amount owed to the company".

    Customers: debit - credit (an advance payment is a credit, so negative).
    Suppliers: credit - debit (an advance payment is a debit, so negative).
    """
    if not accounts:
        return Decimal("0")
    filters: list[list] = [
        ["company", "=", company],
        ["party_type", "=", party_type],
        ["party", "=", party],
        ["account", "in", accounts],
        ["is_cancelled", "=", 0],
    ]
    if before:
        filters.append(["posting_date", "<", before])
    if through:
        filters.append(["posting_date", "<=", through])
    rows = frappe.get_all(
        "GL Entry",
        filters=filters,
        fields=["debit", "credit"],
        limit_page_length=0,
    )
    if party_type == "Customer":
        return _sum(rows, "debit") - _sum(rows, "credit")
    return _sum(rows, "credit") - _sum(rows, "debit")


def _invoice_paid(doctype: str, invoice_name: str) -> Decimal:
    """Sum submitted Payment Entry allocations linked to one invoice."""
    refs = frappe.get_all(
        "Payment Entry Reference",
        filters={"reference_doctype": doctype, "reference_name": invoice_name},
        fields=["parent", "allocated_amount"],
        limit_page_length=0,
    )
    if not refs:
        return Decimal("0")
    parents = sorted({row.parent for row in refs if row.parent})
    valid = set(
        frappe.get_all(
            "Payment Entry",
            filters={"name": ["in", parents], "docstatus": 1},
            pluck="name",
            limit_page_length=0,
        )
    )
    return sum((_dec(row.allocated_amount) for row in refs if row.parent in valid), Decimal("0"))


# ---------------------------------------------------------------------------
# Row builders
# ---------------------------------------------------------------------------
def _invoice_rows(
    doctype: str,
    party_field: str,
    party: str,
    company: str,
    from_date: str,
    to_date: str,
    show_cancelled: bool,
    is_return: int,
) -> list[dict]:
    """Invoice rows (is_return=0) or credit/debit note rows (is_return=1)."""
    filters = [
        ["company", "=", company],
        [party_field, "=", party],
        ["posting_date", "between", [from_date, to_date]],
        ["is_return", "=", is_return],
        ["docstatus", "in", ([1, 2] if show_cancelled else [1])],
    ]
    invoices = frappe.get_all(
        doctype,
        filters=filters,
        fields=[
            "name",
            "posting_date",
            "due_date",
            "grand_total",
            "base_grand_total",
            "paid_amount",
            "base_paid_amount",
            "outstanding_amount",
            "conversion_rate",
            "status",
            "currency",
            "docstatus",
        ],
        order_by="posting_date asc, name asc",
        limit_page_length=0,
    )

    rows: list[dict] = []
    for invoice in invoices:
        allocated = _invoice_paid(doctype, invoice.name)
        paid_amount = _dec(invoice.paid_amount)
        paid = paid_amount if paid_amount else allocated
        outstanding = _dec(invoice.outstanding_amount)
        conversion = _dec(invoice.conversion_rate) or Decimal("1")
        base_paid = _dec(invoice.base_paid_amount) or (paid * conversion)

        # "Paid on the invoice itself" is the part of paid_amount that is not
        # covered by a Payment Entry allocation. POS invoices settle at the
        # counter and carry that amount on the invoice, with no Payment Entry.
        # Returns carry a negative paid_amount (the refund).
        self_paid = paid - allocated

        # Cancelled documents are shown but must not contribute to any total.
        if invoice.docstatus == 2:
            paid = Decimal("0")
            outstanding = Decimal("0")
            base_paid = Decimal("0")
            self_paid = Decimal("0")

        rows.append(
            {
                "section": SECTION_NOTE if is_return else SECTION_INVOICE,
                "type_label": _type_label(SECTION_NOTE if is_return else SECTION_INVOICE),
                "document": invoice.name,
                "posting_date": invoice.posting_date,
                "due_date": invoice.due_date,
                "method": "",
                "reference": "",
                "applied_to": "",
                "total": _q(_dec(invoice.grand_total)),
                "paid": _q(paid),
                "outstanding": _q(outstanding),
                "status": invoice.status,
                "currency": invoice.currency,
                "docstatus": invoice.docstatus,
                "base_total": _q(_dec(invoice.base_grand_total)),
                "base_paid": _q(base_paid),
                "base_outstanding": _q(outstanding * conversion),
                "base_self_paid": _q(self_paid * conversion),
                "is_return": bool(is_return),
            }
        )
    return rows


def _payment_rows(
    party_type: str,
    party: str,
    company: str,
    from_date: str,
    to_date: str,
    show_cancelled: bool,
) -> tuple[list[dict], list[dict]]:
    """Return (payments, advances) for the period.

    ``advances`` contains the unallocated part of each payment. Those amounts
    are already inside the payment's total, so the summary only uses the
    payment total; the advance rows are shown for information.
    """
    primary_type = "Receive" if party_type == "Customer" else "Pay"
    filters = [
        ["company", "=", company],
        ["party_type", "=", party_type],
        ["party", "=", party],
        ["posting_date", "between", [from_date, to_date]],
        ["docstatus", "in", ([1, 2] if show_cancelled else [1])],
    ]
    entries = frappe.get_all(
        "Payment Entry",
        filters=filters,
        fields=[
            "name",
            "posting_date",
            "mode_of_payment",
            "payment_type",
            "reference_no",
            "reference_date",
            "paid_amount",
            "base_paid_amount",
            "unallocated_amount",
            "paid_from_account_currency",
            "paid_to_account_currency",
            "status",
            "docstatus",
        ],
        order_by="posting_date asc, name asc",
        limit_page_length=0,
    )

    payments: list[dict] = []
    advances: list[dict] = []
    for entry in entries:
        refs = frappe.get_all(
            "Payment Entry Reference",
            filters={"parent": entry.name, "parenttype": "Payment Entry"},
            fields=["reference_name", "reference_doctype", "allocated_amount"],
            limit_page_length=0,
        )
        applied = ", ".join(row.reference_name for row in refs if row.reference_name)

        # Refunds move the other way: a customer refund is a "Pay" entry and a
        # supplier refund is a "Receive" entry. Signed amounts keep the
        # statement and the ledger in agreement.
        opposite = entry.payment_type != primary_type
        sign = Decimal("-1") if opposite else Decimal("1")

        # The party account is paid_from for a customer receipt and a supplier
        # refund, and paid_to for a supplier payment and a customer refund.
        currency = (
            entry.paid_from_account_currency
            if (party_type == "Customer") != opposite
            else entry.paid_to_account_currency
        ) or "EGP"

        paid = _dec(entry.paid_amount) * sign
        base_paid = _dec(entry.base_paid_amount) * sign
        base_rate = (base_paid / paid) if paid else Decimal("1")

        row = {
            "document": entry.name,
            "posting_date": entry.posting_date,
            "method": entry.mode_of_payment or "",
            "reference": " ".join(
                part for part in [entry.reference_no, str(entry.reference_date or "")] if part
            ),
            "reference_no": entry.reference_no or "",
            "reference_date": str(entry.reference_date or ""),
            "applied_to": applied or _("—"),
            "total": _q(paid),
            "paid": 0.0,
            "outstanding": 0.0,
            "status": entry.status,
            "currency": currency,
            "docstatus": entry.docstatus,
            "base_total": _q(base_paid),
            "base_paid": _q(base_paid),
            "base_outstanding": 0.0,
        }
        if entry.docstatus == 2:
            row.update(total=0.0, base_total=0.0, base_paid=0.0)

        if not applied and _dec(entry.unallocated_amount) > 0:
            row["applied_to"] = _("Advance / Unallocated")

        payments.append(
            {
                **row,
                "section": SECTION_PAYMENT,
                "type_label": _("Refund") if opposite else _type_label(SECTION_PAYMENT),
            }
        )

        unallocated = _dec(entry.unallocated_amount) * sign
        if unallocated > 0 and entry.docstatus == 1:
            advances.append(
                {
                    **row,
                    "section": SECTION_ADVANCE,
                    "type_label": _type_label(SECTION_ADVANCE),
                    "applied_to": _("Advance / Unallocated"),
                    "total": _q(unallocated),
                    "base_total": _q(unallocated * base_rate),
                }
            )
    return payments, advances


# ---------------------------------------------------------------------------
# Report columns and entry points
# ---------------------------------------------------------------------------
def _columns() -> list[dict]:
    return [
        {"fieldname": "type_label", "label": _("Type"), "fieldtype": "Data", "width": 110},
        {"fieldname": "document", "label": _("Document"), "fieldtype": "Data", "width": 170},
        {"fieldname": "posting_date", "label": _("Date"), "fieldtype": "Date", "width": 95},
        {"fieldname": "due_date", "label": _("Due Date"), "fieldtype": "Date", "width": 95},
        {"fieldname": "method", "label": _("Method"), "fieldtype": "Data", "width": 105},
        {"fieldname": "reference", "label": _("Reference"), "fieldtype": "Data", "width": 130},
        {"fieldname": "applied_to", "label": _("Applied To"), "fieldtype": "Data", "width": 180},
        {
            "fieldname": "total",
            "label": _("Total"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120,
        },
        {
            "fieldname": "paid",
            "label": _("Paid"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120,
        },
        {
            "fieldname": "outstanding",
            "label": _("Outstanding"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120,
        },
        {"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
        {
            "fieldname": "currency",
            "label": _("Currency"),
            "fieldtype": "Link",
            "options": "Currency",
            "width": 80,
        },
    ]


@frappe.whitelist()
def get_fiscal_year_start(company: str | None = None) -> str:
    """Used by party_statement.js to default From Date to the fiscal year."""
    fiscal_year = get_fiscal_year(today(), company=company, raise_on_missing=False)
    return str(fiscal_year[1]) if fiscal_year else str(add_months(today(), -12))


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.get("company") or not filters.get("party_type") or not filters.get("party"):
        frappe.throw(_("Company, Party Type and Party are required"), frappe.MandatoryError)

    party_type = filters.party_type
    party = filters.party
    company = filters.company
    invoice_doctype, party_field, account_type = _party_config(party_type)
    _check_permissions(party_type, party, invoice_doctype)

    # --- Period ------------------------------------------------------------
    from_date = (
        getdate(filters.from_date)
        if filters.get("from_date")
        else getdate(get_fiscal_year_start(company))
    )
    to_date = getdate(filters.to_date) if filters.get("to_date") else getdate(today())
    if from_date > to_date:
        frappe.throw(_("From Date cannot be after To Date"))
    from_date, to_date = str(from_date), str(to_date)
    show_cancelled = bool(filters.get("show_cancelled"))

    # --- Header data -------------------------------------------------------
    company_meta = _company_meta(company)
    party_meta = _party_meta(party_type, party)
    company_currency = company_meta["company_currency"]

    # --- Balances ----------------------------------------------------------
    accounts = _party_accounts(company, account_type)
    opening = _gl_balance(company, party_type, party, accounts, before=from_date)
    closing_gl = _gl_balance(company, party_type, party, accounts, through=to_date)

    # --- Documents ---------------------------------------------------------
    invoice_rows = _invoice_rows(
        invoice_doctype, party_field, party, company, from_date, to_date, show_cancelled, 0
    )
    note_rows = _invoice_rows(
        invoice_doctype, party_field, party, company, from_date, to_date, show_cancelled, 1
    )
    payment_rows, advance_rows = _payment_rows(
        party_type, party, company, from_date, to_date, show_cancelled
    )

    # --- Total row ---------------------------------------------------------
    invoiced = _sum([row for row in invoice_rows if row["docstatus"] == 1], "base_total")
    notes = _sum([row for row in note_rows if row["docstatus"] == 1], "base_total")
    payment_total = _sum([row for row in payment_rows if row["docstatus"] == 1], "base_paid")
    counter_paid = _sum(
        [row for row in invoice_rows + note_rows if row["docstatus"] == 1], "base_self_paid"
    )
    paid = payment_total + counter_paid
    advances = _sum(advance_rows, "base_total")
    closing = opening + invoiced + notes - paid
    difference = closing - closing_gl
    mismatch = abs(difference) > Decimal("0.01")

    # --- Multi-currency note ----------------------------------------------
    foreign_currencies = sorted(
        {
            row["currency"]
            for row in invoice_rows + note_rows + payment_rows
            if row.get("currency") and row["currency"] != company_currency
        }
    )
    currency_note = ""
    if foreign_currencies:
        currency_note = _(
            "Some documents are in {0}. Row amounts use the document currency; "
            "totals and the GL comparison use {1}."
        ).format(", ".join(foreign_currencies), company_currency)

    meta = {
        **company_meta,
        **party_meta,
        "from_date": from_date,
        "to_date": to_date,
        "print_date": frappe.utils.format_date(today()),
        "party_type": party_type,
        "party": party,
        "opening_balance": _q(opening),
        "total_invoiced": _q(invoiced),
        "total_paid": _q(paid),
        "payment_total": _q(payment_total),
        "counter_paid": _q(counter_paid),
        "notes_total": _q(notes),
        "advances_total": _q(advances),
        "closing_balance": _q(closing),
        "gl_closing_balance": _q(closing_gl),
        "currency_note": currency_note,
        "mismatch": bool(mismatch),
        "letter_head_header": _letter_head_header(filters.get("letter_head"), company),
    }

    data: list[dict] = []
    if opening or invoice_rows or note_rows or payment_rows or advance_rows:
        data.append(
            {
                **meta,
                "section": SECTION_OPENING,
                "type_label": _type_label(SECTION_OPENING),
                "document": _("Opening Balance"),
                "posting_date": from_date,
                "due_date": "",
                "method": "",
                "reference": "",
                "applied_to": "",
                "total": _q(opening),
                "paid": 0.0,
                "outstanding": _q(opening),
                "status": _("Opening"),
                "currency": company_currency,
                "docstatus": 1,
                "base_total": _q(opening),
                "base_paid": 0.0,
                "base_outstanding": _q(opening),
            }
        )
    data.extend({**meta, **row} for row in invoice_rows + note_rows + payment_rows + advance_rows)

    # --- Empty state -------------------------------------------------------
    if not invoice_rows and not note_rows and not payment_rows and not advance_rows and not opening:
        return _columns(), [], _("No transactions found for this party in the selected period.")

    report_summary = [
        {
            "label": _("Opening Balance"),
            "value": _q(opening),
            "datatype": "Currency",
            "currency": company_currency,
        },
        {
            "label": _("Total Invoiced"),
            "value": _q(invoiced),
            "datatype": "Currency",
            "currency": company_currency,
        },
        {
            "label": _("Total Paid"),
            "value": _q(paid),
            "datatype": "Currency",
            "currency": company_currency,
        },
        {
            "label": _("Remaining Balance"),
            "value": _q(closing),
            "datatype": "Currency",
            "currency": company_currency,
        },
    ]

    # --- On-screen messages (never printed) --------------------------------
    messages: list[str] = []
    if mismatch:
        messages.append(
            _(
                "<div class='text-danger small'>Warning: the statement closing balance "
                "({0}) differs from the GL balance ({1}) by {2}. Check journals, "
                "write-offs, tax entries or unallocated payments.</div>"
            ).format(
                _money(closing, company_currency),
                _money(closing_gl, company_currency),
                _money(difference, company_currency),
            )
        )
    if currency_note:
        messages.append(f"<div class='text-muted small'>{currency_note}</div>")

    return _columns(), data, "".join(messages), None, report_summary
