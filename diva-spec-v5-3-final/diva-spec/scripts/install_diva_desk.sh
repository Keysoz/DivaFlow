#!/usr/bin/env bash
# Install or upgrade diva_desk on the disposable dev ERPNext stack (DEC-85).
#
# diva_desk is the client-only Desk layer (app_include_js). It has no doctypes
# of its own; the server rules live in diva_guard. The frontend container serves
# /assets, and it has its own copy of the bench, so the JS is copied to both
# containers. Development/staging only.
#
#   ./scripts/install_diva_desk.sh
#   CONTAINER=... FRONTEND_CONTAINER=... SITE=... BENCH=... ./scripts/install_diva_desk.sh
set -euo pipefail

CONTAINER="${CONTAINER:-frappe_docker-backend-1}"
FRONTEND_CONTAINER="${FRONTEND_CONTAINER:-frappe_docker-frontend-1}"
SITE="${SITE:-frontend}"
BENCH="${BENCH:-/home/frappe/frappe-bench}"
APP="diva_desk"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -d "${ROOT}/apps/${APP}" ]]; then
  echo "apps/${APP} not found; run from the repository root" >&2
  exit 1
fi

echo "==> copy ${APP} into ${CONTAINER}:${BENCH}/apps/${APP}"
docker exec "${CONTAINER}" mkdir -p "${BENCH}/apps/${APP}"
docker cp "${ROOT}/apps/${APP}/." "${CONTAINER}:${BENCH}/apps/${APP}/"

echo "==> register the app in the bench virtualenv (editable install)"
docker exec "${CONTAINER}" "${BENCH}/env/bin/pip" install --quiet -e "${BENCH}/apps/${APP}"

echo "==> register the app in ${BENCH}/sites/apps.txt"
docker exec "${CONTAINER}" bash -lc "grep -qx ${APP} ${BENCH}/sites/apps.txt || printf '\n${APP}\n' >> ${BENCH}/sites/apps.txt"

if docker exec "${CONTAINER}" bash -lc "cd ${BENCH} && bench --site ${SITE} list-apps | awk '{print \$1}' | grep -qx ${APP}"; then
  echo "==> ${APP} already installed; migrating"
  docker exec "${CONTAINER}" bash -lc "cd ${BENCH} && bench --site ${SITE} migrate"
else
  echo "==> installing ${APP} on ${SITE}"
  docker exec "${CONTAINER}" bash -lc "cd ${BENCH} && bench --site ${SITE} install-app ${APP}"
fi

echo "==> publish the JS asset to the containers that serve /assets"
for target in "${CONTAINER}" "${FRONTEND_CONTAINER}"; do
  docker exec "${target}" mkdir -p "${BENCH}/assets/${APP}/js"
  docker cp "${ROOT}/apps/${APP}/${APP}/public/js/." "${target}:${BENCH}/assets/${APP}/js/"
done

echo "==> clear cache"
docker exec "${CONTAINER}" bash -lc "cd ${BENCH} && bench --site ${SITE} clear-cache"

echo "==> restart the backend so gunicorn and the boot hooks pick up the app"
docker restart "${CONTAINER}" >/dev/null
docker restart "${FRONTEND_CONTAINER}" >/dev/null

echo "done. Open /app/purchase-receipt/new or /app/sales-invoice/new on ${SITE}."
