# 24 Autopilot Setup: VM, GitHub, OpenCode, Fewest Manual Steps

## 1. Where to run it: use a dedicated Linux VM (DEC-62)
You want to give the agent broad access. Give it a **disposable development VM**, not your laptop's own operating system. Reasons: a mistake cannot touch your personal files or accounts; you can snapshot and roll back; Docker and ERPNext need RAM and disk that a VM can reserve; the VM keeps working when your laptop sleeps.
| Option | When | Cost |
|---|---|---|
| Local VM (VirtualBox, KVM or similar) on your Linux laptop | The laptop has 16 GB RAM or more | $0 |
| Small cloud VM | Less RAM at home, or you want it always on | about $10–20 per month |
Size: 4 vCPU, 8–16 GB RAM, 80–100 GB disk, **Ubuntu 24.04 LTS**.
**Run OpenCode inside the VM** (not on the laptop controlling the VM remotely). You connect from the laptop with SSH, ideally inside `tmux` so tasks keep running if the connection drops. No personal keys on the VM: use one GitHub login for the project only. The VM never holds production credentials (DEC-38).

## 2. One-time setup (about 30–45 minutes)
1. Create the VM, then `ssh` in.
2. `git clone` your private repository (it already contains this package) and `cd` into it.
3. `bash scripts/bootstrap-dev-vm.sh`: installs git, GitHub CLI, Docker, Node, pnpm, Python 3.12 (through `uv`), ffmpeg, tmux, OpenCode and the Antigravity CLI. Log out and back in once.
4. `gh auth login` (use the device-code option and approve it in a browser).
5. `opencode`, then type `/connect`, choose **OpenCode Go**, paste your key. Run `opencode models` and compare the IDs with `opencode.json` (`23`).
6. `agy` and sign in with Google (this is the free Western-vendor reviewer; its free tier is small, about 20 agent requests a day, so use it only for critical reviews).
7. `bash scripts/setup-github.sh`: turns on auto-merge, squash merges, labels and branch protection (private repositories need a paid GitHub plan for protection; the script tells you if it cannot).
8. `bash scripts/start-dev-erpnext.sh`: starts a disposable ERPNext demo at port 8080 (Administrator / admin) for development and tests. You do not need to install ERPNext yourself.

## 3. Running the build
- Start `tmux new -s diva`.
- One task: `bash scripts/run-task.sh P0-10`. OpenCode plans, implements, calls the specialist agents, runs the tests, asks the other-vendor reviewer, pushes a branch and opens a pull request. You read the final report.
- Non-critical pull requests merge themselves when CI passes (auto-merge). **Critical** ones wait for you: run `bash scripts/critical-review.sh <branch>`, then read the result and merge.
- Create issues from the task list if you like: `python3 scripts/create_issues.py --phase P0 --create`.

## 4. Do I switch models, tabs and mentions myself?
Not for autopilot. Each agent has its own fixed model (`opencode.json`). `scripts/run-task.sh` starts the `build` agent; `AGENTS.md` section 11 tells it to call the specialist subagents by name for tests, docs, screens, Arabic text, screenshots and reviews. Switching with Tab and typing @mentions is only for interactive sessions when you want to steer. The agent may occasionally skip a delegation; the pull request checklist and the reviewers catch it.

## 5. What stays manual
- Rotating the exposed credentials on each platform (`P0-01`).
- Creating third-party accounts and approvals (Meta, WhatsApp, TikTok, Bosta, domain).
- Your acceptance scripts at each gate (`18`) and Arabic wording review.
- Merging `critical` pull requests.
- Any task the agent reports as `BLOCKED`.

## 6. Permissions and safety
`opencode.json` allows edits and shell commands so runs do not stop for approval, and denies force pushes, pushes to the default branch, `rm -rf /` style commands and manual merges (only `gh pr merge --auto` is allowed). Test the rules once with a harmless command. For a hard guarantee that the agent cannot merge critical work, use a separate GitHub bot account with write access and require your approval on the default branch (optional).

## 7. Cheaper ways to get the same features
See `25-cost-savings.md`.
