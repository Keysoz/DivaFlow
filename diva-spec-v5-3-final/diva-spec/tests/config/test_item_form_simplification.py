"""The simplified Item form keeps the shop fields and hides the noise (E-04, DEC-99).

Spec 05a section 6: keep code, name, group, UOM and conversion, stock item flag,
sales and purchase flags, disabled, barcodes, image, short description and
reorder level; hide manufacturing/BOM, serial, warranty, weight and shipping,
commission, website and similar fields. Variant and cosmetics batch fields stay.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CONFIG = Path(__file__).resolve().parents[2] / "infra" / "erpnext-config" / "config.yaml"

# Fields/tabs/sections the shop never fills in.
HIDDEN = {
    # whole tabs and sections
    "manufacturing",
    "quality_tab",
    "item_tax_section_break",
    "deferred_accounting_section",
    "foreign_trade_details",
    "supplier_details",
    # assets
    "auto_create_assets",
    "is_grouped_asset",
    "asset_category",
    "asset_naming_series",
    "is_fixed_asset",
    # allowances and attribute noise
    "allow_alternative_item",
    "is_customer_provided_item",
    "over_delivery_receipt_allowance",
    "over_billing_allowance",
    # inventory noise
    "end_of_life",
    "default_material_request_type",
    "warranty_period",
    "weight_per_unit",
    "weight_uom",
    "allow_negative_stock",
    # serial numbers and samples; batches stay for cosmetics
    "has_serial_no",
    "serial_no_series",
    "use_serial_no_wise_valuation",
    "retain_sample",
    "sample_quantity",
    # deferred accounting
    "enable_deferred_expense",
    "no_of_months_exp",
    "enable_deferred_revenue",
    "no_of_months",
    # sales and import noise
    "grant_commission",
    "delivered_by_supplier",
    "country_of_origin",
    "customs_tariff_number",
}

# The fields the owner asked to keep: identity and naming, UOM and conversion,
# stock/sales/purchase flags, price and opening stock entry, barcodes, image,
# description, reorder/purchasing defaults, valuation, variants, batches and
# the accounting/price tables the shop actually uses.
KEPT = {
    # identity and naming
    "naming_series",
    "item_code",
    "item_name",
    "item_group",
    "brand",
    "description",
    "disabled",
    # opening stock and price (DEC-79/80/88)
    "opening_stock",
    "standard_rate",
    # UOM and conversion
    "stock_uom",
    "uoms",
    "uom_tab",
    "purchase_uom",
    "sales_uom",
    # flags
    "is_stock_item",
    "is_sales_item",
    "is_purchase_item",
    # barcodes and image
    "custom_barcode",
    "barcodes",
    "image",
    # reorder, purchasing and valuation
    "reorder_levels",
    "safety_stock",
    "min_order_qty",
    "lead_time_days",
    "last_purchase_rate",
    "supplier_items",
    "customer_items",
    "valuation_method",
    "valuation_rate",
    "item_defaults",
    "max_discount",
    # variants
    "has_variants",
    "variant_of",
    "variant_based_on",
    "attributes",
    # batches and expiry (cosmetics / FEFO)
    "has_batch_no",
    "create_new_batch",
    "batch_number_series",
    "has_expiry_date",
    "shelf_life_in_days",
}


def setters() -> dict[tuple[str, str, str], Any]:
    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    return {
        (row["doctype"], row["fieldname"], row["property"]): row.get("value")
        for row in data.get("property_setters", [])
    }


def test_the_hidden_item_fields_are_in_the_config() -> None:
    rows = setters()
    missing = sorted(field for field in HIDDEN if ("Item", field, "hidden") not in rows)
    assert not missing, f"not hidden in config.yaml: {missing}"
    wrong = sorted(field for field in HIDDEN if rows[("Item", field, "hidden")] != 1)
    assert not wrong, f"hidden setter is not 1: {wrong}"


def test_the_kept_item_fields_are_not_hidden() -> None:
    rows = setters()
    hidden = sorted(field for field in KEPT if rows.get(("Item", field, "hidden")) == 1)
    assert not hidden, f"the simplified form must not hide: {hidden}"


def test_batches_and_variants_stay_available() -> None:
    rows = setters()
    for field in (
        "has_batch_no",
        "create_new_batch",
        "has_expiry_date",
        "has_variants",
        "attributes",
    ):
        assert rows.get(("Item", field, "hidden")) != 1, f"{field} must stay visible"
