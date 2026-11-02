"""The Desk UI contract for the owner's ENH-E-05 follow-up corrections (DEC-97, DEC-100).

These are static checks on the client layer because the behaviour itself
(buttons, dialogs, Enter) only exists in a browser; the live browser checks are
recorded in `docs/appendix-erpnext-verification.md` and the server half is
covered by `scripts/test_desk_workflows.py`.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESK_JS = ROOT / "apps" / "diva_desk" / "diva_desk" / "public" / "js" / "diva_desk.js"
POS_PATCHES = ROOT / "infra" / "posnext-patches" / "v2.0.0"


def desk_js() -> str:
    return DESK_JS.read_text(encoding="utf-8")


def test_purchase_receipt_keeps_the_one_erpnext_primary_action() -> None:
    """No Save/Submit split: the Desk must not override the primary action."""
    source = desk_js()
    assert "set_primary_action" not in source
    assert "Save & Submit" not in source


def test_print_is_its_own_button_and_sharing_is_one_dropdown() -> None:
    source = desk_js()
    start = source.index("function add_share_buttons")
    block = source[start : source.index("function fieldname_of", start)]
    assert 'frm.add_custom_button(__("Print")' in block
    assert 'frm.add_custom_button(\n\t\t\t__("Download PDF")' in block
    assert '__("Open in WhatsApp"), () => open_whatsapp(frm), __("Share")' in block
    assert block.count('__("Share")') == 2


def test_add_new_item_dialog_is_restored_on_every_surface() -> None:
    source = desk_js()
    assert "function open_item_dialog" in source
    assert "function add_new_item_dialog" in source
    # The Item list "Add" opens the Diva dialog, not the standard quick entry.
    assert 'if (doctype === "Item" && is_item_list_route())' in source
    # Purchase Receipt, Purchase Invoice and Sales Invoice each offer it.
    assert source.count('frm.add_custom_button(__("Add New Item")') == 3
    # Document mode must not post a second opening reconciliation.
    assert "post_opening_stock: 0" in source
    assert "post_opening_stock: 1" in source


def test_edit_in_full_is_offered_by_both_dialogs() -> None:
    """DEC-100: the dialog can hand its values to the full Item form."""
    source = desk_js()
    assert "function open_item_full_form" in source
    assert "function item_form_defaults" in source
    # Both the Item-list dialog and the document dialog offer it.
    assert source.count('secondary_action_label: __("Edit in full")') == 2
    # The handoff is applied once on the new Item form.
    assert "ITEM_FORM_DEFAULTS_KEY" in source
    assert 'frappe.ui.form.on("Item", {\n\t\trefresh(frm)' in source
    # Buying and wholesale prices are carried into the full form.
    assert "custom_buying_price" in source
    assert "custom_wholesale_price" in source


def test_item_has_the_owner_approved_price_fields() -> None:
    """DEC-100 amendment: two governed Item fields carry the buying/wholesale price."""
    config = (ROOT / "infra" / "erpnext-config" / "config.yaml").read_text(encoding="utf-8")
    for fieldname in ("custom_buying_price", "custom_wholesale_price"):
        assert f"fieldname: {fieldname}" in config, fieldname
    assert "fieldname: custom_buying_price\n    label: Buying Price (EGP/Dozen)" in config
    assert "fieldname: custom_wholesale_price\n    label: Wholesale Price (EGP/Dozen)" in config
    events = (ROOT / "apps" / "diva_guard" / "diva_guard" / "events.py").read_text(encoding="utf-8")
    assert "def sync_item_price_fields" in events
    assert '"Standard Buying"' in events
    assert '"Wholesale"' in events
    desk_api = (ROOT / "apps" / "diva_guard" / "diva_guard" / "desk_api.py").read_text(
        encoding="utf-8"
    )
    # The entered opening balance is kept on the Item so its form shows it.
    assert '"opening_stock": float(qty)' in desk_api


def test_enter_on_item_stock_and_price_fields_never_opens_the_image_upload() -> None:
    source = desk_js()
    start = source.index("const ITEM_SAFE_NEXT")
    block = source[start : source.index("function handle_item_enter", start)]
    assert 'opening_stock: "standard_rate"' in block
    assert 'standard_rate: "stock_uom"' in block
    assert 'stock_uom: "description"' in block
    assert "handle_item_enter(event)" in source


def test_pos_next_groups_the_same_share_actions() -> None:
    patches = sorted(POS_PATCHES.glob("0016-*.patch"))
    assert len(patches) == 1, patches
    patch = patches[0].read_text(encoding="utf-8")
    assert "+" in patch
    assert "Dropdown" in patch
    assert '__("Share")' in patch
    assert "Download PDF" in patch
    assert "Open in WhatsApp" in patch
    assert '<Button @click="handlePrint">' in patch


def test_share_and_dialog_strings_have_arabic_translations() -> None:
    config = (ROOT / "infra" / "erpnext-config" / "config.yaml").read_text(encoding="utf-8")
    for source_text in (
        "Share",
        "Create Item & Add Line",
        "Opening Stock (Dozen)",
        "Quantity (Dozen)",
        "Source Warehouse",
        "Store WhatsApp number",
        "Edit in full",
    ):
        assert f'source_text: "{source_text}"' in config, source_text
