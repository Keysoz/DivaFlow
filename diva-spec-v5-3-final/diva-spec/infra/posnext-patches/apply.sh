#!/usr/bin/env bash
# Apply the tracked POS Next patch set to a bench app checkout.
# Usage: bash infra/posnext-patches/apply.sh /home/frappe/frappe-bench/apps/pos_next
set -euo pipefail
APP_DIR="${1:?usage: apply.sh /path/to/apps/pos_next}"
PATCH_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_TAG="v2.0.0"
BASE_COMMIT="e0a52c5"

if [ ! -d "$APP_DIR/.git" ]; then
  echo "Not a git checkout: $APP_DIR" >&2
  exit 1
fi
cd "$APP_DIR"

HEAD_COMMIT="$(git rev-parse --short HEAD)"
if [ "$HEAD_COMMIT" != "$BASE_COMMIT" ]; then
  echo "Refusing to apply: HEAD is $HEAD_COMMIT, the patch set targets $BASE_TAG ($BASE_COMMIT)." >&2
  echo "Check out the base tag (git checkout $BASE_TAG) or rebase the patches first — see README.md." >&2
  exit 1
fi

if ! git am -c user.name="Diva Patches" -c user.email="patches@diva.local" "$PATCH_DIR"/v2.0.0/*.patch; then
  echo "Patch series stopped. Fix the conflict, then 'git am --continue' or 'git am --abort'." >&2
  exit 1
fi
echo "Applied $(ls "$PATCH_DIR"/v2.0.0/*.patch | wc -l) patch(es). Rebuild the frontend — see README.md."
