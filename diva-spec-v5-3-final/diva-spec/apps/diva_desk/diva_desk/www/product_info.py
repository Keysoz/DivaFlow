"""Staff-only Product Info page (DEC-95)."""

import frappe

no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/product_info"
        raise frappe.Redirect
    context.no_cache = 1
    return context
