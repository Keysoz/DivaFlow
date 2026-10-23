#!/usr/bin/env bash
# Runs one task end to end with OpenCode, without further input from you.
# Usage: bash scripts/run-task.sh P0-10      (task IDs are in tasks.csv)
# Tip: run it inside tmux so it keeps going if your SSH connection drops:  tmux new -s diva
set -euo pipefail
TASK="${1:?Usage: bash scripts/run-task.sh TASK-ID  (see tasks.csv)}"
ROW="$(python3 - "$TASK" <<'PY'
import csv, sys
t = sys.argv[1]
for r in csv.DictReader(open('tasks.csv', encoding='utf-8-sig')):
    if r['id'] == t:
        print(f"{r['id']}: {r['title']}\nDepends on: {r['depends_on'] or 'none'}\nAcceptance criteria: {r['acceptance']}")
        break
else:
    sys.exit('Task not found in tasks.csv')
PY
)"
mkdir -p logs
LOG="logs/${TASK}-$(date +%Y%m%d-%H%M).log"
PROMPT="$(printf '%s\n\n%s' "Run this task end to end following the Autopilot workflow in AGENTS.md section 11." "$ROW")"
echo "Running ${TASK} with OpenCode (log: ${LOG})"
opencode run --agent build "$PROMPT" 2>&1 | tee "$LOG"
echo
echo "Finished. Read the final report above. If the pull request is labeled 'critical', run: bash scripts/critical-review.sh <branch-name>"
