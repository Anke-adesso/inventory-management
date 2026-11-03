"""
Tests for restocking API endpoints (recommendations and restock orders).
"""
from datetime import datetime, timedelta

import pytest

import main


@pytest.fixture(autouse=True)
def reset_restock_orders():
    """Submitted restock orders are module-level state; isolate each test."""
    main.restock_orders.clear()
    yield
    main.restock_orders.clear()


@pytest.fixture
def forecasts(client):
    """Demand forecasts keyed by SKU."""
    response = client.get("/api/demand")
    return {f["item_sku"]: f for f in response.json()}


class TestRestockRecommendations:
    """Test suite for GET /api/restocking/recommendations."""

    def test_get_recommendations_structure(self, client):
        """Test the response structure and field types."""
        response = client.get("/api/restocking/recommendations?budget=30000")
        assert response.status_code == 200

        data = response.json()
        for field in ["budget", "total_cost", "remaining_budget", "max_cost", "items"]:
            assert field in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) > 0

        for item in data["items"]:
            for field in ["sku", "name", "trend", "forecasted_demand", "unit_cost",
                          "lead_time_days", "recommended_qty", "line_cost", "partial"]:
                assert field in item
            assert isinstance(item["recommended_qty"], int)
            assert item["recommended_qty"] > 0
            assert isinstance(item["partial"], bool)

    def test_zero_budget_returns_no_items(self, client, forecasts):
        """Test that budget 0 yields no items but still reports max_cost."""
        response = client.get("/api/restocking/recommendations?budget=0")
        assert response.status_code == 200

        data = response.json()
        assert data["items"] == []
        assert data["total_cost"] == 0

        expected_max = sum(f["forecasted_demand"] * f["unit_cost"] for f in forecasts.values())
        assert abs(data["max_cost"] - expected_max) < 0.01

    def test_large_budget_covers_all_items(self, client, forecasts):
        """Test that a budget above max_cost fully covers every forecast."""
        response = client.get("/api/restocking/recommendations?budget=10000000")
        data = response.json()

        assert len(data["items"]) == len(forecasts)
        for item in data["items"]:
            assert item["partial"] is False
            assert item["recommended_qty"] == item["forecasted_demand"]
        assert abs(data["total_cost"] - data["max_cost"]) < 0.01

    @pytest.mark.parametrize("budget", [100, 5000, 30000, 60000, 111000])
    def test_total_cost_within_budget(self, client, budget):
        """Test that recommendations never exceed the budget."""
        data = client.get(f"/api/restocking/recommendations?budget={budget}").json()

        assert data["total_cost"] <= budget
        assert abs(data["remaining_budget"] - (budget - data["total_cost"])) < 0.01
        line_sum = sum(i["line_cost"] for i in data["items"])
        assert abs(line_sum - data["total_cost"]) < 0.01

    def test_line_cost_calculation(self, client):
        """Test that line_cost equals quantity times unit_cost."""
        data = client.get("/api/restocking/recommendations?budget=60000").json()
        for item in data["items"]:
            assert abs(item["line_cost"] - item["recommended_qty"] * item["unit_cost"]) < 0.01

    def test_only_last_item_can_be_partial(self, client):
        """Test that at most one item is partial and it is the last one."""
        data = client.get("/api/restocking/recommendations?budget=30000").json()
        items = data["items"]

        partial_indexes = [i for i, item in enumerate(items) if item["partial"]]
        assert len(partial_indexes) <= 1
        if partial_indexes:
            assert partial_indexes[0] == len(items) - 1

    def test_increasing_trend_prioritized(self, client):
        """Test that increasing-trend items come before stable and decreasing ones."""
        data = client.get("/api/restocking/recommendations?budget=10000000").json()
        rank = {"increasing": 0, "stable": 1, "decreasing": 2}
        ranks = [rank[item["trend"]] for item in data["items"]]
        assert ranks == sorted(ranks)

    def test_highest_growth_item_funded_first(self, client, forecasts):
        """Test that within the top trend, the fastest-growing item is first."""
        increasing = [f for f in forecasts.values() if f["trend"] == "increasing"]
        fastest = max(
            increasing,
            key=lambda f: (f["forecasted_demand"] - f["current_demand"]) / f["current_demand"],
        )
        data = client.get("/api/restocking/recommendations?budget=1000").json()
        assert data["items"][0]["sku"] == fastest["item_sku"]

    def test_negative_budget_rejected(self, client):
        """Test that a negative budget is a validation error."""
        response = client.get("/api/restocking/recommendations?budget=-1")
        assert response.status_code == 422

    def test_missing_budget_rejected(self, client):
        """Test that budget is required."""
        response = client.get("/api/restocking/recommendations")
        assert response.status_code == 422


class TestRestockOrders:
    """Test suite for POST/GET /api/restocking/orders."""

    def test_get_restock_orders_initially_empty(self, client):
        """Test that no restock orders exist before any are submitted."""
        response = client.get("/api/restocking/orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_restock_order(self, client, forecasts):
        """Test submitting a valid restock order."""
        payload = {
            "items": [{"sku": "WDG-001", "quantity": 100}, {"sku": "GSK-203", "quantity": 50}],
            "budget": 10000,
        }
        response = client.post("/api/restocking/orders", json=payload)
        assert response.status_code == 201

        order = response.json()
        assert order["order_number"] == "RST-0001"
        assert order["status"] == "Submitted"
        assert len(order["items"]) == 2

        expected_total = 100 * forecasts["WDG-001"]["unit_cost"] + 50 * forecasts["GSK-203"]["unit_cost"]
        assert abs(order["total_cost"] - expected_total) < 0.01

    def test_restock_order_uses_server_prices(self, client, forecasts):
        """Test that unit costs come from server data, not the request."""
        payload = {
            "items": [{"sku": "MTR-304", "quantity": 1, "unit_cost": 0.01}],
            "budget": 10000,
        }
        order = client.post("/api/restocking/orders", json=payload).json()
        assert order["items"][0]["unit_cost"] == forecasts["MTR-304"]["unit_cost"]

    def test_restock_order_lead_time_is_max(self, client, forecasts):
        """Test that order lead time is the slowest item's lead time."""
        skus = ["GSK-203", "MTR-304", "WDG-001"]
        payload = {"items": [{"sku": s, "quantity": 1} for s in skus], "budget": 10000}
        order = client.post("/api/restocking/orders", json=payload).json()

        expected = max(forecasts[s]["lead_time_days"] for s in skus)
        assert order["lead_time_days"] == expected

        submitted = datetime.fromisoformat(order["submitted_date"])
        delivery = datetime.fromisoformat(order["expected_delivery"])
        assert delivery - submitted == timedelta(days=expected)

    def test_restock_order_appears_in_list(self, client):
        """Test that submitted orders are returned newest first."""
        for qty in (1, 2):
            client.post("/api/restocking/orders",
                        json={"items": [{"sku": "WDG-001", "quantity": qty}], "budget": 1000})

        orders = client.get("/api/restocking/orders").json()
        assert [o["order_number"] for o in orders] == ["RST-0002", "RST-0001"]

    def test_restock_order_unknown_sku(self, client):
        """Test that an unknown SKU is rejected."""
        payload = {"items": [{"sku": "NOPE-999", "quantity": 1}], "budget": 1000}
        response = client.post("/api/restocking/orders", json=payload)
        assert response.status_code == 400
        assert "unknown sku" in response.json()["detail"].lower()

    @pytest.mark.parametrize("quantity", [0, -5])
    def test_restock_order_non_positive_quantity(self, client, quantity):
        """Test that zero or negative quantities are rejected."""
        payload = {"items": [{"sku": "WDG-001", "quantity": quantity}], "budget": 1000}
        assert client.post("/api/restocking/orders", json=payload).status_code == 400

    def test_restock_order_duplicate_sku(self, client):
        """Test that the same SKU twice is rejected."""
        payload = {
            "items": [{"sku": "WDG-001", "quantity": 1}, {"sku": "WDG-001", "quantity": 2}],
            "budget": 1000,
        }
        assert client.post("/api/restocking/orders", json=payload).status_code == 400

    def test_restock_order_over_budget(self, client):
        """Test that an order exceeding the budget is rejected and not stored."""
        payload = {"items": [{"sku": "MTR-304", "quantity": 10}], "budget": 100}
        response = client.post("/api/restocking/orders", json=payload)
        assert response.status_code == 400
        assert "exceeds budget" in response.json()["detail"].lower()
        assert client.get("/api/restocking/orders").json() == []

    def test_restock_order_empty_items(self, client):
        """Test that an order with no items is a validation error."""
        response = client.post("/api/restocking/orders", json={"items": [], "budget": 1000})
        assert response.status_code == 422

    def test_restock_order_does_not_affect_sales_orders(self, client):
        """Test that restock orders stay out of sales orders and dashboard KPIs."""
        orders_before = len(client.get("/api/orders").json())
        summary_before = client.get("/api/dashboard/summary").json()

        client.post("/api/restocking/orders",
                    json={"items": [{"sku": "WDG-001", "quantity": 10}], "budget": 1000})

        assert len(client.get("/api/orders").json()) == orders_before
        assert client.get("/api/dashboard/summary").json() == summary_before


class TestRestockEdgeCases:
    """Regression tests for budget arithmetic and input validation edge cases."""

    def test_budget_equal_to_max_cost_covers_everything(self, client):
        """Test that a budget exactly equal to max_cost yields no partial line."""
        max_cost = client.get("/api/restocking/recommendations?budget=0").json()["max_cost"]
        data = client.get(f"/api/restocking/recommendations?budget={max_cost}").json()

        assert all(not item["partial"] for item in data["items"])
        assert data["total_cost"] == max_cost
        assert data["remaining_budget"] == 0

    def test_budget_equal_to_prefix_cost_has_no_partial(self, client):
        """Test exact-boundary budgets for every priority prefix."""
        full = client.get("/api/restocking/recommendations?budget=10000000").json()["items"]
        cents = 0
        for n, item in enumerate(full, start=1):
            cents += round(item["line_cost"] * 100)
            data = client.get(f"/api/restocking/recommendations?budget={cents / 100}").json()
            assert len(data["items"]) == n
            assert data["items"][-1]["partial"] is False

    def test_exact_partial_quantity(self, client, forecasts):
        """Test the partial quantity is the floor of leftover budget / unit cost."""
        data = client.get("/api/restocking/recommendations?budget=30000").json()
        *full_items, last = data["items"]
        spent_cents = sum(round(i["line_cost"] * 100) for i in full_items)
        unit_cents = round(forecasts[last["sku"]]["unit_cost"] * 100)

        assert last["partial"] is True
        assert last["recommended_qty"] == (3000000 - spent_cents) // unit_cents

    def test_stable_items_ordered_by_growth(self, client):
        """Test that within the same trend, higher growth comes first."""
        items = client.get("/api/restocking/recommendations?budget=10000000").json()["items"]
        demand = {f["item_sku"]: f for f in client.get("/api/demand").json()}
        stable = [demand[i["sku"]] for i in items if i["trend"] == "stable"]
        growth = [(f["forecasted_demand"] - f["current_demand"]) / f["current_demand"] for f in stable]
        assert growth == sorted(growth, reverse=True)

    @pytest.mark.parametrize("budget", ["inf", "nan", "-inf"])
    def test_non_finite_budget_rejected_on_recommendations(self, client, budget):
        """Test that non-finite budgets are validation errors."""
        response = client.get(f"/api/restocking/recommendations?budget={budget}")
        assert response.status_code == 422

    @pytest.mark.parametrize("budget", ["NaN", "Infinity", "-1"])
    def test_invalid_budget_rejected_on_order(self, client, budget):
        """Test that NaN/Infinity/negative budgets can't bypass the over-budget check."""
        body = '{"items": [{"sku": "MTR-304", "quantity": 1000}], "budget": %s}' % budget
        response = client.post("/api/restocking/orders", content=body,
                               headers={"content-type": "application/json"})
        assert response.status_code == 400
        assert client.get("/api/restocking/orders").json() == []

    def test_order_at_exact_budget_accepted(self, client, forecasts):
        """Test that an order costing exactly the budget is accepted."""
        cost = 450 * forecasts["WDG-001"]["unit_cost"]
        payload = {"items": [{"sku": "WDG-001", "quantity": 450}], "budget": cost}
        assert client.post("/api/restocking/orders", json=payload).status_code == 201

    def test_order_one_cent_over_budget_rejected(self, client, forecasts):
        """Test that an order one cent over the budget is rejected."""
        cents = 450 * round(forecasts["WDG-001"]["unit_cost"] * 100)
        payload = {"items": [{"sku": "WDG-001", "quantity": 450}], "budget": (cents - 1) / 100}
        assert client.post("/api/restocking/orders", json=payload).status_code == 400

    def test_recommendation_round_trips_into_order(self, client):
        """Test that ordering exactly what was recommended is accepted at the same budget."""
        for budget in (1500, 30000, 56000, 111381.48):
            rec = client.get(f"/api/restocking/recommendations?budget={budget}").json()
            payload = {"items": [{"sku": i["sku"], "quantity": i["recommended_qty"]} for i in rec["items"]],
                       "budget": budget}
            response = client.post("/api/restocking/orders", json=payload)
            assert response.status_code == 201
            assert abs(response.json()["total_cost"] - rec["total_cost"]) < 0.001

    def test_zero_demand_item_does_not_stop_fill(self):
        """Test that a zero-demand forecast is skipped instead of ending the fill."""
        forecasts = [
            {"item_sku": "A", "item_name": "A", "current_demand": 10, "forecasted_demand": 0,
             "trend": "increasing", "unit_cost": 1.0, "lead_time_days": 1},
            {"item_sku": "B", "item_name": "B", "current_demand": 10, "forecasted_demand": 10,
             "trend": "stable", "unit_cost": 1.0, "lead_time_days": 1},
        ]
        result = main.build_restock_recommendations(forecasts, 100)
        assert [i["sku"] for i in result["items"]] == ["B"]
