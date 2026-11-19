app_name = "diva_desk"
app_title = "Diva Desk"
app_publisher = "Diva"
app_description = "Diva Desk keyboard, focus and workflow layer"
app_email = "ops@diva.local"
app_license = "mit"

# Client-only app: the Desk loads these files on every page. Server permissions,
# money and stock rules stay in diva_guard (DEC-85).
# DEC-107: the Supplier/Customer quick entries drop email, postal code and
# state, and pre-fill Cairo/Egypt.
app_include_js = [
    "/assets/diva_desk/js/diva_desk.js",
    "/assets/diva_desk/js/party_quick_entry.js",
]
