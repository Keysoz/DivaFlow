#!/usr/bin/env bash
# Second-vendor review of a critical branch with the Antigravity CLI (agy). Free tier is small (about 20 agent requests a day).
# Usage: bash scripts/critical-review.sh task/P0-10-repo-and-ci
set -euo pipefail
BRANCH="${1:?Usage: bash scripts/critical-review.sh BRANCH}"
BASE="$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)"
git fetch origin "$BASE" "$BRANCH" >/dev/null 2>&1 || true
agy -p "$(cat prompts/07-critical-review.md)

Review the changes between origin/${BASE} and origin/${BRANCH} (use git diff). Do not edit files. Answer PASS or FAIL with file and line references."
