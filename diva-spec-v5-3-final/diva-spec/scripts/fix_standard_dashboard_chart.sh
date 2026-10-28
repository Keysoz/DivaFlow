#!/usr/bin/env bash
# Work around ERPNext 16's "Item-wise Annual Sales" dashboard chart, which calls
# the Item-wise Sales History report without the required company filter and
# crashes with "cannot unpack non-iterable NoneType object".
#
# ERPNext marks the chart as standard, so the UI/API refuse edits. This script
# sets the chart's filters_json directly (data only) and is safe to re-run after
# every migrate/upgrade. Dev/staging first; production via the owner's deploy.
set -euo pipefail

CONTAINER="${CONTAINER:-frappe_docker-backend-1}"
SITE="${SITE:-frontend}"
COMPANY="${COMPANY:-}"

docker exec -i "${CONTAINER}" "${BENCH:-/home/frappe/frappe-bench}/env/bin/python" - "${SITE}" "${COMPANY}" <<'PY'
import json
import os
import sys

import frappe

os.chdir("/home/frappe/frappe-bench/sites")
site, company = sys.argv[1], sys.argv[2]
frappe.init(site=site, sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
company = company or frappe.db.get_value("Global Defaults", "Global Defaults", "default_company") or "Diva Dev"
name = "Item-wise Annual Sales"
current = frappe.db.get_value("Dashboard Chart", name, "filters_json") or "{}"
filters = json.loads(current)
wanted = dict(filters)
wanted["company"] = company
wanted.setdefault("from_date", "2020-06-22")
if wanted != filters:
    frappe.db.set_value("Dashboard Chart", name, "filters_json", json.dumps(wanted), update_modified=False)
    frappe.db.commit()
    print("updated", name, wanted)
else:
    print("already ok", name, filters)
PY
