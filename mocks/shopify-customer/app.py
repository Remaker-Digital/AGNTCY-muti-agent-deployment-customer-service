# ============================================================================
# Mock Shopify Customer Accounts API - Phase 6
# ============================================================================
# Purpose: Simulate Shopify Customer Accounts API for local development
#
# This mock API simulates:
# - OAuth 2.0 authorization flow with PKCE
# - Token exchange and refresh
# - Customer profile retrieval
# - Customer orders retrieval
# - Token revocation (logout)
#
# The mock provides predictable responses for testing authentication flows
# without requiring a real Shopify store or customer accounts.
#
# Port: 8010 (configured in docker-compose.yml)
#
# Test Credentials:
# - Email: test@example.com / Password: test123
# - Email: vip@example.com / Password: vip456 (VIP customer)
#
# Related Documentation:
# - Shopify Customer Accounts API: https://shopify.dev/docs/api/customer
# - Phase 6-7 Planning: docs/PHASE-6-7-PLANNING-DECISIONS.md (Q5.A)
# ============================================================================

import json
import os
import secrets
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Header, Query, Form
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

# Initialize FastAPI app
app = FastAPI(
    title="Mock Shopify Customer Accounts API",
    description="Mock Shopify Customer Accounts API for development and testing",
    version="1.0.0",
)

# Data directory for JSON fixtures
DATA_DIR = Path("/app/data") if os.path.exists("/app/data") else Path("./data")


def load_fixture(filename: str) -> Dict:
    """Load JSON fixture from data directory."""
    filepath = DATA_DIR / filename
    if not filepath.exists():
        return {}

    with open(filepath, "r") as f:
        return json.load(f)


# ============================================================================
# In-Memory Storage (Mock)
# ============================================================================
# For development/testing, we store auth state in memory.
# In production, Cosmos DB handles this.
# ============================================================================

# Active authorization requests (state -> request data)
_pending_auth: Dict[str, Dict] = {}

# Issued tokens (access_token -> token data)
_active_tokens: Dict[str, Dict] = {}

# Mock customer database
MOCK_CUSTOMERS = {
    "test@example.com": {
        "id": "gid://shopify/Customer/12345678901",
        "email": "test@example.com",
        "password": "test123",  # Mock only - never store plain passwords in production!
        "firstName": "Test",
        "lastName": "Customer",
        "phone": "+1-555-123-4567",
        "acceptsMarketing": True,
        "createdAt": "2024-01-15T10:30:00Z",
        "ordersCount": 5,
        "totalSpent": "249.95",
        "tags": [],
        "defaultAddress": {
            "address1": "123 Main Street",
            "address2": "Apt 4B",
            "city": "New York",
            "province": "NY",
            "country": "United States",
            "zip": "10001",
        },
    },
    "vip@example.com": {
        "id": "gid://shopify/Customer/98765432101",
        "email": "vip@example.com",
        "password": "vip456",
        "firstName": "VIP",
        "lastName": "Customer",
        "phone": "+1-555-VIP-1234",
        "acceptsMarketing": False,
        "createdAt": "2022-06-01T08:00:00Z",
        "ordersCount": 47,
        "totalSpent": "4,523.80",
        "tags": ["VIP", "Wholesale"],
        "defaultAddress": {
            "address1": "500 Enterprise Blvd",
            "city": "San Francisco",
            "province": "CA",
            "country": "United States",
            "zip": "94105",
        },
    },
}

# Mock orders for customers
MOCK_ORDERS = {
    "gid://shopify/Customer/12345678901": [
        {
            "id": "gid://shopify/Order/1001",
            "name": "#1001",
            "processedAt": "2024-01-20T14:30:00Z",
            "fulfillmentStatus": "FULFILLED",
            "financialStatus": "PAID",
            "totalPrice": {"amount": "49.99", "currencyCode": "USD"},
        },
        {
            "id": "gid://shopify/Order/1002",
            "name": "#1002",
            "processedAt": "2024-01-25T09:15:00Z",
            "fulfillmentStatus": "IN_PROGRESS",
            "financialStatus": "PAID",
            "totalPrice": {"amount": "89.99", "currencyCode": "USD"},
        },
    ],
    "gid://shopify/Customer/98765432101": [
        {
            "id": "gid://shopify/Order/2001",
            "name": "#2001",
            "processedAt": "2024-01-18T11:00:00Z",
            "fulfillmentStatus": "FULFILLED",
            "financialStatus": "PAID",
            "totalPrice": {"amount": "523.50", "currencyCode": "USD"},
        },
    ],
}


# ============================================================================
# Pydantic Models
# ============================================================================


class TokenRequest(BaseModel):
    """OAuth token request."""

    grant_type: str
    client_id: str
    client_secret: Optional[str] = None
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    code_verifier: Optional[str] = None
    refresh_token: Optional[str] = None


class LoginForm(BaseModel):
    """Mock login form submission."""

    email: str
    password: str
    state: str


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/")
async def root():
    """API root - basic info."""
    return {
        "service": "Mock Shopify Customer Accounts API",
        "version": "1.0.0",
        "endpoints": [
            "/authorize",
            "/token",
            "/customer",
            "/customer/orders",
            "/revoke",
            "/health",
        ],
        "test_accounts": [
            {"email": "test@example.com", "password": "test123"},
            {"email": "vip@example.com", "password": "vip456"},
        ],
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mock-shopify-customer"}


# ============================================================================
# OAuth 2.0 Flow
# ============================================================================


@app.get("/authorize")
async def authorize(
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    response_type: str = Query("code"),
    scope: str = Query("openid customer-account-api:full"),
    state: str = Query(...),
    code_challenge: str = Query(...),
    code_challenge_method: str = Query("S256"),
):
    """
    OAuth authorization endpoint - Step 1.

    In a real implementation, this would show Shopify's login page.
    For mock, we return a simple HTML login form.
    """
    # Store authorization request for later validation
    _pending_auth[state] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "created_at": datetime.utcnow().isoformat(),
    }

    # Return simple login form (mock only)
    html_form = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Mock Shopify Login</title></head>
    <body style="font-family: sans-serif; max-width: 400px; margin: 50px auto;">
        <h2>Mock Shopify Login</h2>
        <p>Test accounts:</p>
        <ul>
            <li>test@example.com / test123</li>
            <li>vip@example.com / vip456</li>
        </ul>
        <form action="/login" method="POST">
            <input type="hidden" name="state" value="{state}">
            <div style="margin: 10px 0;">
                <label>Email:</label><br>
                <input type="email" name="email" required style="width: 100%; padding: 8px;">
            </div>
            <div style="margin: 10px 0;">
                <label>Password:</label><br>
                <input type="password" name="password" required style="width: 100%; padding: 8px;">
            </div>
            <button type="submit" style="padding: 10px 20px; background: #5c6ac4; color: white; border: none; cursor: pointer;">
                Log in
            </button>
        </form>
    </body>
    </html>
    """
    return JSONResponse(
        content={"html": html_form, "state": state},
        media_type="application/json",
    )


@app.post("/login")
async def login(
    email: str = Form(...),
    password: str = Form(...),
    state: str = Form(...),
):
    """
    Mock login form handler.

    Validates credentials and redirects with authorization code.
    """
    # Validate state
    if state not in _pending_auth:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    auth_request = _pending_auth[state]

    # Validate credentials
    customer = MOCK_CUSTOMERS.get(email)
    if not customer or customer["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Generate authorization code
    auth_code = f"mock_code_{secrets.token_urlsafe(16)}"

    # Store code with customer info
    _pending_auth[auth_code] = {
        **auth_request,
        "customer_id": customer["id"],
        "state": state,
    }

    # Build redirect URL
    redirect_uri = auth_request["redirect_uri"]
    redirect_url = f"{redirect_uri}?code={auth_code}&state={state}"

    return RedirectResponse(url=redirect_url, status_code=302)


@app.post("/token")
async def token_exchange(request: TokenRequest):
    """
    OAuth token endpoint - Step 2.

    Exchanges authorization code for access/refresh tokens.
    """
    if request.grant_type == "authorization_code":
        return await _handle_code_exchange(request)
    elif request.grant_type == "refresh_token":
        return await _handle_token_refresh(request)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported grant_type: {request.grant_type}")


async def _handle_code_exchange(request: TokenRequest):
    """Handle authorization code exchange."""
    if not request.code:
        raise HTTPException(status_code=400, detail="Missing code parameter")

    # Validate authorization code
    if request.code not in _pending_auth:
        raise HTTPException(status_code=400, detail="Invalid authorization code")

    auth_data = _pending_auth.pop(request.code)

    # Validate redirect_uri matches
    if request.redirect_uri != auth_data["redirect_uri"]:
        raise HTTPException(status_code=400, detail="redirect_uri mismatch")

    # In real implementation, we'd validate code_verifier against code_challenge
    # For mock, we skip PKCE validation

    # Generate tokens
    access_token = f"mock_access_{secrets.token_urlsafe(32)}"
    refresh_token = f"mock_refresh_{secrets.token_urlsafe(32)}"
    id_token = f"mock_id_{secrets.token_urlsafe(32)}"

    expires_in = 3600  # 1 hour

    # Store token data
    _active_tokens[access_token] = {
        "customer_id": auth_data["customer_id"],
        "scope": auth_data["scope"],
        "expires_at": (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat(),
        "refresh_token": refresh_token,
    }

    # Also index by refresh token for refresh flow
    _active_tokens[refresh_token] = {
        "customer_id": auth_data["customer_id"],
        "scope": auth_data["scope"],
        "is_refresh": True,
    }

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "scope": auth_data["scope"],
        "id_token": id_token,
    }


async def _handle_token_refresh(request: TokenRequest):
    """Handle refresh token exchange."""
    if not request.refresh_token:
        raise HTTPException(status_code=400, detail="Missing refresh_token parameter")

    # Validate refresh token
    if request.refresh_token not in _active_tokens:
        raise HTTPException(status_code=400, detail="Invalid refresh token")

    token_data = _active_tokens[request.refresh_token]
    if not token_data.get("is_refresh"):
        raise HTTPException(status_code=400, detail="Invalid refresh token")

    # Generate new access token
    access_token = f"mock_access_{secrets.token_urlsafe(32)}"
    expires_in = 3600

    # Store new token
    _active_tokens[access_token] = {
        "customer_id": token_data["customer_id"],
        "scope": token_data["scope"],
        "expires_at": (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat(),
        "refresh_token": request.refresh_token,
    }

    return {
        "access_token": access_token,
        "refresh_token": request.refresh_token,  # Same refresh token
        "token_type": "Bearer",
        "expires_in": expires_in,
        "scope": token_data["scope"],
    }


# ============================================================================
# Customer API Endpoints
# ============================================================================


def _get_customer_from_token(authorization: str) -> Dict:
    """Validate token and get customer data."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.replace("Bearer ", "")

    if token not in _active_tokens:
        raise HTTPException(status_code=401, detail="Invalid access token")

    token_data = _active_tokens[token]
    if token_data.get("is_refresh"):
        raise HTTPException(status_code=401, detail="Cannot use refresh token for API access")

    # Check expiry
    expires_at = datetime.fromisoformat(token_data["expires_at"])
    if datetime.utcnow() > expires_at:
        raise HTTPException(status_code=401, detail="Access token expired")

    # Find customer
    customer_id = token_data["customer_id"]
    for customer in MOCK_CUSTOMERS.values():
        if customer["id"] == customer_id:
            return customer

    raise HTTPException(status_code=404, detail="Customer not found")


@app.get("/customer")
async def get_customer(authorization: str = Header(...)):
    """
    Get authenticated customer's profile.

    Requires Bearer token from OAuth flow.
    """
    customer = _get_customer_from_token(authorization)

    # Return customer data (without password)
    return {
        "id": customer["id"],
        "email": customer["email"],
        "firstName": customer["firstName"],
        "lastName": customer["lastName"],
        "phone": customer["phone"],
        "acceptsMarketing": customer["acceptsMarketing"],
        "createdAt": customer["createdAt"],
        "ordersCount": customer["ordersCount"],
        "totalSpent": customer["totalSpent"],
        "defaultAddress": customer["defaultAddress"],
        "tags": customer["tags"],
    }


@app.get("/customer/orders")
async def get_customer_orders(
    authorization: str = Header(...),
    limit: int = Query(10, ge=1, le=50),
):
    """
    Get authenticated customer's orders.

    Requires Bearer token from OAuth flow.
    """
    customer = _get_customer_from_token(authorization)
    customer_id = customer["id"]

    orders = MOCK_ORDERS.get(customer_id, [])
    return {"orders": orders[:limit]}


# ============================================================================
# Token Revocation
# ============================================================================


@app.post("/revoke")
async def revoke_token(token: str = Form(...)):
    """
    Revoke an access or refresh token.

    Used for logout functionality.
    """
    if token in _active_tokens:
        # If revoking access token, also revoke associated refresh token
        token_data = _active_tokens.pop(token)
        if "refresh_token" in token_data:
            _active_tokens.pop(token_data["refresh_token"], None)

    return {"revoked": True}


# ============================================================================
# Development Helpers
# ============================================================================


@app.get("/debug/tokens")
async def debug_tokens():
    """List active tokens (development only)."""
    return {
        "active_tokens": len(_active_tokens),
        "pending_auth": len(_pending_auth),
    }


@app.post("/debug/reset")
async def debug_reset():
    """Reset all state (development only)."""
    _active_tokens.clear()
    _pending_auth.clear()
    return {"reset": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8010)
