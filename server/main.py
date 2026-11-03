import math
import threading
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel, Field
from mock_data import inventory_items, orders, demand_forecasts, backlog_items, spending_summary, monthly_spending, category_spending, recent_transactions, purchase_orders

app = FastAPI(title="Factory Inventory Management System")

# Quarter mapping for date filtering
QUARTER_MAP = {
    'Q1-2025': ['2025-01', '2025-02', '2025-03'],
    'Q2-2025': ['2025-04', '2025-05', '2025-06'],
    'Q3-2025': ['2025-07', '2025-08', '2025-09'],
    'Q4-2025': ['2025-10', '2025-11', '2025-12']
}

def filter_by_month(items: list, month: Optional[str]) -> list:
    """Filter items by month/quarter based on order_date field"""
    if not month or month == 'all':
        return items

    if month.startswith('Q'):
        # Handle quarters
        if month in QUARTER_MAP:
            months = QUARTER_MAP[month]
            return [item for item in items if any(m in item.get('order_date', '') for m in months)]
    else:
        # Direct month match
        return [item for item in items if month in item.get('order_date', '')]

    return items

def apply_filters(items: list, warehouse: Optional[str] = None, category: Optional[str] = None,
                 status: Optional[str] = None) -> list:
    """Apply common filters to a list of items"""
    filtered = items

    if warehouse and warehouse != 'all':
        filtered = [item for item in filtered if item.get('warehouse') == warehouse]

    if category and category != 'all':
        filtered = [item for item in filtered if item.get('category', '').lower() == category.lower()]

    if status and status != 'all':
        filtered = [item for item in filtered if item.get('status', '').lower() == status.lower()]

    return filtered

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class InventoryItem(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    warehouse: str
    quantity_on_hand: int
    reorder_point: int
    unit_cost: float
    location: str
    last_updated: str

class Order(BaseModel):
    id: str
    order_number: str
    customer: str
    items: List[dict]
    status: str
    order_date: str
    expected_delivery: str
    total_value: float
    actual_delivery: Optional[str] = None
    warehouse: Optional[str] = None
    category: Optional[str] = None

class DemandForecast(BaseModel):
    id: str
    item_sku: str
    item_name: str
    current_demand: int
    forecasted_demand: int
    trend: str
    period: str
    unit_cost: float
    lead_time_days: int

class BacklogItem(BaseModel):
    id: str
    order_id: str
    item_sku: str
    item_name: str
    quantity_needed: int
    quantity_available: int
    days_delayed: int
    priority: str
    has_purchase_order: Optional[bool] = False

class PurchaseOrder(BaseModel):
    id: str
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    status: str
    created_date: str
    notes: Optional[str] = None

class CreatePurchaseOrderRequest(BaseModel):
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    notes: Optional[str] = None

class RestockRecommendation(BaseModel):
    sku: str
    name: str
    trend: str
    forecasted_demand: int
    unit_cost: float
    lead_time_days: int
    recommended_qty: int
    line_cost: float
    partial: bool

class RestockRecommendationResponse(BaseModel):
    budget: float
    total_cost: float
    remaining_budget: float
    max_cost: float
    items: List[RestockRecommendation]

class RestockOrderItem(BaseModel):
    sku: str
    quantity: int

class CreateRestockOrderRequest(BaseModel):
    items: List[RestockOrderItem] = Field(min_length=1)
    # Checked in the handler, not via Field constraints: a 422 echoes the rejected input,
    # and NaN/Infinity can't be serialized to JSON, which turns the error into a 500.
    budget: float

class RestockOrderLine(BaseModel):
    sku: str
    name: str
    quantity: int
    unit_cost: float
    line_cost: float

class RestockOrder(BaseModel):
    id: str
    order_number: str
    items: List[RestockOrderLine]
    total_cost: float
    submitted_date: str
    lead_time_days: int
    expected_delivery: str
    status: str

# Submitted restock orders live in memory only, like all other data in this demo:
# a server restart clears them.
restock_orders: list = []
# The POST handler is sync, so FastAPI runs it in a threadpool; the lock keeps
# sequence numbers unique when two orders arrive at once.
restock_orders_lock = threading.Lock()

TREND_PRIORITY = {'increasing': 0, 'stable': 1, 'decreasing': 2}

def to_cents(amount: float) -> int:
    """Convert dollars to integer cents, never rounding a budget up."""
    # round(..., 6) first absorbs binary noise (0.29 * 100 == 28.999999999999996);
    # floor then guarantees a budget like 100.007 can't buy 100.01 worth of goods.
    return math.floor(round(amount * 100, 6))

def build_restock_recommendations(forecasts: list, budget: float) -> dict:
    """Fit restock quantities from the demand forecast into a budget (greedy fill)."""
    # Quantity targets the full forecasted demand rather than a gap to a stock level,
    # because most forecast SKUs have no inventory record to compute a gap from.
    # Rising-demand items are funded first; ties go to the faster-growing item, then SKU
    # so the ordering is deterministic.
    def priority(f):
        growth = (f['forecasted_demand'] - f['current_demand']) / f['current_demand'] if f['current_demand'] else 0
        return (TREND_PRIORITY.get(f['trend'], len(TREND_PRIORITY)), -growth, f['item_sku'])

    # All budget arithmetic is in integer cents: with floats, a budget exactly equal to
    # the cost of the items (e.g. the slider at max_cost) could fall short by 1e-12 and
    # turn the last item into a spurious partial line.
    max_cost_cents = sum(f['forecasted_demand'] * to_cents(f['unit_cost']) for f in forecasts)
    budget_cents = to_cents(budget)
    remaining = budget_cents
    items = []
    for f in sorted(forecasts, key=priority):
        target = f['forecasted_demand']
        unit_cents = to_cents(f['unit_cost'])
        fits = target * unit_cents <= remaining
        # Strict priority: the first item that doesn't fully fit gets whatever whole units
        # the leftover buys, and filling stops there. Skipping ahead to cheaper, lower-priority
        # items would spend budget on demand we ranked as less urgent.
        qty = target if fits else remaining // unit_cents
        if qty > 0:
            line_cents = qty * unit_cents
            remaining -= line_cents
            items.append({
                'sku': f['item_sku'],
                'name': f['item_name'],
                'trend': f['trend'],
                'forecasted_demand': target,
                'unit_cost': f['unit_cost'],
                'lead_time_days': f['lead_time_days'],
                'recommended_qty': qty,
                'line_cost': line_cents / 100,
                'partial': qty < target,
            })
        if not fits:
            break

    total_cents = budget_cents - remaining
    return {
        'budget': budget,
        'total_cost': total_cents / 100,
        'remaining_budget': remaining / 100,
        'max_cost': max_cost_cents / 100,
        'items': items,
    }

# API endpoints
@app.get("/")
def root():
    return {"message": "Factory Inventory Management System API", "version": "1.0.0"}

@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Get all inventory items with optional filtering"""
    return apply_filters(inventory_items, warehouse, category)

@app.get("/api/inventory/{item_id}", response_model=InventoryItem)
def get_inventory_item(item_id: str):
    """Get a specific inventory item"""
    item = next((item for item in inventory_items if item["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/api/orders", response_model=List[Order])
def get_orders(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get all orders with optional filtering"""
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)
    return filtered_orders

@app.get("/api/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    """Get a specific order"""
    order = next((order for order in orders if order["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/api/demand", response_model=List[DemandForecast])
def get_demand_forecasts():
    """Get demand forecasts"""
    return demand_forecasts

@app.get("/api/backlog", response_model=List[BacklogItem])
def get_backlog():
    """Get backlog items with purchase order status"""
    # Add has_purchase_order flag to each backlog item
    result = []
    for item in backlog_items:
        item_dict = dict(item)
        # Check if this backlog item has a purchase order
        has_po = any(po["backlog_item_id"] == item["id"] for po in purchase_orders)
        item_dict["has_purchase_order"] = has_po
        result.append(item_dict)
    return result

@app.get("/api/dashboard/summary")
def get_dashboard_summary(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get summary statistics for dashboard with optional filtering"""
    # Filter inventory
    filtered_inventory = apply_filters(inventory_items, warehouse, category)

    # Filter orders
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    total_inventory_value = sum(item["quantity_on_hand"] * item["unit_cost"] for item in filtered_inventory)
    low_stock_items = len([item for item in filtered_inventory if item["quantity_on_hand"] <= item["reorder_point"]])
    pending_orders = len([order for order in filtered_orders if order["status"] in ["Processing", "Backordered"]])
    total_backlog_items = len(backlog_items)

    return {
        "total_inventory_value": round(total_inventory_value, 2),
        "low_stock_items": low_stock_items,
        "pending_orders": pending_orders,
        "total_backlog_items": total_backlog_items,
        "total_orders_value": sum(order["total_value"] for order in filtered_orders)
    }

@app.get("/api/spending/summary")
def get_spending_summary():
    """Get spending summary statistics"""
    return spending_summary

@app.get("/api/spending/monthly")
def get_monthly_spending():
    """Get monthly spending breakdown"""
    return monthly_spending

@app.get("/api/spending/categories")
def get_category_spending():
    """Get spending by category"""
    return category_spending

@app.get("/api/spending/transactions")
def get_recent_transactions():
    """Get recent transactions"""
    return recent_transactions

@app.get("/api/reports/quarterly")
def get_quarterly_reports(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get quarterly performance reports, honoring the same filters as /api/orders"""
    # Filter first, then aggregate: the report must describe exactly the orders the
    # global filter bar selects, so the numbers match the Orders and Dashboard pages.
    filtered_orders = filter_by_month(apply_filters(orders, warehouse, category, status), month)
    quarters = {}

    for order in filtered_orders:
        order_date = order.get('order_date', '')
        # Determine quarter
        if '2025-01' in order_date or '2025-02' in order_date or '2025-03' in order_date:
            quarter = 'Q1-2025'
        elif '2025-04' in order_date or '2025-05' in order_date or '2025-06' in order_date:
            quarter = 'Q2-2025'
        elif '2025-07' in order_date or '2025-08' in order_date or '2025-09' in order_date:
            quarter = 'Q3-2025'
        elif '2025-10' in order_date or '2025-11' in order_date or '2025-12' in order_date:
            quarter = 'Q4-2025'
        else:
            continue

        if quarter not in quarters:
            quarters[quarter] = {
                'quarter': quarter,
                'total_orders': 0,
                'total_revenue': 0,
                'delivered_orders': 0,
                'avg_order_value': 0
            }

        quarters[quarter]['total_orders'] += 1
        quarters[quarter]['total_revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            quarters[quarter]['delivered_orders'] += 1

    # Calculate averages and fulfillment rate
    result = []
    for q, data in quarters.items():
        if data['total_orders'] > 0:
            data['avg_order_value'] = round(data['total_revenue'] / data['total_orders'], 2)
            data['fulfillment_rate'] = round((data['delivered_orders'] / data['total_orders']) * 100, 1)
        result.append(data)

    # Sort by quarter
    result.sort(key=lambda x: x['quarter'])
    return result

@app.get("/api/reports/monthly-trends")
def get_monthly_trends(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get month-over-month trends, honoring the same filters as /api/orders"""
    filtered_orders = filter_by_month(apply_filters(orders, warehouse, category, status), month)
    months = {}

    for order in filtered_orders:
        order_date = order.get('order_date', '')
        if not order_date:
            continue

        # Extract month (format: YYYY-MM-DD)
        month = order_date[:7]  # Gets YYYY-MM

        if month not in months:
            months[month] = {
                'month': month,
                'order_count': 0,
                'revenue': 0,
                'delivered_count': 0
            }

        months[month]['order_count'] += 1
        months[month]['revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            months[month]['delivered_count'] += 1

    # Convert to list and sort
    result = list(months.values())
    result.sort(key=lambda x: x['month'])
    return result

@app.get("/api/restocking/recommendations", response_model=RestockRecommendationResponse)
def get_restock_recommendations(budget: float = Query(..., ge=0, allow_inf_nan=False)):
    """Recommend restock quantities from the demand forecast that fit within the budget"""
    return build_restock_recommendations(demand_forecasts, budget)

@app.post("/api/restocking/orders", response_model=RestockOrder, status_code=201)
def create_restock_order(request: CreateRestockOrderRequest):
    """Submit a restock order. Prices and lead times come from server data, not the client."""
    # NaN would make every "total > budget" comparison False and silently skip the check.
    if not math.isfinite(request.budget) or request.budget < 0:
        raise HTTPException(status_code=400, detail="Budget must be a finite, non-negative number")
    forecasts_by_sku = {f['item_sku']: f for f in demand_forecasts}
    seen = set()
    lines = []
    for item in request.items:
        if item.sku not in forecasts_by_sku:
            raise HTTPException(status_code=400, detail=f"Unknown SKU: {item.sku}")
        if item.sku in seen:
            raise HTTPException(status_code=400, detail=f"Duplicate SKU: {item.sku}")
        if item.quantity <= 0:
            raise HTTPException(status_code=400, detail=f"Quantity must be positive for {item.sku}")
        seen.add(item.sku)
        f = forecasts_by_sku[item.sku]
        lines.append({
            'sku': item.sku,
            'name': f['item_name'],
            'quantity': item.quantity,
            'unit_cost': f['unit_cost'],
            'line_cents': item.quantity * to_cents(f['unit_cost']),
            'lead_time_days': f['lead_time_days'],
        })

    # Same integer-cents comparison as the recommendations, so an order built from
    # a recommendation at budget X is always accepted at budget X.
    total_cents = sum(l['line_cents'] for l in lines)
    total_cost = total_cents / 100
    if total_cents > to_cents(request.budget):
        raise HTTPException(
            status_code=400,
            detail=f"Order total {total_cost:.2f} exceeds budget {request.budget:.2f}"
        )

    # The order ships complete, so it arrives when its slowest item does.
    lead_time = max(l.pop('lead_time_days') for l in lines)
    for l in lines:
        l['line_cost'] = l.pop('line_cents') / 100
    submitted = datetime.now().replace(microsecond=0)
    with restock_orders_lock:
        sequence = len(restock_orders) + 1
        order = {
            'id': str(sequence),
            'order_number': f"RST-{sequence:04d}",
            'items': lines,
            'total_cost': total_cost,
            'submitted_date': submitted.isoformat(),
            'lead_time_days': lead_time,
            'expected_delivery': (submitted + timedelta(days=lead_time)).isoformat(),
            'status': 'Submitted',
        }
        restock_orders.append(order)
    return order

@app.get("/api/restocking/orders", response_model=List[RestockOrder])
def get_restock_orders():
    """Get submitted restock orders, newest first"""
    return list(reversed(restock_orders))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
