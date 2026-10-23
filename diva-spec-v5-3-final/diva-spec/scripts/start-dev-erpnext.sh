#!/usr/bin/env bash
# Starts a DISPOSABLE ERPNext demo for development and tests (frappe_docker pwd.yml). Never put real business data in it.
# Usage: bash scripts/start-dev-erpnext.sh [directory]
set -euo pipefail
DIR="${1:-$HOME/frappe_docker}"
[ -d "$DIR/.git" ] || git clone https://github.com/frappe/frappe_docker "$DIR"
cd "$DIR"
docker compose -f pwd.yml up -d
echo "Waiting for ERPNext to finish creating the site (about 5 minutes on the first start)..."
for i in $(seq 1 60); do
  if curl -fsS http://localhost:8080/api/method/ping >/dev/null 2>&1; then
    echo "ERPNext is up: http://localhost:8080   user: Administrator   password: admin"
    echo "Check the image versions in pwd.yml; the project targets ERPNext 16 (task P0-04a)."
    exit 0
  fi
  sleep 10
done
echo "Not ready yet. Watch progress with: docker compose -f $DIR/pwd.yml logs -f create-site"
exit 1
