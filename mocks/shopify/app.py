"""
Mock Shopify API for AGNTCY Multi-Agent Customer Service Platform
Phase 1-3: Local development mock service

This mock API simulates Shopify's REST Admin API endpoints needed for:
- Product catalog queries
- Inventory management
- Order status checks
- Cart operations

All responses are static JSON fixtures for predictable testing.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Initialize FastAPI app
app = FastAPI(
    title="Mock Shopify API",
    description="Mock Shopify REST Admin API for development and testing",
    version="1.0.0"
)

# Data directory for JSON fixtures
DATA_DIR = Path("/app/data") if os.path.exists("/app/data") else Path("./data")


def load_fixture(filename: str) -> Dict:
    """Load JSON fixture from data directory."""
    filepath = DATA_DIR / filename
    if not filepath.exists():
        return {"error": f"Fixture {filename} not found"}

    with open(filepath, "r") as f:
        return json.load(f)


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """API root - basic info."""
    return {
        "service": "Mock Shopify API",
        "version": "1.0.0",
        "endpoints": [
            "/admin/api/2024-01/products.json",
            "/admin/api/2024-01/products/{product_id}.json",
            "/admin/api/2024-01/inventory_levels.json",
            "/admin/api/2024-01/orders.json",
            "/admin/api/2024-01/orders/{order_id}.json",
            "/admin/api/2024-01/checkouts.json"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mock-shopify"}


@app.get("/admin/api/2024-01/products.json")
async def get_products(
    limit: int = Query(50, ge=1, le=250),
    page_info: Optional[str] = None,
    x_shopify_access_token: str = Header(None)
):
    """
    Get products list.
    Mock response with sample e-commerce products.
    """
    products_data = load_fixture("products.json")

    # Simulate pagination
    all_products = products_data.get("products", [])
    return {
        "products": all_products[:limit]
    }


@app.get("/admin/api/2024-01/products/{product_id}.json")
async def get_product(
    product_id: str,
    x_shopify_access_token: str = Header(None)
):
    """Get single product by ID (supports both string and numeric IDs)."""
    products_data = load_fixture("products.json")
    products = products_data.get("products", [])

    for product in products:
        # Support both string IDs (like "PROD-001") and numeric IDs
        if str(product.get("id")) == str(product_id):
            return {"product": product}

    raise HTTPException(status_code=404, detail="Product not found")


@app.get("/admin/api/2024-01/inventory_levels.json")
async def get_inventory_levels(
    location_ids: Optional[str] = Query(None),
    inventory_item_ids: Optional[str] = Query(None),
    x_shopify_access_token: str = Header(None)
):
    """
    Get inventory levels.
    Returns stock quantities for products.
    """
    inventory_data = load_fixture("inventory.json")
    return inventory_data


@app.get("/admin/api/2024-01/orders.json")
async def get_orders(
    status: Optional[str] = Query("any"),
    customer_email: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=250),
    x_shopify_access_token: str = Header(None)
):
    """
    Get orders list with optional filtering by customer email.
    Mock response with sample customer orders.
    """
    orders_data = load_fixture("orders.json")
    all_orders = orders_data.get("orders", [])

    # Filter by customer email if provided
    if customer_email:
        filtered_orders = [
            order for order in all_orders
            if order.get("customer_email", "").lower() == customer_email.lower()
        ]
        return {"orders": filtered_orders[:limit]}

    # Filter by status if not "any"
    if status and status != "any":
        filtered_orders = [
            order for order in all_orders
            if order.get("status", "").lower() == status.lower()
        ]
        return {"orders": filtered_orders[:limit]}

    return {"orders": all_orders[:limit]}


@app.get("/admin/api/2024-01/orders/{order_id}.json")
async def get_order(
    order_id: str,
    x_shopify_access_token: str = Header(None)
):
    """Get single order by ID or order number (supports formats like 'ORD-10234' or '10234')."""
    orders_data = load_fixture("orders.json")
    orders = orders_data.get("orders", [])

    for order in orders:
        # Match by order_id, order_number, or just the numeric part
        if (str(order.get("order_id")) == str(order_id) or
            str(order.get("order_number")) == str(order_id) or
            str(order.get("order_id")).replace("ORD-", "") == str(order_id)):
            return {"order": order}

    raise HTTPException(status_code=404, detail="Order not found")


@app.get("/admin/api/2024-01/checkouts.json")
async def get_checkouts(
    x_shopify_access_token: str = Header(None)
):
    """
    Get abandoned checkouts (carts).
    Important for cart abandonment KPI tracking.
    """
    checkouts_data = load_fixture("checkouts.json")
    return checkouts_data


@app.post("/admin/api/2024-01/checkouts.json")
async def create_checkout(
    x_shopify_access_token: str = Header(None)
):
    """
    Create new checkout.
    Mock response for cart creation.
    """
    return {
        "checkout": {
            "id": 123456789,
            "token": "mock-checkout-token",
            "created_at": "2024-01-18T12:00:00Z",
            "status": "open"
        }
    }


# Webhook simulation endpoint (for future Phase 2/3 testing)
@app.post("/webhooks/orders/create")
async def webhook_order_created():
    """Simulate Shopify webhook for order creation."""
    return {"received": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
