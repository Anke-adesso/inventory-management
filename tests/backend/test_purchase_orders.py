"""
Tests for purchase order API endpoints.
"""
import math

import pytest

import main


@pytest.fixture(autouse=True)
def reset_purchase_orders():
    """Purchase orders live in memory; isolate every test."""
    main.purchase_orders.clear()
    yield
    main.purchase_orders.clear()


@pytest.fixture
def po_payload():
    """Valid create request for backlog item 1."""
    return {
        "backlog_item_id": "1",
        "supplier_name": "Acme Filters GmbH",
        "quantity": 350,
        "unit_cost": 12.5,
        "expected_delivery_date": "2025-11-15",
        "notes": "Rush order",
    }


class TestPurchaseOrderEndpoints:
    """Test suite for purchase order endpoints."""

    def test_create_purchase_order(self, client, po_payload):
        """Test creating a purchase order for a backlog item."""
        response = client.post("/api/purchase-orders", json=po_payload)
        assert response.status_code == 201

        po = response.json()
        assert po["id"] == "PO-0001"
        assert po["backlog_item_id"] == "1"
        assert po["supplier_name"] == "Acme Filters GmbH"
        assert po["quantity"] == 350
        assert po["unit_cost"] == 12.5
        assert po["expected_delivery_date"] == "2025-11-15"
        assert po["status"] == "pending"
        assert po["notes"] == "Rush order"
        assert len(po["created_date"]) == 10  # YYYY-MM-DD

    def test_get_purchase_order_by_backlog_item(self, client, po_payload):
        """Test fetching the PO that belongs to a backlog item."""
        created = client.post("/api/purchase-orders", json=po_payload).json()

        response = client.get("/api/purchase-orders/1")
        assert response.status_code == 200
        assert response.json() == created

    def test_get_nonexistent_purchase_order(self, client):
        """Test fetching a PO for a backlog item that has none."""
        response = client.get("/api/purchase-orders/1")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_backlog_reflects_purchase_order(self, client, po_payload):
        """Test that /api/backlog links the new PO to its backlog item."""
        before = {i["id"]: i for i in client.get("/api/backlog").json()}
        assert before["1"]["has_purchase_order"] is False
        assert before["1"]["purchase_order_id"] is None

        po = client.post("/api/purchase-orders", json=po_payload).json()

        after = {i["id"]: i for i in client.get("/api/backlog").json()}
        assert after["1"]["has_purchase_order"] is True
        assert after["1"]["purchase_order_id"] == po["id"]
        assert after["2"]["purchase_order_id"] is None

    def test_duplicate_purchase_order_rejected(self, client, po_payload):
        """Test that a backlog item can only get one purchase order."""
        assert client.post("/api/purchase-orders", json=po_payload).status_code == 201
        response = client.post("/api/purchase-orders", json=po_payload)
        assert response.status_code == 409
        assert len(main.purchase_orders) == 1

    def test_unknown_backlog_item(self, client, po_payload):
        """Test creating a PO for a backlog item that doesn't exist."""
        po_payload["backlog_item_id"] = "nonexistent-999"
        response = client.post("/api/purchase-orders", json=po_payload)
        assert response.status_code == 404

    @pytest.mark.parametrize("field,value", [
        ("supplier_name", "   "),
        ("quantity", 0),
        ("quantity", -5),
        ("unit_cost", 0),
        ("unit_cost", -1.5),
        ("expected_delivery_date", "15.11.2025"),
        ("expected_delivery_date", "2025-02-30"),
    ])
    def test_invalid_input_rejected(self, client, po_payload, field, value):
        """Test that invalid field values return 400 and create nothing."""
        po_payload[field] = value
        response = client.post("/api/purchase-orders", json=po_payload)
        assert response.status_code == 400
        assert "detail" in response.json()
        assert main.purchase_orders == []

    def test_non_finite_unit_cost_rejected(self, client, po_payload):
        """Test that NaN unit cost is rejected rather than stored."""
        # Bypass the JSON encoder, which refuses NaN, to send the literal token.
        body = (
            '{"backlog_item_id": "1", "supplier_name": "X", "quantity": 1, '
            '"unit_cost": NaN, "expected_delivery_date": "2025-11-15"}'
        )
        response = client.post(
            "/api/purchase-orders", content=body,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code in (400, 422)
        assert main.purchase_orders == []

    def test_missing_field_returns_422(self, client, po_payload):
        """Test that a missing required field fails validation."""
        del po_payload["supplier_name"]
        response = client.post("/api/purchase-orders", json=po_payload)
        assert response.status_code == 422

    def test_notes_optional_and_blank_becomes_null(self, client, po_payload):
        """Test that blank notes are stored as null."""
        po_payload["notes"] = "  "
        po = client.post("/api/purchase-orders", json=po_payload).json()
        assert po["notes"] is None
