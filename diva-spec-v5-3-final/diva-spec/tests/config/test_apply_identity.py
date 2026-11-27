"""The {company}/{abbr} substitution that lets one config serve every shop (PROD-22).

`infra/erpnext-config/apply.py` is on the pytest `pythonpath`, so the helpers are
imported directly rather than re-tested through a live site.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import apply
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "infra" / "erpnext-config" / "config.yaml"


class FakeClient:
    """Minimal stand-in for apply.Client, recording which paths were read."""

    def __init__(self, defaults: dict[str, Any], company: dict[str, Any]) -> None:
        self.defaults = defaults
        self.company = company
        self.paths: list[str] = []

    def get(self, path: str) -> dict[str, Any]:
        self.paths.append(path)
        if "Global%20Defaults" in path:
            return {"data": self.defaults}
        return {"data": self.company}


def load_config() -> dict[str, Any]:
    parsed: dict[str, Any] = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    return parsed


def walk(value: Any) -> list[Any]:
    found = [value]
    if isinstance(value, dict):
        for key, item in value.items():
            found.extend(walk(key))
            found.extend(walk(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(walk(item))
    return found


def test_default_company_placeholder_survives_yaml_parsing() -> None:
    """An unquoted `{company}` is a YAML flow mapping, so it must be quoted."""
    singles = load_config()["singles"]
    entry = next(
        e for e in singles if e["doctype"] == "Global Defaults" and e["field"] == "default_company"
    )
    assert entry["value"] == "{company}"
    assert isinstance(entry["value"], str)


def test_no_placeholder_is_parsed_as_a_mapping() -> None:
    for value in walk(load_config()):
        if isinstance(value, dict):
            assert value != {"company": None}, "quote the {company} placeholder"
            assert value != {"abbr": None}, "quote the {abbr} placeholder"


def test_substitution_reaches_nested_values() -> None:
    config = {
        "singles": [{"value": "{company}"}],
        "property_setters": [{"value": "Stores - {abbr}"}],
        "nested": {"list": ["/files/{abbr}-logo.png", 3]},
    }
    result = apply._substitute(config, "مؤسسة النور", "NR")
    assert result["singles"][0]["value"] == "مؤسسة النور"
    assert result["property_setters"][0]["value"] == "Stores - NR"
    assert result["nested"]["list"] == ["/files/NR-logo.png", 3]


def test_substitution_leaves_jinja_alone() -> None:
    template = "{{ doc.company }} uses {abbr}"
    assert apply._substitute(template, "Diva", "DD") == "{{ doc.company }} uses DD"


def test_substitution_does_not_mutate_the_input() -> None:
    config = {"singles": [{"value": "{company}"}]}
    apply._substitute(config, "Diva", "DD")
    assert config["singles"][0]["value"] == "{company}"


def test_unresolved_placeholders_finds_leftovers() -> None:
    config = {"a": ["{company}", "plain"], "b": {"c": "Stores - {abbr}"}}
    assert apply._unresolved_placeholders(config) == ["{abbr}", "{company}"]


def test_unresolved_placeholders_ignores_resolved_values() -> None:
    config = apply._substitute({"value": "Stores - {abbr}"}, "Diva", "DD")
    assert apply._unresolved_placeholders(config) == []


def test_resolve_identity_prefers_the_given_values() -> None:
    client = FakeClient({}, {})
    assert apply.resolve_identity(client, "مؤسسة النور", "NR") == ("مؤسسة النور", "NR")
    assert client.paths == []


def test_resolve_identity_falls_back_to_the_site() -> None:
    client = FakeClient({"default_company": "Diva Dev"}, {"abbr": "DD"})
    assert apply.resolve_identity(client, None, None) == ("Diva Dev", "DD")
    assert any("Global%20Defaults" in path for path in client.paths)
    assert any("Company" in path for path in client.paths)


def test_resolve_identity_rejects_half_a_pair() -> None:
    with pytest.raises(SystemExit):
        apply.resolve_identity(FakeClient({}, {}), "Diva Dev", None)
    with pytest.raises(SystemExit):
        apply.resolve_identity(FakeClient({}, {}), None, "DD")


def test_resolve_identity_rejects_a_site_without_a_company() -> None:
    with pytest.raises(SystemExit):
        apply.resolve_identity(FakeClient({}, {}), None, None)


def test_resolve_identity_rejects_a_company_without_an_abbr() -> None:
    with pytest.raises(SystemExit):
        apply.resolve_identity(FakeClient({"default_company": "Diva Dev"}, {}), None, None)
