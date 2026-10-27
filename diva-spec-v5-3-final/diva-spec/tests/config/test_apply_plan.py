"""Unit tests for the ERPNext configuration planner (TASK-E-03)."""

from apply import plan_property_setters, plan_workspaces


def test_property_setter_create() -> None:
    actions = plan_property_setters(
        [{"doctype": "Sales Invoice", "fieldname": "tax_id", "property": "hidden", "value": 1}],
        {},
    )
    assert len(actions) == 1
    assert actions[0].action == "create"
    assert actions[0].desired == "1"


def test_property_setter_noop() -> None:
    actions = plan_property_setters(
        [{"doctype": "Sales Invoice", "fieldname": "tax_id", "property": "hidden", "value": 1}],
        {("Sales Invoice", "tax_id", "hidden"): "1"},
    )
    assert actions[0].action == "noop"


def test_property_setter_update() -> None:
    actions = plan_property_setters(
        [{"doctype": "Sales Invoice", "fieldname": "tax_id", "property": "hidden", "value": 1}],
        {("Sales Invoice", "tax_id", "hidden"): "0"},
    )
    assert actions[0].action == "update"
    assert actions[0].current == "0"


def test_workspace_missing_is_reported_not_applied() -> None:
    actions = plan_workspaces([{"name": "HR", "hidden": True}], {})
    assert actions[0].action == "missing"


def test_workspace_noop_and_update() -> None:
    actions = plan_workspaces(
        [{"name": "HR", "hidden": True}, {"name": "Manufacturing", "hidden": True}],
        {"HR": "1", "Manufacturing": "0"},
    )
    assert [a.action for a in actions] == ["noop", "update"]
