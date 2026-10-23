#!/usr/bin/env bash
# Run ONCE by the owner, inside the repository, after `gh auth login`.
# Enables auto-merge, squash-only merges, branch cleanup, labels, and branch protection for the default branch.
# Note: GitHub requires a paid plan (for example GitHub Pro) for branch protection on PRIVATE repositories.
set -euo pipefail
REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
BRANCH="$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)"
echo "Configuring ${REPO} (default branch: ${BRANCH})"

gh api -X PATCH "repos/${REPO}" \
  -F allow_auto_merge=true -F delete_branch_on_merge=true \
  -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false >/dev/null
echo "Repository settings updated."

for spec in "critical:B60205" "phase-P0:0E8A16" "phase-E:1D76DB" "phase-PUB:5319E7" "phase-O:FBCA04" "phase-B:C2E0C6" "phase-C:BFD4F2" "phase-A:D4C5F9" "phase-M:F9D0C4" "phase-G:EDEDED"; do
  name="${spec%%:*}"; color="${spec##*:}"
  gh label create "$name" --color "$color" --force >/dev/null 2>&1 || true
done
echo "Labels created."

if gh api -X PUT "repos/${REPO}/branches/${BRANCH}/protection" --input - >/dev/null 2>&1 <<JSON
{
  "required_status_checks": null,
  "enforce_admins": true,
  "required_pull_request_reviews": { "required_approving_review_count": 0 },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
then
  echo "Branch protection enabled: pull request required, no force pushes, administrators included."
  echo "After the CI workflow exists (task P0-10), add it as a required check in GitHub: Settings > Branches."
else
  echo "Branch protection could not be enabled (private repositories need a paid GitHub plan)."
  echo "The agent rules in AGENTS.md still forbid pushing to ${BRANCH}; consider GitHub Pro (a few dollars a month) for a hard guarantee."
fi
