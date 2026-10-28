#!/usr/bin/env bash
# Install or upgrade custom_reports (Party Statement) on the disposable dev
# ERPNext stack. Development/staging only — never run this against production.
#
#   ./scripts/install_custom_reports.sh
#   CONTAINER=... SITE=... BENCH=... ./scripts/install_custom_reports.sh
set -euo pipefail

CONTAINER="${CONTAINER:-frappe_docker-backend-1}"
SITE="${SITE:-frontend}"
BENCH="${BENCH:-/home/frappe/frappe-bench}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -d "${ROOT}/apps/custom_reports" ]]; then
  echo "apps/custom_reports not found; run from the repository root" >&2
  exit 1
fi

echo "==> copy custom_reports into ${CONTAINER}:${BENCH}/apps/custom_reports"
docker exec "${CONTAINER}" mkdir -p "${BENCH}/apps/custom_reports"
docker cp "${ROOT}/apps/custom_reports/." "${CONTAINER}:${BENCH}/apps/custom_reports/"

echo "==> register the app in the bench virtualenv (editable install)"
docker exec "${CONTAINER}" "${BENCH}/env/bin/pip" install --quiet -e "${BENCH}/apps/custom_reports"

echo "==> register the app in ${BENCH}/sites/apps.txt"
docker exec "${CONTAINER}" bash -lc "grep -qx custom_reports ${BENCH}/sites/apps.txt || printf '\ncustom_reports\n' >> ${BENCH}/sites/apps.txt"

if docker exec "${CONTAINER}" bash -lc "cd ${BENCH} && bench --site ${SITE} list-apps | awk '{print \$1}' | grep -qx custom_reports"; then
  echo "==> custom_reports already installed; migrating"
  docker exec "${CONTAINER}" bash -lc "cd ${BENCH} && bench --site ${SITE} migrate"
else
  echo "==> installing custom_reports on ${SITE}"
  docker exec "${CONTAINER}" bash -lc "cd ${BENCH} && bench --site ${SITE} install-app custom_reports"
fi

echo "==> build assets"
if docker exec "${CONTAINER}" bash -lc "command -v node >/dev/null 2>&1"; then
  docker exec "${CONTAINER}" bash -lc "cd ${BENCH} && bench build --app custom_reports"
else
  echo "node is not installed in ${CONTAINER}; skipping bench build (no compiled assets required)"
fi

echo "==> clear cache"
docker exec "${CONTAINER}" bash -lc "cd ${BENCH} && bench --site ${SITE} clear-cache"

echo "==> restart backend so gunicorn loads the app"
docker restart "${CONTAINER}" >/dev/null

echo 'done. Open /app/query-report/Party%20Statement after the desk loads.'
