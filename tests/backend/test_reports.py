"""
Tests for reports API endpoints.
"""
import pytest


REPORT_ENDPOINTS = ["/api/reports/quarterly", "/api/reports/monthly-trends"]


class TestReportsEndpoints:
    """Test suite for reports endpoints, including global filter support."""

    def test_get_quarterly_reports(self, client):
        """Test getting quarterly reports without filters."""
        response = client.get("/api/reports/quarterly")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        for quarter in data:
            for field in ["quarter", "total_orders", "total_revenue",
                          "avg_order_value", "fulfillment_rate"]:
                assert field in quarter

    def test_get_monthly_trends(self, client):
        """Test getting monthly trends without filters."""
        response = client.get("/api/reports/monthly-trends")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        for month in data:
            for field in ["month", "order_count", "revenue", "delivered_count"]:
                assert field in month

    @pytest.mark.parametrize("endpoint", REPORT_ENDPOINTS)
    def test_all_filter_equals_unfiltered(self, client, endpoint):
        """Test that filter value 'all' is treated as no filter."""
        unfiltered = client.get(endpoint).json()
        response = client.get(
            f"{endpoint}?warehouse=all&category=all&status=all&month=all"
        )
        assert response.status_code == 200
        assert response.json() == unfiltered

    def test_monthly_trends_by_warehouse_matches_orders(self, client):
        """Test that warehouse-filtered trends aggregate exactly the filtered orders."""
        orders = client.get("/api/orders?warehouse=Tokyo").json()
        trends = client.get("/api/reports/monthly-trends?warehouse=Tokyo").json()

        assert sum(m["order_count"] for m in trends) == len(orders)
        assert abs(
            sum(m["revenue"] for m in trends) - sum(o["total_value"] for o in orders)
        ) < 0.01

    def test_quarterly_by_category_matches_orders(self, client):
        """Test that category-filtered quarterly totals match the filtered orders."""
        orders = client.get("/api/orders?category=Sensors").json()
        quarters = client.get("/api/reports/quarterly?category=Sensors").json()

        assert sum(q["total_orders"] for q in quarters) == len(orders)
        assert abs(
            sum(q["total_revenue"] for q in quarters) - sum(o["total_value"] for o in orders)
        ) < 0.01

    def test_quarterly_by_status_delivered(self, client):
        """Test that a Delivered status filter yields 100% fulfillment per quarter."""
        quarters = client.get("/api/reports/quarterly?status=Delivered").json()
        assert len(quarters) > 0
        for q in quarters:
            assert q["fulfillment_rate"] == 100.0

    def test_monthly_trends_by_month(self, client):
        """Test that a month filter returns only that month."""
        data = client.get("/api/reports/monthly-trends?month=2025-03").json()
        assert len(data) == 1
        assert data[0]["month"] == "2025-03"

    def test_quarterly_by_quarter(self, client):
        """Test that a quarter filter returns only that quarter."""
        data = client.get("/api/reports/quarterly?month=Q2-2025").json()
        assert [q["quarter"] for q in data] == ["Q2-2025"]

    def test_reports_multiple_filters_match_orders(self, client):
        """Test combined filters aggregate the same orders as /api/orders."""
        query = "warehouse=London&category=Actuators&status=Shipped&month=Q3-2025"
        orders = client.get(f"/api/orders?{query}").json()
        quarters = client.get(f"/api/reports/quarterly?{query}").json()
        trends = client.get(f"/api/reports/monthly-trends?{query}").json()

        assert sum(q["total_orders"] for q in quarters) == len(orders)
        assert sum(m["order_count"] for m in trends) == len(orders)

    @pytest.mark.parametrize("endpoint", REPORT_ENDPOINTS)
    def test_reports_no_matches_returns_empty_list(self, client, endpoint):
        """Test that a filter matching nothing returns an empty list, not an error."""
        response = client.get(f"{endpoint}?warehouse=Nowhere")
        assert response.status_code == 200
        assert response.json() == []
