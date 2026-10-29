"""Unit tests for the Desk layout planner (ENH-E-02)."""

from typing import Any, cast

from apply import Action
from apply_desk import _desired, _same, _workspace_content, apply_entries, plan_entries


def _chart(**overrides: Any) -> dict[str, Any]:
    entry = {
        "doctype": "Dashboard Chart",
        "name": "Diva Sales Trend",
        "chart_name": "Diva Sales Trend",
        "chart_type": "Sum",
        "document_type": "Sales Invoice",
        "is_public": 1,
        "filters_json": [["Sales Invoice", "docstatus", "=", 1]],
    }
    entry.update(overrides)
    return entry


def test_workspace_content_ids_are_stable() -> None:
    blocks = [
        {"type": "header", "text": "<b>Store</b>", "col": 12},
        {"type": "chart", "chart_name": "Sales Trend", "col": 12},
    ]
    first = _workspace_content("Diva Store", blocks)
    second = _workspace_content("Diva Store", blocks)
    assert first == second
    assert '"id":"' in first
    assert _workspace_content("Diva Reports", blocks) != first


def test_json_fields_are_canonical_for_comparison() -> None:
    current = {"filters_json": '[["Sales Invoice", "docstatus", "=", 1]]'}
    desired = _desired(_chart())
    assert _same(current, "filters_json", desired["filters_json"])


def test_chart_plan_create_noop_update() -> None:
    entry = _chart()
    assert plan_entries([entry], {})[0].action == "create"
    existing = {
        ("Dashboard Chart", "Diva Sales Trend"): {
            "name": "Diva Sales Trend",
            "chart_name": "Diva Sales Trend",
            "chart_type": "Sum",
            "document_type": "Sales Invoice",
            "is_public": 1,
            "filters_json": '[["Sales Invoice", "docstatus", "=", 1]]',
            "creation": "2026-10-29",
        }
    }
    assert plan_entries([entry], existing)[0].action == "noop"
    existing[("Dashboard Chart", "Diva Sales Trend")]["chart_type"] = "Bar"
    assert plan_entries([entry], existing)[0].action == "update"


def test_workspace_child_rows_ignore_server_fields() -> None:
    entry = {
        "doctype": "Workspace",
        "name": "Diva Store",
        "label": "Diva Store",
        "charts": [{"chart_name": "Diva Sales Trend", "label": "Sales Trend"}],
        "shortcuts": [{"label": "Open POS", "type": "URL", "url": "/pos/"}],
    }
    existing = {
        ("Workspace", "Diva Store"): {
            "name": "Diva Store",
            "label": "Diva Store",
            "charts": [
                {
                    "name": "row1",
                    "parent": "Diva Store",
                    "chart_name": "Diva Sales Trend",
                    "label": "Sales Trend",
                }
            ],
            "shortcuts": [
                {
                    "name": "row2",
                    "parent": "Diva Store",
                    "label": "Open POS",
                    "type": "URL",
                    "url": "/pos/",
                    "doc_view": "",
                }
            ],
        }
    }
    assert plan_entries([entry], existing)[0].action == "noop"


def test_number_card_create_sets_name_then_display_label() -> None:
    entry = {
        "doctype": "Number Card",
        "name": "Diva Today Sales",
        "label": "Today's Sales",
        "type": "Document Type",
        "document_type": "Sales Invoice",
        "function": "Sum",
        "aggregate_function_based_on": "base_grand_total",
    }
    desired = _desired(entry)
    client = _FakeClient()
    apply_entries(
        cast(Any, client),
        [entry],
        [Action("desk", "Number Card::Diva Today Sales", "create", None, desired)],
    )
    assert client.calls[0][0] == "POST"
    assert client.calls[0][2]["label"] == "Diva Today Sales"
    assert client.calls[1][0] == "PUT"
    assert client.calls[1][2] == {"label": "Today's Sales"}


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("POST", path, payload))
        return {}

    def put(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("PUT", path, payload))
        return {}
