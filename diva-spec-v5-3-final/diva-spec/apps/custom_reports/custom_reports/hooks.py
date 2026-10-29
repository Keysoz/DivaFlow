app_name = "custom_reports"
app_title = "Diva Reports"
app_publisher = "Diva"
app_description = "Diva custom Frappe reports"
app_email = "ops@diva.local"
app_license = "mit"

after_install = "custom_reports.install.after_install"
after_migrate = "custom_reports.install.after_migrate"

# Show the app on the Desk "Apps" screen and open the store dashboard.
add_to_apps_screen = [
    {
        "name": app_name,
        "logo": (
            "data:image/svg+xml;base64,"
            "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI2NCIgaGVpZ2h0"
            "PSI2NCIgdmlld0JveD0iMCAwIDY0IDY0IiByb2xlPSJpbWciIGFyaWEtbGFiZWw9IkRpdmEgUmVw"
            "b3J0cyI+CiAgPHJlY3Qgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0IiByeD0iMTQiIGZpbGw9IiMyZjll"
            "NDQiLz4KICA8cmVjdCB4PSIxNSIgeT0iMzUiIHdpZHRoPSI3IiBoZWlnaHQ9IjE0IiByeD0iMiIg"
            "ZmlsbD0iI2ZmZmZmZiIvPgogIDxyZWN0IHg9IjI4LjUiIHk9IjI3IiB3aWR0aD0iNyIgaGVpZ2h0"
            "PSIyMiIgcng9IjIiIGZpbGw9IiNmZmZmZmYiLz4KICA8cmVjdCB4PSI0MiIgeT0iMTgiIHdpZHRo"
            "PSI3IiBoZWlnaHQ9IjMxIiByeD0iMiIgZmlsbD0iI2ZmZmZmZiIvPgo8L3N2Zz4K"
        ),
        "title": app_title,
        "route": "/app/diva-store",
        "has_permission": "frappe.permissions.check_app_permission",
        "sequence_id": 2,
    }
]
