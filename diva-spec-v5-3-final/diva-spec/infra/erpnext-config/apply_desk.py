"""Idempotent Desk layout: workspaces, charts and number cards (ENH-E-02).

Applies a declarative `desk.yaml` through the ERPNext REST API, with a dry-run
diff by default. Re-running must change nothing. Everything is stored as data
(Workspace, Dashboard Chart, Number Card); no core code is touched.

Usage:
  ERPNEXT_URL=... ERPNEXT_API_KEY=... ERPNEXT_API_SECRET=... \
    python3 infra/erpnext-config/apply_desk.py --config infra/erpnext-config/desk.yaml [--apply]
  ERPNEXT_URL=... ERPNEXT_USER=... ERPNEXT_PASSWORD=... (session login fallback)
"""

import argparse
import hashlib
import json
import os
import sys
from typing import Any

import yaml
from apply import Action, ApiError, Client, _quoted, _short

# Fields stored as JSON text in the database but written as YAML structures.
JSON_FIELDS = frozenset(
    {
        "content",
        "filters_json",
        "dynamic_filters_json",
        "filters_config",
        "custom_options",
        "chart_options",
    }
)


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def _canon(value: Any) -> str:
    """Canonical JSON for a value that may already be a JSON string."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return str(value)
    return str(json.dumps(value, sort_keys=True, separators=(",", ":")))


def _workspace_content(name: str, blocks: list[dict[str, Any]]) -> str:
    """Build the workspace `content` JSON with stable block ids.

    The ids are derived from the workspace, block index, type and key, so a
    second apply produces byte-identical content (idempotent).
    """
    out: list[dict[str, Any]] = []
    for index, block in enumerate(blocks):
        block_type = str(block["type"])
        data = {key: value for key, value in block.items() if key != "type"}
        key = (
            data.get("text")
            or data.get("shortcut_name")
            or data.get("chart_name")
            or data.get("number_card_name")
            or data.get("card_name")
            or str(index)
        )
        digest = hashlib.sha1(f"{name}:{index}:{block_type}:{key}".encode()).hexdigest()[:10]
        out.append({"id": digest, "type": block_type, "data": data})
    return json.dumps(out, separators=(",", ":"))


def _desired(entry: dict[str, Any]) -> dict[str, Any]:
    """Turn a YAML entry into the REST payload for its doctype."""
    payload: dict[str, Any] = {}
    values = entry.get("set") or {
        key: value
        for key, value in entry.items()
        if key not in {"doctype", "name", "children", "set"}
    }
    for key, value in values.items():
        if key == "content" and entry["doctype"] == "Workspace" and not isinstance(value, str):
            payload[key] = _workspace_content(str(entry["name"]), value)
        elif key in JSON_FIELDS and not isinstance(value, str):
            payload[key] = json.dumps(value, separators=(",", ":"))
        else:
            payload[key] = value
    for child, rows in entry.get("children", {}).items():
        payload[child] = rows
    return payload


def _same(current: dict[str, Any], key: str, desired: Any) -> bool:
    if key in JSON_FIELDS:
        return _canon(current.get(key)) == _canon(desired)
    if isinstance(desired, list):
        current_rows = current.get(key) or []
        if len(current_rows) != len(desired):
            return False
        for current_row, desired_row in zip(current_rows, desired, strict=True):
            for row_key, row_value in desired_row.items():
                if _text(current_row.get(row_key)) != _text(row_value):
                    return False
        return True
    return _text(current.get(key)) == _text(desired)


def plan_entries(
    entries: list[dict[str, Any]], existing: dict[tuple[str, str], dict[str, Any]]
) -> list[Action]:
    actions: list[Action] = []
    for entry in entries:
        doctype, name = str(entry["doctype"]), str(entry["name"])
        desired = _desired(entry)
        current = existing.get((doctype, name))
        target = f"{doctype}::{name}"
        if current is None:
            actions.append(Action("desk", target, "create", None, desired))
            continue
        if any(not _same(current, key, value) for key, value in desired.items()):
            shown = {key: current.get(key) for key in desired}
            actions.append(Action("desk", target, "update", shown, desired))
        else:
            actions.append(Action("desk", target, "noop", _summary(desired), desired))
    return actions


def _summary(values: dict[str, Any]) -> dict[str, Any]:
    return {
        key: (value if not isinstance(value, (list, dict)) else f"<{type(value).__name__}>")
        for key, value in values.items()
    }


def fetch_existing(
    client: Client, entries: list[dict[str, Any]]
) -> dict[tuple[str, str], dict[str, Any]]:
    existing: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in entries:
        doctype, name = str(entry["doctype"]), str(entry["name"])
        try:
            existing[(doctype, name)] = client.get(
                "/api/resource/" + _quoted(doctype) + "/" + _quoted(name)
            )["data"]
        except ApiError as exc:
            if exc.code != 404:
                raise
    return existing


def apply_entries(client: Client, entries: list[dict[str, Any]], actions: list[Action]) -> None:
    by_target = {f"{entry['doctype']}::{entry['name']}": entry for entry in entries}
    for action in actions:
        if action.action not in {"create", "update"}:
            continue
        entry = by_target[action.target]
        doctype, name = str(entry["doctype"]), str(entry["name"])
        payload = _desired(entry)
        if action.action == "create":
            body = {"doctype": doctype, "name": name, **payload}
            # Number Card.autoname uses the label, so create it with the
            # document name as a temporary label, then set the display label.
            if doctype == "Number Card" and payload.get("label") != name:
                body["label"] = name
                client.post("/api/resource/" + _quoted(doctype), body)
                client.put(
                    "/api/resource/" + _quoted(doctype) + "/" + _quoted(name),
                    {"label": payload["label"]},
                )
            else:
                client.post("/api/resource/" + _quoted(doctype), body)
        else:
            client.put(
                "/api/resource/" + _quoted(doctype) + "/" + _quoted(name),
                payload,
            )


def _shortcut_row(entry: dict[str, Any]) -> dict[str, Any]:
    """A Workspace Shortcut child row from a YAML entry."""
    return {
        "label": str(entry["label"]),
        "type": str(entry.get("type", "URL")),
        "url": str(entry.get("url", "")),
        "link_to": str(entry.get("link_to", "")),
        "icon": str(entry.get("icon", "link")),
        "doc_view": "",
        "report_ref_doctype": str(entry.get("report_ref_doctype", "")),
        "stats_filter": "",
    }


def _shortcut_block(workspace: str, label: str, col: int) -> dict[str, Any]:
    digest = hashlib.sha1(f"{workspace}:standard:{label}".encode()).hexdigest()[:10]
    return {"id": digest, "type": "shortcut", "data": {"shortcut_name": label, "col": col}}


def apply_standard_shortcuts(client: Client, entries: list[dict[str, Any]], apply: bool) -> int:
    """Append a shortcut to a standard workspace, idempotently.

    Standard workspaces cannot be edited directly (Frappe keeps site edits in a
    `Custom Workspace` delta), so this reads the base workspace and the existing
    delta, appends the block and widget once, and saves the delta.
    """
    changes = 0
    for entry in entries:
        workspace = str(entry["workspace"])
        label = str(entry["label"])
        try:
            base = client.get("/api/resource/" + _quoted("Workspace") + "/" + _quoted(workspace))[
                "data"
            ]
        except ApiError as exc:
            if exc.code == 404:
                print(f"missing  workspace  {workspace}::{label}")
                continue
            raise
        try:
            custom = client.get(
                "/api/resource/" + _quoted("Custom Workspace") + "/" + _quoted(workspace)
            )["data"]
        except ApiError as exc:
            if exc.code != 404:
                raise
            custom = None

        content = json.loads((custom or {}).get("content") or base.get("content") or "[]")
        widgets = json.loads((custom or {}).get("widgets") or "{}")
        already = any(str(row.get("label")) == label for row in base.get("shortcuts") or []) or any(
            block.get("type") == "shortcut" and block.get("data", {}).get("shortcut_name") == label
            for block in content
        )
        if already:
            print(f"noop     shortcut   {workspace}::{label}")
            continue

        changes += 1
        content.append(_shortcut_block(workspace, label, int(entry.get("col", 3))))
        widgets.setdefault("shortcut", []).append(_shortcut_row(entry))
        print(f"create   shortcut   {workspace}::{label}")
        if apply:
            payload = {
                "workspace": workspace,
                "content": json.dumps(content, separators=(",", ":")),
                "widgets": json.dumps(widgets, separators=(",", ":")),
            }
            if custom:
                client.put(
                    "/api/resource/" + _quoted("Custom Workspace") + "/" + _quoted(workspace),
                    payload,
                )
            else:
                client.post("/api/resource/" + _quoted("Custom Workspace"), payload)
    return changes


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

    entries: list[dict[str, Any]] = []
    for section, doctype in (
        ("dashboard_charts", "Dashboard Chart"),
        ("number_cards", "Number Card"),
        ("workspaces", "Workspace"),
    ):
        for raw in config.get(section, []):
            name = raw.get("name") or raw.get("chart_name") or raw.get("label")
            if not name:
                sys.exit(f"{section} entry is missing a name")
            entries.append({"doctype": doctype, "name": str(name), **raw})

    client = Client(base)
    key, secret = os.environ.get("ERPNEXT_API_KEY"), os.environ.get("ERPNEXT_API_SECRET")
    if key and secret:
        client.headers["Authorization"] = f"token {key}:{secret}"
    else:
        user, password = os.environ.get("ERPNEXT_USER"), os.environ.get("ERPNEXT_PASSWORD")
        if not (user and password):
            sys.exit("Set ERPNEXT_API_KEY/ERPNEXT_API_SECRET or ERPNEXT_USER/ERPNEXT_PASSWORD")
        client.post("/api/method/login", {"usr": user, "pwd": password})

    existing = fetch_existing(client, entries)
    actions = plan_entries(entries, existing)

    for action in actions:
        print(
            f"{action.action:8} {action.kind:10} {action.target}  "
            f"current={_short(action.current)} desired={_short(action.desired)}"
        )
    changed = [action for action in actions if action.action in {"create", "update"}]
    shortcut_changes = apply_standard_shortcuts(
        client, config.get("standard_shortcuts", []), apply=args.apply
    )
    total = len(changed) + shortcut_changes
    print(f"\n{total} change(s), {len(actions) - len(changed)} no-op/missing")

    if args.apply and changed:
        apply_entries(client, entries, changed)
    if args.apply and total:
        print("applied")
    elif not args.apply:
        print("dry run (use --apply to write)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
