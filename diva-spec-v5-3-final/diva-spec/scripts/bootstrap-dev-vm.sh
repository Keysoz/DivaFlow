#!/usr/bin/env bash
# One-time setup for a fresh Ubuntu 24.04 (or Debian 12) dev VM. Run as a NORMAL user with sudo (not root).
# Read it before running. It installs: git, GitHub CLI, Docker + Compose, Node 22 + pnpm, uv (Python 3.12),
# ffmpeg, tmux, OpenCode and the Antigravity CLI. It does NOT install ERPNext (see start-dev-erpnext.sh).
set -euo pipefail

if [ "$(id -u)" -eq 0 ]; then echo "Run as a normal user with sudo, not as root."; exit 1; fi
. /etc/os-release
echo "Detected: ${PRETTY_NAME}"
case "${ID}" in ubuntu|debian) ;; *) echo "This script supports Ubuntu and Debian only."; exit 1;; esac

sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg git make jq tmux unzip build-essential ffmpeg python3 python3-venv python3-pip

# GitHub CLI
if ! command -v gh >/dev/null 2>&1; then
  sudo mkdir -p -m 755 /etc/apt/keyrings
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null
  sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null
  sudo apt-get update -y && sudo apt-get install -y gh
fi

# Docker Engine + Compose plugin (Docker's official repository)
if ! command -v docker >/dev/null 2>&1; then
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL "https://download.docker.com/linux/${ID}/gpg" | sudo gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${ID} ${VERSION_CODENAME} stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo usermod -aG docker "${USER}"
fi

# Node 22 + pnpm
if ! command -v node >/dev/null 2>&1 || [ "$(node -v | cut -d. -f1 | tr -d v)" -lt 20 ]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi
sudo corepack enable || true
corepack prepare pnpm@latest --activate || true

# uv manages Python 3.12 on any distro
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.12 || true

# Coding agents
command -v opencode >/dev/null 2>&1 || curl -fsSL https://opencode.ai/install | bash
command -v agy >/dev/null 2>&1 || curl -fsSL https://antigravity.google/cli/install.sh | bash

echo
echo "Done. Log out and log back in once so the docker group applies."
echo "Next, one time each:"
echo "  1) gh auth login"
echo "  2) opencode   (then type /connect, choose OpenCode Go, paste the key)"
echo "  3) agy        (sign in with Google)"
echo "  4) bash scripts/setup-github.sh"
echo "  5) bash scripts/start-dev-erpnext.sh"
