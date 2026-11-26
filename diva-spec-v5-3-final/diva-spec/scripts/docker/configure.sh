#!/bin/bash
# Write the shared bench configuration for the Diva Store stack (PROD-05).
#
# Runs once before the site is created. Passwords arrive as environment
# variables from the installer-generated .env; nothing is hard-coded.

set -euo pipefail

cd /home/frappe/frappe-bench

mkdir -p sites

# bench builds its command list and sys.path from sites/apps.txt. Derive it
# from the app directories so `rules-engine` (a library, not a bench app) is
# never listed. frappe must stay first.
write_apps_txt() {
    local app
    echo "frappe"
    for dir in apps/*/; do
        app="$(basename "$dir")"
        if [ "$app" != "frappe" ] && [ -f "apps/$app/$app/hooks.py" ]; then
            echo "$app"
        fi
    done
    return 0
}

write_apps_txt > sites/apps.txt

bench set-config -g db_host db
bench set-config -gp db_port 3306
bench set-config -g redis_cache "redis://:${REDIS_CACHE_PASSWORD}@redis-cache:6379"
bench set-config -g redis_queue "redis://:${REDIS_QUEUE_PASSWORD}@redis-queue:6379"
bench set-config -g redis_socketio "redis://:${REDIS_QUEUE_PASSWORD}@redis-queue:6379"
bench set-config -gp socketio_port 9000
bench set-config -g host_name "http://localhost:8080"
bench set-config -g serve_default_site true

echo "Diva Store: shared configuration written."
