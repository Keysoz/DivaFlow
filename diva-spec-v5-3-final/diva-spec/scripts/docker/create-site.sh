#!/bin/bash
# Create the Diva Store site on first start (PROD-05).
#
# Every step is guarded so a resumed install continues instead of failing on an
# existing site or app. The site is left with setup_complete=0; the owner
# finishes it through /diva-setup, which creates the Company with the real
# abbreviation and then queues the full configuration.

set -euo pipefail

cd /home/frappe/frappe-bench

SITE="diva.local"

# `bench new-site` rewrites sites/apps.txt with only the apps it installed, but
# bench resolves app imports from that file. Put every Diva app back before
# installing the rest, otherwise `bench install-app diva_guard` fails with
# "No module named 'diva_guard'".
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

if [ ! -d "sites/$SITE" ]; then
    bench new-site "$SITE" \
        --mariadb-user-host-login-scope='%' \
        --admin-password "$ADMIN_PASSWORD" \
        --db-root-username root \
        --db-root-password "$DB_ROOT_PASSWORD" \
        --install-app erpnext
fi

write_apps_txt > sites/apps.txt

for app in diva_guard diva_desk custom_reports pos_next; do
    if ! bench --site "$SITE" list-apps | grep -qx "$app"; then
        bench --site "$SITE" install-app "$app"
    fi
done

bench --site "$SITE" execute diva_guard.setup.ensure_api_credentials
bench --site "$SITE" execute diva_guard.setup.prepare_first_run

echo "Diva Store: site $SITE is ready for the setup wizard."
