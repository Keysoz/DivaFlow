#!/usr/bin/env bash
# Re-register the Diva/POS apps in sites/apps.txt and clear the caches (DEC-103).
#
# The stock frappe_docker configurator rebuilds sites/apps.txt from its own
# image on EVERY `docker compose -f pwd.yml up -d`. Its image only contains
# frappe + erpnext, so every stack restart silently unregisters pos_next,
# diva_guard, diva_desk and custom_reports. Symptoms: the Diva Guard form
# answers 404 (`الوحدة Diva Guard غير موجودة`), /product_info fails with
# TemplateNotFound, workspace charts fail (NaN paths), and the website-search
# background job dies with ModuleNotFoundError.
#
# This script is idempotent and safe to run after every `compose up`.
set -euo pipefail

CONTAINER="${CONTAINER:-frappe_docker-backend-1}"
SITE="${SITE:-frontend}"
BENCH="${BENCH:-/home/frappe/frappe-bench}"
# Order does not matter to Frappe; these are the apps the install scripts add.
APPS="${APPS:-pos_next diva_guard diva_desk custom_reports}"

registered() {
  docker exec "${CONTAINER}" bash -lc "grep -qx '${1}' '${BENCH}/sites/apps.txt'"
}

missing=""
for app in ${APPS}; do
  if ! registered "${app}"; then
    missing="${missing} ${app}"
  fi
done

if [[ -z "${missing}" ]]; then
  echo "apps.txt is complete (${APPS})"
  exit 0
fi

echo "==> re-registering missing apps:${missing}"
for app in ${missing}; do
  docker exec "${CONTAINER}" bash -lc "echo '${app}' >> '${BENCH}/sites/apps.txt'"
done
docker exec "${CONTAINER}" bash -lc "grep -q '^frappe$' '${BENCH}/sites/apps.txt' && grep -q '^erpnext$' '${BENCH}/sites/apps.txt'"

# The app registry is cached (site cache and the worker processes), so restart.
echo "==> clearing cache and restarting ${CONTAINER}"
docker exec "${CONTAINER}" bash -lc "cd '${BENCH}' && bench --site '${SITE}' clear-cache" >/dev/null
docker restart "${CONTAINER}" >/dev/null
echo "done. Apps registered:${missing}"
