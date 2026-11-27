#!/bin/bash
# Boot hook for the Diva Store WSL2 distro (DEC-109).
#
# systemd starts this after Docker. It is a no-op until the Windows installer
# has written /opt/diva/.env, so importing the distro before setup is safe.

set -euo pipefail

cd /opt/diva

if [ ! -f .env ]; then
    echo "diva-store: /opt/diva/.env is missing; skipping compose start"
    exit 0
fi

if [ ! -f store.prod.yml ]; then
    echo "diva-store: /opt/diva/store.prod.yml is missing; skipping compose start"
    exit 1
fi

exec /usr/bin/docker compose --env-file .env -f store.prod.yml up -d
