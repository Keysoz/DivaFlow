# Appendix: ERPNext verification

Evidence for the ERPNext tasks. Created by TASK-P0-04a (2026-10-26); TASK-P0-04 adds the verification findings below.

## 1. Disposable development stack (TASK-P0-04a)

Built by `scripts/start-dev-erpnext.sh`: it clones `frappe/frappe_docker` into `$HOME/frappe_docker` (or a directory you pass) and runs `docker compose -f pwd.yml up -d`. This is a **disposable demo**: never put real business data in it. The production ERPNext is installed on the store VM in TASK-E-00a.

| Item | Value |
|---|---|
| Date of record | 2026-10-26 |
| Start command | `bash scripts/start-dev-erpnext.sh` |
| Stop command | `docker compose -f ~/frappe_docker/pwd.yml down` |
| URL | `http://localhost:8080` (port 8080 as required by P0-04a) |
| Site name | `frontend` (default in `pwd.yml`) |
| Login | `Administrator` / `admin` — the documented disposable dev default printed by the start script |
| Image pin | `frappe/erpnext:v16.52.1` (already tagged to the major version 16 in `pwd.yml`; no change was needed) |
| Image digest | `sha256:eb1c22d2bb926ed97352b63334507bf0297f1ca1244b406e3f30869ca5d0092b` |
| Database | `mariadb:11.8` (`sha256:f16d7a344413e519dff518f27bdb221388f84b0d274c97c4fb5f2cb0dc1b34fa`) |
| Cache and queue | `redis:6.2-alpine` (`sha256:592b215e9287182f11ba9d7c229dc0ba312bb900a016ea65ae378b0127567319`) |
| Host | Linux 6.12.100+deb13-amd64, Docker 29.9.2, Docker Compose v5.6.1 |

### Recorded versions

```
$ docker exec frappe_docker-backend-1 bench version
erpnext 16.52.1  ()
frappe 16.53.0  ()

$ docker exec frappe_docker-backend-1 bench --site frontend list-apps
frappe  16.53.0 UNVERSIONED
erpnext 16.52.1 UNVERSIONED
```

The `UNVERSIONED` label is normal for a locally built app inside the image; the versions in the first command are authoritative.

### Health evidence

```
$ curl -fsS http://localhost:8080/api/method/ping
{"message":"pong"}

$ curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/login
200

$ docker ps --format "{{.Names}} {{.Ports}}" | grep 8080
frappe_docker-frontend-1 0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp
```

## 2. Verification findings (TASK-P0-04)

To be filled by TASK-P0-04: version, installed apps, stock reservation behavior, Item Barcode with UOM, Dozen whole-number UOM, Payment Terms, credit limit, and the REST endpoints the adapter needs.
