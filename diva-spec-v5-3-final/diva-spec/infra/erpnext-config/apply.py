"""Idempotent ERPNext configuration (TASK-E-03, E-04, E-05, E-02, E-16).

Applies a declarative config (property setters, single-doctype settings,
records and workspace visibility) through the ERPNext REST API, with a dry-run
diff by default. Re-running must change nothing (idempotent). Configuration is
stored as data; no core code is touched.

Usage (credentials from the environment, never hard-coded):
  ERPNEXT_URL=... ERPNEXT_API_KEY=... ERPNEXT_API_SECRET=... \
    python3 infra/erpnext-config/apply.py --config infra/erpnext-config/config.yaml [--apply]
  ERPNEXT_URL=... ERPNEXT_USER=... ERPNEXT_PASSWORD=... (session login fallback)
"""

import argparse
import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

import yaml


@dataclass
class Action:
    kind: str
    target: str
    action: str
    current: Any = None
    desired: Any = None


def _normalize(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def plan_property_setters(
    entries: list[dict[str, Any]], existing: dict[tuple[str, str, str], str]
) -> list[Action]:
    actions: list[Action] = []
    for entry in entries:
        key = (entry["doctype"], entry["fieldname"], entry["property"])
        target = ".".join(key)
        desired = _normalize(entry["value"])
        if key not in existing:
            actions.append(Action("property_setter", target, "create", None, desired))
        elif _normalize(existing[key]) != desired:
            actions.append(Action("property_setter", target, "update", existing[key], desired))
        else:
            actions.append(Action("property_setter", target, "noop", existing[key], desired))
    return actions


def plan_workspaces(entries: list[dict[str, Any]], existing: dict[str, str]) -> list[Action]:
    actions: list[Action] = []
    for entry in entries:
        name = entry["name"]
        desired = _normalize(entry.get("hidden", True))
        if name not in existing:
            actions.append(Action("workspace", name, "missing", None, desired))
        elif _normalize(existing[name]) != desired:
            actions.append(Action("workspace", name, "update", existing[name], desired))
        else:
            actions.append(Action("workspace", name, "noop", existing[name], desired))
    return actions


def plan_singles(
    entries: list[dict[str, Any]], existing: dict[tuple[str, str], str]
) -> list[Action]:
    actions: list[Action] = []
    for entry in entries:
        key = (entry["doctype"], entry["field"])
        target = f"{key[0]}.{key[1]}"
        desired = _normalize(entry["value"])
        if key not in existing:
            actions.append(Action("single", target, "create", None, desired))
        elif _normalize(existing[key]) != desired:
            actions.append(Action("single", target, "update", existing[key], desired))
        else:
            actions.append(Action("single", target, "noop", existing[key], desired))
    return actions


PERMISSION_FLAGS = (
    "read",
    "write",
    "create",
    "select",
    "delete",
    "submit",
    "cancel",
    "amend",
    "print",
    "email",
    "report",
    "import",
    "export",
    "share",
)


def _perm_key(row: dict[str, Any]) -> tuple[str, str, int]:
    return (str(row["parent"]), str(row["role"]), int(row.get("permlevel") or 0))


def plan_permission_mirrors(
    standard: dict[tuple[str, str, int], dict[str, Any]],
    custom: dict[tuple[str, str, int], dict[str, Any]],
) -> list[Action]:
    """Re-create standard DocPerm rows that Custom DocPerm rows have shadowed.

    Installing POS Next writes Custom DocPerm rows. Frappe then ignores the
    standard DocPerm table for those doctypes, so every role without a custom
    row loses access (TASK-E-16 / DEC-72). Mirroring the standard rows restores
    ERPNext's documented role baseline; vendor-only roles (POSNext Cashier,
    Nexus POS Manager) have no standard row and are left untouched.
    """
    actions: list[Action] = []
    for key, row in standard.items():
        target = "::".join([key[0], key[1], str(key[2])])
        wanted = {flag: int(row.get(flag) or 0) for flag in PERMISSION_FLAGS}
        if key not in custom:
            actions.append(Action("docperm", target, "create", None, wanted))
            continue
        current = {flag: int(custom[key].get(flag) or 0) for flag in PERMISSION_FLAGS}
        if current != wanted:
            actions.append(
                Action(
                    "docperm",
                    target,
                    "update",
                    {"name": custom[key].get("name"), **current},
                    wanted,
                )
            )
        else:
            actions.append(Action("docperm", target, "noop", current, wanted))
    return actions


def _record_key(entry: dict[str, Any]) -> str:
    doctype = str(entry["doctype"])
    return doctype + "::" + json.dumps(entry["match"], sort_keys=True)


def plan_records(
    entries: list[dict[str, Any]], existing: dict[str, dict[str, Any]]
) -> list[Action]:
    actions: list[Action] = []
    for entry in entries:
        key = _record_key(entry)
        desired = {k: _normalize(v) for k, v in entry["set"].items()}
        if key not in existing:
            actions.append(Action("record:" + entry["doctype"], key, "create", None, desired))
            continue
        current = existing[key]
        if any(_normalize(current.get(k)) != v for k, v in desired.items()):
            actions.append(Action("record:" + entry["doctype"], key, "update", current, desired))
        else:
            actions.append(Action("record:" + entry["doctype"], key, "noop", current, desired))
    return actions


class ApiError(RuntimeError):
    def __init__(self, message: str, code: int) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class Client:
    base: str
    headers: dict[str, str] = field(default_factory=dict)
    opener: urllib.request.OpenerDirector = field(init=False)

    def __post_init__(self) -> None:
        cooker = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cooker))

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        data = None
        headers = dict(self.headers)
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.base + path, data=data, headers=headers, method=method
        )
        try:
            with self.opener.open(request) as response:
                return json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as exc:
            message = f"{method} {path} failed: {exc.code} {exc.read()[:200]!r}"
            raise ApiError(message, exc.code) from exc

    def get(self, path: str) -> Any:
        return self._request("GET", path)

    def put(self, path: str, payload: dict[str, Any]) -> Any:
        return self._request("PUT", path, payload)

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        return self._request("POST", path, payload)


def _quoted(value: str) -> str:
    return urllib.parse.quote(value)


def _query(filters: list[list[Any]], fields: list[str]) -> str:
    return "?filters=" + _quoted(json.dumps(filters)) + "&fields=" + _quoted(json.dumps(fields))


def fetch_existing_property_setters(
    client: Client, entries: list[dict[str, Any]]
) -> dict[tuple[str, str, str], str]:
    existing: dict[tuple[str, str, str], str] = {}
    for entry in entries:
        filters = [
            ["doc_type", "=", entry["doctype"]],
            ["field_name", "=", entry["fieldname"]],
            ["property", "=", entry["property"]],
        ]
        rows = client.get(
            "/api/resource/" + _quoted("Property Setter") + _query(filters, ["name", "value"])
        )["data"]
        if rows:
            existing[(entry["doctype"], entry["fieldname"], entry["property"])] = (
                rows[0].get("value") or ""
            )
    return existing


def fetch_existing_workspaces(client: Client, names: list[str]) -> dict[str, str]:
    existing: dict[str, str] = {}
    for name in names:
        try:
            data = client.get("/api/resource/Workspace/" + _quoted(name))["data"]
        except ApiError as exc:
            if exc.code != 404:
                raise
            continue
        existing[name] = _normalize(data.get("is_hidden", 0))
    return existing


def fetch_existing_singles(
    client: Client, entries: list[dict[str, Any]]
) -> dict[tuple[str, str], str]:
    existing: dict[tuple[str, str], str] = {}
    for entry in entries:
        doctype = entry["doctype"]
        data = client.get("/api/resource/" + _quoted(doctype) + "/" + _quoted(doctype))["data"]
        existing[(doctype, entry["field"])] = data.get(entry["field"])
    return existing


def fetch_existing_records(
    client: Client, entries: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    existing: dict[str, dict[str, Any]] = {}
    for entry in entries:
        doctype = entry["doctype"]
        filters = [[k, "=", v] for k, v in entry["match"].items()]
        fields = ["name", *entry["match"].keys(), *entry["set"].keys()]
        rows = client.get("/api/resource/" + _quoted(doctype) + _query(filters, fields))["data"]
        if rows:
            existing[_record_key(entry)] = rows[0]
    return existing


def fetch_standard_permissions(
    client: Client, doctypes: list[str]
) -> dict[tuple[str, str, int], dict[str, Any]]:
    if not doctypes:
        return {}
    fields = ["parent", "role", "permlevel", *PERMISSION_FLAGS]
    filters = [["parent", "in", doctypes]]
    rows = client.get(
        "/api/resource/" + _quoted("DocPerm") + _query(filters, fields) + "&limit_page_length=0"
    )["data"]
    return {_perm_key(row): row for row in rows}


def fetch_custom_permissions(
    client: Client, doctypes: list[str]
) -> dict[tuple[str, str, int], dict[str, Any]]:
    if not doctypes:
        return {}
    filters = [["parent", "in", doctypes]]
    rows = client.get(
        "/api/resource/"
        + _quoted("Custom DocPerm")
        + _query(filters, ["name", "parent", "role", "permlevel", *PERMISSION_FLAGS])
        + "&limit_page_length=0"
    )["data"]
    return {_perm_key(row): row for row in rows}


def apply_actions(
    client: Client,
    actions: list[Action],
    entries_by_target: dict[str, dict[str, Any]],
    singles_by_target: dict[str, dict[str, Any]],
    records_by_key: dict[str, dict[str, Any]],
) -> None:
    for action in actions:
        if action.action in {"noop", "missing"}:
            continue
        if action.kind == "property_setter":
            doctype, fieldname, prop = action.target.split(".")
            entry = entries_by_target.get(action.target, {})
            payload = {
                "doctype": "Property Setter",
                "doctype_or_field": "DocField",
                "doc_type": doctype,
                "field_name": fieldname,
                "property": prop,
                "value": action.desired,
                "property_type": entry.get("property_type", "Check"),
            }
            if action.action == "create":
                client.post("/api/resource/" + _quoted("Property Setter"), payload)
            else:
                filters = [
                    ["doc_type", "=", doctype],
                    ["field_name", "=", fieldname],
                    ["property", "=", prop],
                ]
                rows = client.get(
                    "/api/resource/" + _quoted("Property Setter") + _query(filters, ["name"])
                )["data"]
                client.put(
                    "/api/resource/" + _quoted("Property Setter") + "/" + _quoted(rows[0]["name"]),
                    {"value": action.desired},
                )
        elif action.kind == "workspace":
            client.put(
                "/api/resource/Workspace/" + _quoted(action.target),
                {"is_hidden": 1 if action.desired == "1" else 0},
            )
        elif action.kind == "single":
            doctype, fieldname = action.target.split(".")
            client.put(
                "/api/resource/" + _quoted(doctype) + "/" + _quoted(doctype),
                {fieldname: _typed(singles_by_target.get(action.target, {}).get("value"))},
            )
        elif action.kind == "docperm":
            doctype, role, permlevel = action.target.split("::")
            payload = {
                "parent": doctype,
                "parenttype": "DocType",
                "parentfield": "permissions",
                "role": role,
                "permlevel": int(permlevel),
                **action.desired,
            }
            if action.action == "update":
                name = action.current.get("name")
                client.put(
                    "/api/resource/" + _quoted("Custom DocPerm") + "/" + _quoted(name),
                    action.desired,
                )
            else:
                client.post("/api/resource/" + _quoted("Custom DocPerm"), payload)
        elif action.kind.startswith("record:"):
            doctype = action.kind.split(":", 1)[1]
            record_entry = records_by_key.get(action.target)
            if record_entry is None:
                continue
            if action.action == "create":
                client.post(
                    "/api/resource/" + _quoted(doctype),
                    {**record_entry["match"], **record_entry["set"]},
                )
            else:
                name = action.current.get("name")
                client.put(
                    "/api/resource/" + _quoted(doctype) + "/" + _quoted(name),
                    record_entry["set"],
                )


def _typed(value: Any) -> Any:
    if isinstance(value, bool):
        return 1 if value else 0
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--apply", action="store_true", help="write the changes (default: dry run)")
    args = parser.parse_args()

    base = os.environ.get("ERPNEXT_URL", "").rstrip("/")
    if not base:
        sys.exit("Set ERPNEXT_URL")

    with open(args.config, encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    entries = config.get("property_setters", [])
    workspaces = config.get("workspaces", [])
    singles = config.get("singles", [])
    records = config.get("records", [])
    permission_mirrors = config.get("permission_mirrors", [])

    client = Client(base)
    key, secret = os.environ.get("ERPNEXT_API_KEY"), os.environ.get("ERPNEXT_API_SECRET")
    if key and secret:
        client.headers["Authorization"] = f"token {key}:{secret}"
    else:
        user, password = os.environ.get("ERPNEXT_USER"), os.environ.get("ERPNEXT_PASSWORD")
        if not (user and password):
            sys.exit("Set ERPNEXT_API_KEY/ERPNEXT_API_SECRET or ERPNEXT_USER/ERPNEXT_PASSWORD")
        client.post("/api/method/login", {"usr": user, "pwd": password})

    existing_ps = fetch_existing_property_setters(client, entries)
    existing_ws = fetch_existing_workspaces(client, [w["name"] for w in workspaces])
    existing_singles = fetch_existing_singles(client, singles)
    existing_records = fetch_existing_records(client, records)
    standard_perms = fetch_standard_permissions(client, permission_mirrors)
    custom_perms = fetch_custom_permissions(client, permission_mirrors)
    actions = (
        plan_property_setters(entries, existing_ps)
        + plan_workspaces(workspaces, existing_ws)
        + plan_singles(singles, existing_singles)
        + plan_records(records, existing_records)
        + plan_permission_mirrors(standard_perms, custom_perms)
    )

    for action in actions:
        print(
            f"{action.action:8} {action.kind:15} {action.target}  "
            f"current={action.current!r} desired={action.desired!r}"
        )
    changed = [a for a in actions if a.action in {"create", "update"}]
    print(f"\n{len(changed)} change(s), {len(actions) - len(changed)} no-op/missing")

    if args.apply and changed:
        entries_by_target = {f"{e['doctype']}.{e['fieldname']}.{e['property']}": e for e in entries}
        singles_by_target = {f"{e['doctype']}.{e['field']}": e for e in singles}
        records_by_key = {_record_key(e): e for e in records}
        apply_actions(client, changed, entries_by_target, singles_by_target, records_by_key)
        print("applied")
    elif not args.apply:
        print("dry run (use --apply to write)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
