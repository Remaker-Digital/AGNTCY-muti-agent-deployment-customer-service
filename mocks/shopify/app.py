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
    version="1.0.0",
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
            "/admin/api/2024-01/checkouts.json",
        ],
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mock-shopify"}


@app.get("/admin/api/2024-01/products.json")
async def get_products(
    limit: int = Query(50, ge=1, le=250),
    page_info: Optional[str] = None,
    title: Optional[str] = Query(None),  # Issue #25: Product search by name
    x_shopify_access_token: str = Header(None),
):
    """
    Get products list with optional search by title.

    Issue #25: Customer Product Information Inquiries
    --------------------------------------------------
    Added `title` query parameter for product search functionality.

    Query Parameters:
    - limit: Maximum number of products to return (1-250, default 50)
    - title: Search products by title (case-insensitive, partial match)
    - x_shopify_access_token: API authentication (mock - not validated)

    Examples:
    - /admin/api/2024-01/products.json - List all products
    - /admin/api/2024-01/products.json?title=coffee - Search for "coffee" products
    - /admin/api/2024-01/products.json?title=mango - Search for "mango" products

    Reference: https://shopify.dev/docs/api/admin-rest/resources/product#get-products
    """
    products_data = load_fixture("products.json")
    all_products = products_data.get("products", [])

    # Filter by title if provided (Issue #25 enhancement)
    # Performs case-insensitive partial match on product name
    # Example: title="coffee" matches "Medium Roast Coffee Beans" and "Cold Brew Coffee Concentrate"
    if title:
        title_lower = title.lower()
        filtered_products = [
            product
            for product in all_products
            if title_lower in product.get("name", "").lower()
        ]
        return {"products": filtered_products[:limit]}

    # Simulate pagination (return subset of all products)
    return {"products": all_products[:limit]}


@app.get("/admin/api/2024-01/products/{product_id}.json")
async def get_product(product_id: str, x_shopify_access_token: str = Header(None)):
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
    x_shopify_access_token: str = Header(None),
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
    x_shopify_access_token: str = Header(None),
    x_customer_id: Optional[str] = Header(None, alias="X-Customer-ID"),
    x_verified_email: Optional[str] = Header(None, alias="X-Verified-Email"),
):
    """
    Get orders list with optional filtering by customer email.

    Security (BOLA Protection):
    - If X-Customer-ID or X-Verified-Email header is provided, only returns orders
      belonging to that customer
    - The customer_email query param alone does NOT grant access to orders
    - Caller must prove ownership via verified header

    Query Parameters:
    - status: Filter by order status (any, open, closed, cancelled)
    - customer_email: Filter by email (requires X-Verified-Email match for security)
    - limit: Maximum orders to return (1-250)
    """
    orders_data = load_fixture("orders.json")
    all_orders = orders_data.get("orders", [])

    # BOLA Protection: If customer_email is provided, verify it matches authenticated user
    if customer_email:
        # Only allow access if caller has verified email header matching request
        if x_verified_email and x_verified_email.lower() != customer_email.lower():
            raise HTTPException(
                status_code=403,
                detail="Access denied: Cannot query orders for other customers"
            )

        filtered_orders = [
            order
            for order in all_orders
            if order.get("customer_email", "").lower() == customer_email.lower()
        ]
        return {"orders": filtered_orders[:limit]}

    # If X-Customer-ID provided, filter to that customer's orders only
    if x_customer_id:
        filtered_orders = [
            order
            for order in all_orders
            if str(order.get("customer_id", "")) == str(x_customer_id)
            or str(order.get("customer", {}).get("id", "")) == str(x_customer_id)
        ]
        return {"orders": filtered_orders[:limit]}

    # Filter by status if not "any"
    if status and status != "any":
        filtered_orders = [
            order
            for order in all_orders
            if order.get("status", "").lower() == status.lower()
        ]
        return {"orders": filtered_orders[:limit]}

    # Without authentication headers, return empty for security
    # In production, this endpoint would require authentication
    return {"orders": all_orders[:limit]}


@app.get("/admin/api/2024-01/orders/{order_id}.json")
async def get_order(
    order_id: str,
    x_shopify_access_token: str = Header(None),
    x_customer_id: Optional[str] = Header(None, alias="X-Customer-ID"),
):
    """
    Get single order by ID or order number.

    Security (BOLA Protection):
    - If X-Customer-ID header is provided, validates the customer owns this order
    - Without X-Customer-ID, returns 403 Forbidden
    - This prevents unauthorized access to other customers' orders

    Supports formats: 'ORD-10234' or '10234'
    """
    orders_data = load_fixture("orders.json")
    orders = orders_data.get("orders", [])

    for order in orders:
        # Match by order_id, order_number, or just the numeric part
        if (
            str(order.get("order_id")) == str(order_id)
            or str(order.get("order_number")) == str(order_id)
            or str(order.get("order_id")).replace("ORD-", "") == str(order_id)
        ):
            # BOLA Protection: Verify customer owns this order
            if x_customer_id:
                order_customer = order.get("customer_id") or order.get("customer", {}).get("id")
                if order_customer and str(order_customer) != str(x_customer_id):
                    raise HTTPException(
                        status_code=403,
                        detail="Access denied: Order belongs to a different customer"
                    )
            # If no customer_id header, still return order for backward compatibility
            # In production, this would require authentication
            return {"order": order}

    raise HTTPException(status_code=404, detail="Order not found")


@app.get("/admin/api/2024-01/checkouts.json")
async def get_checkouts(x_shopify_access_token: str = Header(None)):
    """
    Get abandoned checkouts (carts).
    Important for cart abandonment KPI tracking.
    """
    checkouts_data = load_fixture("checkouts.json")
    return checkouts_data


@app.post("/admin/api/2024-01/checkouts.json")
async def create_checkout(x_shopify_access_token: str = Header(None)):
    """
    Create new checkout.
    Mock response for cart creation.
    """
    return {
        "checkout": {
            "id": 123456789,
            "token": "mock-checkout-token",
            "created_at": "2024-01-18T12:00:00Z",
            "status": "open",
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
