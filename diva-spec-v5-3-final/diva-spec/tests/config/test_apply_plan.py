"""Unit tests for the ERPNext configuration planner (TASK-E-03)."""

from apply import Action, apply_actions, plan_property_setters, plan_workspaces


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


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def post(self, path: str, payload: dict) -> dict:
        self.calls.append(("POST", path, payload))
        return {}

    def put(self, path: str, payload: dict) -> dict:
        self.calls.append(("PUT", path, payload))
        return {}

    def get(self, path: str) -> dict:
        return {"data": [{"name": "PS-1"}]}


def test_property_setter_create_payload() -> None:
    client = FakeClient()
    apply_actions(
        client, [Action("property_setter", "Sales Invoice.tax_id.hidden", "create", None, "1")], {}
    )
    method, _path, payload = client.calls[0]
    assert method == "POST"
    assert payload["doctype_or_field"] == "DocField"
    assert payload["property_type"] == "Check"
    assert payload["value"] == "1"


def test_property_setter_update_payload() -> None:
    client = FakeClient()
    apply_actions(
        client, [Action("property_setter", "Sales Invoice.tax_id.hidden", "update", "0", "1")], {}
    )
    method, _path, payload = client.calls[-1]
    assert method == "PUT"
    assert payload == {"value": "1"}
