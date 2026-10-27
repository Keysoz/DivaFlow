"""Contract tests for the ERPNext adapter (TASK-E-12).

These tests talk to a real ERPNext instance and are skipped unless
ERPNEXT_URL is set in the environment.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from decimal import Decimal

import pytest

from erpnext_adapter import ErpNextClient

pytestmark = [
    pytest.mark.contract,
    pytest.mark.skipif(not os.environ.get("ERPNEXT_URL"), reason="ERPNEXT_URL not set"),
]


@pytest.fixture(scope="module")
def erp_client() -> Iterator[ErpNextClient]:
    """Create an ERPNext client from environment credentials."""
    url = os.environ.get("ERPNEXT_URL")
    if not url:
        pytest.skip("ERPNEXT_URL not set")

    api_key = os.environ.get("ERPNEXT_API_KEY")
    api_secret = os.environ.get("ERPNEXT_API_SECRET")
    username = os.environ.get("ERPNEXT_USER")
    password = os.environ.get("ERPNEXT_PASSWORD")

    if api_key and api_secret:
        client = ErpNextClient(url, api_key=api_key, api_secret=api_secret)
    elif username and password:
        client = ErpNextClient(url, username=username, password=password)
    else:
        pytest.skip("No ERPNext credentials (set ERPNEXT_API_KEY/SECRET or ERPNEXT_USER/PASSWORD)")

    yield client
    client.close()


class TestContract:
    """Contract tests verify the adapter works against a real ERPNext instance."""

    def test_ping(self, erp_client: ErpNextClient) -> None:
        """Ping endpoint returns pong."""
        assert erp_client.ping() is True

    def test_barcode_lookup(self, erp_client: ErpNextClient) -> None:
        """Barcode 2000000000015 resolves to P004-DOZEN.

        NOTE: This test currently FAILS due to a bug in the adapter.
        The adapter's get_item_by_barcode() requests fields ["parent","uom"]
        from the Item Barcode list endpoint, but Frappe's REST API for child
        doctypes only returns {"name": "..."}. The adapter needs to be fixed
        to fetch the full record or use a different query approach.
        """
        item = erp_client.get_item_by_barcode("2000000000015")
        assert item is not None, "Barcode 2000000000015 should exist in dev ERPNext"
        assert item["item_code"] == "P004-DOZEN"

    def test_price_list_rate(self, erp_client: ErpNextClient) -> None:
        """P004-DOZEN price in Standard Selling/Dozen is 1440."""
        rate = erp_client.get_price_list_rate("P004-DOZEN", "Standard Selling", "Dozen")
        assert rate == Decimal("1440")

    def test_bin_actual_qty(self, erp_client: ErpNextClient) -> None:
        """P004-DOZEN bin actual quantity is 60."""
        bin_data = erp_client.get_bin("P004-DOZEN")
        assert bin_data["actual_qty"] == 60
