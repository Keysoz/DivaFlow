#!/usr/bin/env bash
# Install or upgrade diva_guard on the disposable dev ERPNext stack (TASK-E-14a).
#
# This script is for development/staging only. It never touches production:
# set CONTAINER, SITE and BENCH explicitly if your stack differs.
set -euo pipefail

CONTAINER="${CONTAINER:-frappe_docker-backend-1}"
SITE="${SITE:-frontend}"
BENCH="${BENCH:-/home/frappe/frappe-bench}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -d "${ROOT}/apps/diva_guard" ]]; then
  echo "apps/diva_guard not found; run from the repository root" >&2
  exit 1
fi

echo "==> install rules-engine into ${CONTAINER}"
docker cp "${ROOT}/packages/rules-engine" "${CONTAINER}:/tmp/rules-engine"
docker exec "${CONTAINER}" "${BENCH}/env/bin/pip" install --quiet /tmp/rules-engine

echo "==> copy diva_guard into ${CONTAINER}:${BENCH}/apps/diva_guard"
docker exec "${CONTAINER}" mkdir -p "${BENCH}/apps/diva_guard"
docker cp "${ROOT}/apps/diva_guard/." "${CONTAINER}:${BENCH}/apps/diva_guard/"

if docker exec "${CONTAINER}" bash -lc "cd ${BENCH} && bench --site ${SITE} list-apps | grep -qx diva_guard"; then
  echo "==> diva_guard already installed; migrating"
  docker exec "${CONTAINER}" bash -lc "cd ${BENCH} && bench --site ${SITE} migrate"
else
  echo "==> installing diva_guard on ${SITE}"
  docker exec "${CONTAINER}" bash -lc "cd ${BENCH} && bench --site ${SITE} install-app diva_guard"
fi

echo "==> restarting the backend so gunicorn loads the app"
docker restart "${CONTAINER}" >/dev/null

echo "done. Seed settings with scripts/seed_diva_guard.py (DIVA_MANAGER_PIN from the secret store)."
