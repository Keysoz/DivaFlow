"""Unit tests for the ERPNext configuration planner (TASK-E-03)."""

from apply import (
    Action,
    ApiError,
    apply_actions,
    fetch_existing_print_formats,
    plan_custom_fields,
    plan_permission_mirrors,
    plan_print_formats,
    plan_property_setters,
    plan_records,
    plan_singles,
    plan_workspaces,
)


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
        client,
        [Action("property_setter", "Sales Invoice.tax_id.hidden", "create", None, "1")],
        {},
        {},
        {},
    )
    method, _path, payload = client.calls[0]
    assert method == "POST"
    assert payload["doctype_or_field"] == "DocField"
    assert payload["property_type"] == "Check"
    assert payload["value"] == "1"


def test_property_setter_update_payload() -> None:
    client = FakeClient()
    apply_actions(
        client,
        [Action("property_setter", "Sales Invoice.tax_id.hidden", "update", "0", "1")],
        {},
        {},
        {},
    )
    method, _path, payload = client.calls[-1]
    assert method == "PUT"
    assert payload == {"value": "1"}


def test_plan_singles() -> None:
    entries = [{"doctype": "Stock Settings", "field": "allow_negative_stock", "value": 0}]
    assert plan_singles(entries, {})[0].action == "create"
    assert (
        plan_singles(entries, {("Stock Settings", "allow_negative_stock"): "0"})[0].action == "noop"
    )
    assert (
        plan_singles(entries, {("Stock Settings", "allow_negative_stock"): "1"})[0].action
        == "update"
    )


def test_plan_records() -> None:
    entries = [
        {"doctype": "UOM", "match": {"uom_name": "Dozen"}, "set": {"must_be_whole_number": 1}}
    ]
    assert plan_records(entries, {})[0].action == "create"
    key = "UOM::" + '{"uom_name": "Dozen"}'
    assert (
        plan_records(entries, {key: {"name": "Dozen", "must_be_whole_number": 1}})[0].action
        == "noop"
    )
    assert (
        plan_records(entries, {key: {"name": "Dozen", "must_be_whole_number": 0}})[0].action
        == "update"
    )


def test_permission_mirror_creates_missing_standard_rows() -> None:
    standard = {
        ("Sales Invoice", "Accounts User", 0): {
            "parent": "Sales Invoice",
            "role": "Accounts User",
            "permlevel": 0,
            "read": 1,
            "create": 1,
            "submit": 1,
        }
    }
    actions = plan_permission_mirrors(standard, {})
    assert len(actions) == 1
    assert actions[0].action == "create"
    assert actions[0].target == "Sales Invoice::Accounts User::0"
    assert actions[0].desired["read"] == 1
    assert actions[0].desired["create"] == 1
    assert actions[0].desired["delete"] == 0


def test_permission_mirror_repairs_narrowed_vendor_rows() -> None:
    standard = {
        ("Address", "All", 0): {
            "parent": "Address",
            "role": "All",
            "permlevel": 0,
            "read": 1,
            "write": 1,
            "create": 1,
        }
    }
    custom = {("Address", "All", 0): {"name": "abc", "read": 1, "write": 0, "create": 0}}
    actions = plan_permission_mirrors(standard, custom)
    assert actions[0].action == "update"
    assert actions[0].current["name"] == "abc"
    assert actions[0].desired["write"] == 1


def test_permission_mirror_is_idempotent() -> None:
    standard = {
        ("Sales Invoice", "Accounts User", 0): {
            "parent": "Sales Invoice",
            "role": "Accounts User",
            "permlevel": 0,
            "read": 1,
        }
    }
    custom = {
        ("Sales Invoice", "Accounts User", 0): {
            "name": "abc",
            "read": 1,
            "write": 0,
            "create": 0,
            "select": 0,
            "delete": 0,
            "submit": 0,
            "cancel": 0,
            "amend": 0,
            "print": 0,
            "email": 0,
            "report": 0,
            "import": 0,
            "export": 0,
            "share": 0,
        }
    }
    actions = plan_permission_mirrors(standard, custom)
    assert actions[0].action == "noop"


def test_docperm_create_payload() -> None:
    client = FakeClient()
    apply_actions(
        client,
        [
            Action(
                "docperm",
                "Sales Invoice::Accounts User::0",
                "create",
                None,
                {"read": 1, "create": 1, "submit": 1},
            )
        ],
        {},
        {},
        {},
    )
    method, path, payload = client.calls[0]
    assert method == "POST"
    assert path.endswith("/Custom%20DocPerm")
    assert payload["parent"] == "Sales Invoice"
    assert payload["parenttype"] == "DocType"
    assert payload["role"] == "Accounts User"
    assert payload["permlevel"] == 0
    assert payload["read"] == 1
    assert payload["create"] == 1


def test_docperm_update_payload_uses_row_name() -> None:
    client = FakeClient()
    apply_actions(
        client,
        [
            Action(
                "docperm",
                "Address::All::0",
                "update",
                {"name": "abc123", "read": 1},
                {"read": 1, "write": 1},
            )
        ],
        {},
        {},
        {},
    )
    method, path, payload = client.calls[0]
    assert method == "PUT"
    assert path.endswith("/Custom%20DocPerm/abc123")
    assert payload["write"] == 1
    assert "parent" not in payload


def test_plan_print_formats_create_and_noop() -> None:
    entry = {"name": "Diva Receipt", "doc_type": "Sales Invoice", "html": "<p>hi</p>"}
    assert plan_print_formats([entry], {})[0].action == "create"
    existing = {
        "Diva Receipt": {
            "name": "Diva Receipt",
            "doc_type": "Sales Invoice",
            "print_format_type": "Jinja",
            "standard": "No",
            "custom_format": 1,
            "default_print_language": "ar",
            "disabled": 0,
            "html": "<p>hi</p>",
        }
    }
    assert plan_print_formats([entry], existing)[0].action == "noop"
    existing["Diva Receipt"]["html"] = "<p>old</p>"
    assert plan_print_formats([entry], existing)[0].action == "update"


def test_print_format_create_payload() -> None:
    client = FakeClient()
    desired = {
        "doc_type": "Sales Invoice",
        "print_format_type": "Jinja",
        "standard": "No",
        "custom_format": 1,
        "default_print_language": "ar",
        "disabled": 0,
        "html": "<p>hi</p>",
    }
    apply_actions(
        client, [Action("print_format", "Diva Receipt", "create", None, desired)], {}, {}, {}
    )
    method, path, payload = client.calls[0]
    assert method == "POST"
    assert path.endswith("/Print%20Format")
    assert payload["name"] == "Diva Receipt"
    assert payload["doc_type"] == "Sales Invoice"
    assert payload["html"] == "<p>hi</p>"


def test_print_format_update_payload_quotes_spaced_name() -> None:
    client = FakeClient()
    desired = {
        "doc_type": "Sales Invoice",
        "print_format_type": "Jinja",
        "standard": "No",
        "custom_format": 1,
        "default_print_language": "ar",
        "disabled": 0,
        "html": "<p>new</p>",
    }
    apply_actions(
        client,
        [
            Action(
                "print_format",
                "Diva Sales Invoice A4",
                "update",
                {"name": "Diva Sales Invoice A4"},
                desired,
            )
        ],
        {},
        {},
        {},
    )
    method, path, payload = client.calls[0]
    assert method == "PUT"
    assert path.endswith("/Print%20Format/Diva%20Sales%20Invoice%20A4")
    assert "name" not in payload
    assert payload["html"] == "<p>new</p>"


class FailingClient(FakeClient):
    def __init__(self, code: int) -> None:
        super().__init__()
        self.code = code

    def get(self, path: str) -> dict:
        raise ApiError("boom", self.code)


def test_fetch_print_formats_ignores_404_only() -> None:
    assert fetch_existing_print_formats(FailingClient(404), ["X"]) == {}
    try:
        fetch_existing_print_formats(FailingClient(500), ["X"])
    except ApiError as exc:
        assert exc.code == 500
    else:  # pragma: no cover - explicit failure path
        raise AssertionError("500 must propagate")


def test_plan_custom_fields_create_update_noop() -> None:
    entry = {
        "dt": "Item",
        "fieldname": "custom_barcode",
        "label": "Barcode",
        "fieldtype": "Data",
        "allow_in_quick_entry": 1,
    }
    assert plan_custom_fields([entry], {})[0].action == "create"
    existing = {
        ("Item", "custom_barcode"): {
            "name": "Item-custom_barcode",
            "label": "Barcode",
            "fieldtype": "Data",
            "allow_in_quick_entry": 1,
        }
    }
    assert plan_custom_fields([entry], existing)[0].action == "noop"
    existing[("Item", "custom_barcode")]["label"] = "Old"
    assert plan_custom_fields([entry], existing)[0].action == "update"


def test_custom_field_create_payload() -> None:
    client = FakeClient()
    desired = {
        "label": "Barcode",
        "fieldtype": "Data",
        "allow_in_quick_entry": 1,
    }
    apply_actions(
        client,
        [Action("custom_field", "Item::custom_barcode", "create", None, desired)],
        {},
        {},
        {},
    )
    method, path, payload = client.calls[0]
    assert method == "POST"
    assert path.endswith("/Custom%20Field")
    assert payload["dt"] == "Item"
    assert payload["fieldname"] == "custom_barcode"
    assert payload["allow_in_quick_entry"] == 1


def test_custom_field_update_payload() -> None:
    client = FakeClient()
    apply_actions(
        client,
        [
            Action(
                "custom_field",
                "Item::custom_barcode",
                "update",
                {"name": "Item-custom_barcode"},
                {"label": "Barcode", "allow_in_quick_entry": 1},
            )
        ],
        {},
        {},
        {},
    )
    method, path, payload = client.calls[0]
    assert method == "PUT"
    assert path.endswith("/Custom%20Field/Item-custom_barcode")
    assert payload == {"label": "Barcode", "allow_in_quick_entry": 1}
