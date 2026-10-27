#!/usr/bin/env bash
# Apply the tracked POS Next patch set to a bench app checkout.
# Usage: bash infra/posnext-patches/apply.sh /home/frappe/frappe-bench/apps/pos_next
set -euo pipefail
APP_DIR="${1:?usage: apply.sh /path/to/apps/pos_next}"
PATCH_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ ! -d "$APP_DIR/.git" ]; then
  echo "Not a git checkout: $APP_DIR" >&2
  exit 1
fi
cd "$APP_DIR"
git am "$PATCH_DIR"/v2.0.0/*.patch
echo "Applied $(ls "$PATCH_DIR"/v2.0.0/*.patch | wc -l) patch(es). Rebuild the frontend — see README.md."
