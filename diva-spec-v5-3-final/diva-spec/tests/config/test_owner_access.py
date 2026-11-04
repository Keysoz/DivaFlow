"""Owner access configuration (DEC-104).

The owner removed Diva Guard and POS Next from the Desk apps screen (both now
open from the Diva Store dashboard) and asked for the `ahmed_ramadan` account to
land on Diva Store after login. Everything must be data in the config pipeline,
never a code path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _config() -> dict[str, Any]:
    return yaml.safe_load((ROOT / "infra" / "erpnext-config" / "config.yaml").read_text("utf-8"))


def _desk() -> dict[str, Any]:
    return yaml.safe_load((ROOT / "infra" / "erpnext-config" / "desk.yaml").read_text("utf-8"))


def test_ahmed_ramadan_record_redirects_him_to_diva_store() -> None:
    records = _config().get("records", [])
    rows = [
        record
        for record in records
        if record.get("doctype") == "User"
        and record.get("match", {}).get("username") == "ahmed_ramadan"
    ]
    assert len(rows) == 1, rows
    record = rows[0]
    assert record["create"] is False, "the pipeline must not create the staff account"
    assert record["set"]["default_workspace"] == "Diva Store"
    assert record["set"]["default_app"] == "custom_reports"
    assert record["set"]["language"] == "ar"


def test_ahmed_ramadan_roles_are_additive_and_complete() -> None:
    entries = _config().get("user_roles", [])
    rows = [entry for entry in entries if entry["user"] == "ahmed_ramadan"]
    assert len(rows) == 1, rows
    roles = set(rows[0]["roles"])
    assert {"POSNext Cashier", "Sales User", "Stock User", "Purchase User"} <= roles


def test_apply_supports_update_only_records_and_additive_roles() -> None:
    source = (ROOT / "infra" / "erpnext-config" / "apply.py").read_text(encoding="utf-8")
    assert 'entry.get("create", True)' in source
    assert "plan_user_roles" in source
    assert "fetch_user_roles" in source


def test_diva_guard_workspace_is_manager_only() -> None:
    workspaces = {entry["name"]: entry for entry in _desk()["workspaces"]}
    guard = workspaces["Diva Guard"]
    roles = {row["role"] for row in guard["roles"]}
    assert roles == {
        "System Manager",
        "Sales Manager",
        "Sales Master Manager",
        "Purchase Manager",
        "Stock Manager",
        "Accounts Manager",
        "Accounts User",
    }
    assert "POSNext Cashier" not in roles
    assert "Sales User" not in roles


def test_diva_store_has_the_two_entry_points() -> None:
    workspaces = {entry["name"]: entry for entry in _desk()["workspaces"]}
    store = workspaces["Diva Store"]
    labels = {shortcut["label"]: shortcut for shortcut in store["shortcuts"]}
    assert labels["Open POS"]["url"] == "/pos/"
    assert labels["Diva Guard"]["url"] == "/app/diva-guard"
