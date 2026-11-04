#!/usr/bin/env bash
# Starts a DISPOSABLE ERPNext demo for development and tests (frappe_docker pwd.yml). Never put real business data in it.
# Usage: bash scripts/start-dev-erpnext.sh [directory]
set -euo pipefail
DIR="${1:-$HOME/frappe_docker}"
[ -d "$DIR/.git" ] || git clone https://github.com/frappe/frappe_docker "$DIR"
cd "$DIR"
if ! grep -qE 'image: frappe/erpnext:v16' pwd.yml; then
  echo "pwd.yml does not pin a frappe/erpnext v16 image; refusing to start (task P0-04a targets ERPNext 16)." >&2
  echo "Pin the image in $DIR/pwd.yml, then re-run." >&2
  exit 1
fi
# DEC-103: the stock configurator rewrites sites/apps.txt from its own image on
# every start, silently unregistering apps installed later in the backend
# (pos_next, diva_guard, diva_desk, custom_reports). Only write it on first boot.
if grep -Fq 'ls -1 apps > sites/apps.txt;' pwd.yml; then
  # \|\| is sed's escaped pipe (the replacement contains two literal pipes).
  sed -i 's~ls -1 apps > sites/apps.txt;~[ -f sites/apps.txt ] \|\| ls -1 apps > sites/apps.txt;~' pwd.yml
  echo "Patched the configurator in $DIR/pwd.yml so it no longer overwrites sites/apps.txt (DEC-103)."
fi
docker compose -f pwd.yml up -d
echo "Waiting for ERPNext to finish creating the site (about 5 minutes on the first start)..."
for i in $(seq 1 60); do
  if curl -fsS http://localhost:8080/api/method/ping >/dev/null 2>&1; then
    echo "ERPNext is up: http://localhost:8080   user: Administrator   password: admin"
    "$(dirname "${BASH_SOURCE[0]}")/ensure-apps-registered.sh"
    echo "Check the image versions in pwd.yml; the project targets ERPNext 16 (task P0-04a)."
    exit 0
  fi
  sleep 10
done
echo "Not ready yet. Watch progress with: docker compose -f $DIR/pwd.yml logs -f create-site"
exit 1
