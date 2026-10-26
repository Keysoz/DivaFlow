#!/usr/bin/env python3
"""Create GitHub issues from tasks.csv with the GitHub CLI (gh).

Dry run by default: prints what it would create. Add --create to really create.
Examples:
  python3 scripts/create_issues.py --phase P0
  python3 scripts/create_issues.py --phase E --create
Requires: gh installed and logged in (gh auth login), run inside the repository.
"""

import argparse
import csv
import subprocess
import sys

ap = argparse.ArgumentParser()
ap.add_argument(
    "--phase",
    required=True,
    help="Phase to create, e.g. P0, E, PUB, O, B, C, A, M, or 'All gates'",
)
ap.add_argument(
    "--create", action="store_true", help="really create the issues (default is a dry run)"
)
ap.add_argument("--csv", default="tasks.csv")
args = ap.parse_args()

with open(args.csv, newline="", encoding="utf-8-sig") as f:
    tasks = [r for r in csv.DictReader(f) if r["phase"] == args.phase]
if not tasks:
    sys.exit(f"No tasks found for phase {args.phase}")

for t in tasks:
    title = f"{t['id']}: {t['title']}"[:240]
    body = (
        f"**Phase:** {t['phase']}\n**Depends on:** {t['depends_on'] or 'none'}\n"
        f"**Source:** docs/{t['source']}.md\n\n**Acceptance criteria**\n{t['acceptance']}\n\n"
        "Follow AGENTS.md. Use prompts/00-session-start.md. "
        "Critical code needs a Western-vendor review (prompts/07)."
    )
    if args.create:
        subprocess.run(
            [
                "gh",
                "issue",
                "create",
                "--title",
                title,
                "--body",
                body,
                "--label",
                f"phase-{t['phase']}",
            ],
            check=False,
        )
    else:
        print(f"[dry run] {title}")
print(f"{len(tasks)} issue(s) {'created' if args.create else 'would be created'}.")
