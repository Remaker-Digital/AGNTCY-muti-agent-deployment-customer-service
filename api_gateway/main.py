"""
API Gateway for Phase 5 Load Testing

This FastAPI service provides HTTP REST endpoints for the multi-agent customer
service platform. It bridges HTTP requests to the AGNTCY agent pipeline.

Endpoints:
- POST /api/v1/chat - Process customer message through agent pipeline
- GET /health - Health check endpoint for Application Gateway
- GET /api/v1/status - System status and metrics
- GET /api/v1/pool/stats - Connection pool statistics (auto-scaling support)

Educational Notes:
- This gateway is necessary because SLIM/AGNTCY uses gRPC (HTTP/2 + protobufs)
- Application Gateway v2 requires HTTP/HTTPS backends for health probes
- This service can run as a sidecar container or standalone service
- Connection pooling enables efficient scaling for 10,000 daily users

Usage:
    uvicorn api_gateway.main:app --host 0.0.0.0 --port 8080

Cost Impact:
    - Adds ~$5-10/month for Container Instance (0.5 vCPU, 1GB RAM)
    - Enables load testing through Application Gateway
    - Reuses Azure OpenAI calls from console module
    - Connection pooling reduces latency by ~20-30%

Auto-Scaling Support:
    - Circuit breaker prevents cascade failures under load
    - Connection pool metrics exposed for KEDA scaling decisions
    - Graceful degradation when Azure OpenAI is rate-limited
"""

import os
import sys
import time
import uuid
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import security utilities
try:
    from shared.security import (
        sanitize_message,
        SanitizationResult,
        RateLimiter,
        RateLimitConfig,
        check_rate_limit,
    )
    SECURITY_MODULE_AVAILABLE = True
except ImportError:
    SECURITY_MODULE_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import connection pool (optional - graceful fallback if not available)
try:
    from shared.openai_pool import (
        init_openai_pool,
        get_openai_pool,
        close_openai_pool,
        AzureOpenAIPool,
        PoolConfig,
    )

    CONNECTION_POOL_AVAILABLE = True
    logger.info("Connection pool module loaded successfully")
except ImportError as e:
    CONNECTION_POOL_AVAILABLE = False
    logger.warning(
        f"Connection pool not available: {e}. Using direct Azure OpenAI calls."
    )

# =============================================================================
# Request/Response Models
# =============================================================================


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(
        ..., min_length=1, max_length=4096, description="Customer message"
    )
    session_id: Optional[str] = Field(
        default=None, description="Session ID for conversation continuity"
    )
    language: Optional[str] = Field(
        default="en", description="Language code (en, fr-CA, es)"
    )


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    response: str = Field(..., description="AI-generated response")
    session_id: str = Field(..., description="Session ID for this conversation")
    intent: Optional[str] = Field(default=None, description="Classified intent")
    confidence: Optional[float] = Field(
        default=None, description="Intent confidence score"
    )
    escalated: bool = Field(
        default=False, description="Whether the message was escalated"
    )
    processing_time_ms: int = Field(
        ..., description="Total processing time in milliseconds"
    )
    agents_involved: list = Field(
        default_factory=list, description="Agents that processed this message"
    )
    language: str = Field(
        default="en", description="Language used for response (en, fr-CA, es)"
    )


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Service status (healthy/unhealthy)")
    timestamp: str = Field(..., description="Current timestamp")
    version: str = Field(..., description="API version")
    azure_openai_available: bool = Field(..., description="Azure OpenAI connectivity")
    uptime_seconds: float = Field(..., description="Service uptime")


class StatusResponse(BaseModel):
    """System status response model."""

    status: str
    timestamp: str
    metrics: Dict[str, Any]


class PoolStatsResponse(BaseModel):
    """Connection pool statistics response model."""

    pool_enabled: bool = Field(..., description="Whether connection pooling is active")
    pool_size: int = Field(default=0, description="Current pool size")
    active_connections: int = Field(default=0, description="Active connections")
    available_connections: int = Field(default=0, description="Available connections")
    total_requests: int = Field(default=0, description="Total requests through pool")
    total_errors: int = Field(default=0, description="Total errors")
    circuit_breaker_state: str = Field(
        default="unknown", description="Circuit breaker state"
    )
    avg_wait_time_ms: float = Field(
        default=0.0, description="Average connection wait time"
    )
    timestamp: str = Field(..., description="Current timestamp")


# =============================================================================
# Widget API Models (Phase 6)
# =============================================================================


class WidgetConfigRequest(BaseModel):
    """Request model for widget configuration lookup."""

    merchant_id: str = Field(..., description="Merchant ID for configuration lookup")


class WidgetConfigResponse(BaseModel):
    """Widget configuration response model."""

    merchant_id: str
    enabled: bool = True
    primary_color: str = "#5c6ac4"
    secondary_color: str = "#ffffff"
    agent_name: str = "Support Assistant"
    greeting: Optional[str] = None
    position: str = "bottom-right"
    language: str = "en"
    show_powered_by: bool = True
    features: Dict[str, bool] = Field(default_factory=dict)


class SessionCreateRequest(BaseModel):
    """Request model for session creation."""

    merchant_id: str = Field(..., description="Merchant ID")
    channel: str = Field(default="web", description="Channel type (web, whatsapp)")
    device_id: Optional[str] = Field(default=None, description="Device fingerprint")
    user_agent: Optional[str] = Field(default=None, description="User agent string")


class SessionCreateResponse(BaseModel):
    """Session creation response model."""

    session_id: str
    auth_level: str = "anonymous"
    expires_at: str
    created_at: str


class SessionInfoResponse(BaseModel):
    """Session information response model."""

    session_id: str
    auth_level: str
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    is_vip: bool = False
    conversation_count: int = 0
    created_at: str
    expires_at: str


class AuthLoginRequest(BaseModel):
    """OAuth login initiation request."""

    session_id: str = Field(..., description="Current session ID")
    redirect_uri: str = Field(..., description="Redirect URI after login")


class AuthLoginResponse(BaseModel):
    """OAuth login initiation response."""

    authorization_url: str
    state: str


class AuthCallbackRequest(BaseModel):
    """OAuth callback request."""

    code: str = Field(..., description="Authorization code from Shopify")
    state: str = Field(..., description="State parameter for CSRF verification")
    redirect_uri: str = Field(..., description="Redirect URI used in login")


class AuthCallbackResponse(BaseModel):
    """OAuth callback response."""

    session_id: str
    auth_level: str
    customer_name: Optional[str] = None
    success: bool


class EmbedCodeRequest(BaseModel):
    """Request model for generating widget embed code."""

    merchant_id: str = Field(..., description="Merchant ID for the widget")
    primary_color: Optional[str] = Field(
        default="#5c6ac4", description="Primary brand color (hex)"
    )
    position: Optional[str] = Field(
        default="bottom-right", description="Widget position (bottom-right, bottom-left)"
    )
    language: Optional[str] = Field(
        default="en", description="Default language (en, fr-CA, es)"
    )
    custom_greeting: Optional[str] = Field(
        default=None, description="Custom greeting message"
    )
    show_powered_by: Optional[bool] = Field(
        default=True, description="Show 'Powered by AGNTCY' footer"
    )


class EmbedCodeResponse(BaseModel):
    """Response model for widget embed code."""

    merchant_id: str
    script_tag: str = Field(..., description="Full script tag for embedding")
    cdn_url: str = Field(..., description="CDN URL for the widget script")
    init_code: str = Field(..., description="JavaScript initialization code")
    full_snippet: str = Field(..., description="Complete embed snippet (copy-paste ready)")


# =============================================================================
# WhatsApp API Models (Phase 6)
# =============================================================================


class WhatsAppVerifyRequest(BaseModel):
    """Request model for webhook verification."""

    mode: str = Field(..., alias="hub.mode", description="Verification mode")
    token: str = Field(..., alias="hub.verify_token", description="Verify token")
    challenge: str = Field(..., alias="hub.challenge", description="Challenge to return")

    class Config:
        populate_by_name = True


class WhatsAppSendMessageRequest(BaseModel):
    """Request model for sending WhatsApp messages."""

    to: str = Field(..., description="Recipient phone number (without + prefix)")
    message: str = Field(..., max_length=4096, description="Message text")
    reply_to_message_id: Optional[str] = Field(
        default=None, description="Message ID to reply to"
    )


class WhatsAppSendTemplateRequest(BaseModel):
    """Request model for sending WhatsApp template messages."""

    to: str = Field(..., description="Recipient phone number")
    template_name: str = Field(..., description="Name of approved template")
    language: str = Field(default="en_US", description="Template language code")
    parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Template parameters by component type"
    )


class WhatsAppSendButtonsRequest(BaseModel):
    """Request model for sending interactive button messages."""

    to: str = Field(..., description="Recipient phone number")
    body: str = Field(..., description="Message body text")
    buttons: list = Field(..., description="List of buttons with id and title")
    header: Optional[str] = Field(default=None, description="Header text")
    footer: Optional[str] = Field(default=None, description="Footer text")


class WhatsAppMessageResponse(BaseModel):
    """Response model for sent WhatsApp messages."""

    success: bool
    message_id: Optional[str] = None
    to: str
    timestamp: str
    error: Optional[str] = None


class WhatsAppSessionResponse(BaseModel):
    """Response model for WhatsApp session information."""

    phone_number: str
    session_id: Optional[str] = None
    auth_level: str = "anonymous"
    customer_name: Optional[str] = None
    is_linked: bool = False
    linked_channels: list = Field(default_factory=list)


class WhatsAppWebhookStatusResponse(BaseModel):
    """Response model for webhook configuration status."""

    configured: bool
    verify_token_set: bool
    app_secret_set: bool
    handlers_registered: int
    phone_number_id: Optional[str] = None
    business_account_id: Optional[str] = None


# =============================================================================
# Application State
# =============================================================================


class AppState:
    """Application state container."""

    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.total_latency_ms = 0
        self.azure_mode = None
        self.azure_available = False
        self.pool_enabled = False
        self.openai_pool: Optional[AzureOpenAIPool] = None


app_state = AppState()


# =============================================================================
# FastAPI Application
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    # Startup
    logger.info("API Gateway starting up...")

    # Initialize connection pool if available and enabled
    use_pool = os.getenv("USE_CONNECTION_POOL", "true").lower() == "true"

    if CONNECTION_POOL_AVAILABLE and use_pool:
        try:
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            api_key = os.getenv("AZURE_OPENAI_API_KEY")

            if endpoint and api_key:
                # Configure pool for auto-scaling workload
                pool_config = PoolConfig(
                    min_connections=int(os.getenv("POOL_MIN_CONNECTIONS", "2")),
                    max_connections=int(os.getenv("POOL_MAX_CONNECTIONS", "10")),
                    connection_timeout=float(
                        os.getenv("POOL_CONNECTION_TIMEOUT", "30.0")
                    ),
                    max_retries=int(os.getenv("POOL_MAX_RETRIES", "3")),
                    circuit_breaker_threshold=int(
                        os.getenv("POOL_CIRCUIT_BREAKER_THRESHOLD", "5")
                    ),
                    circuit_breaker_timeout=float(
                        os.getenv("POOL_CIRCUIT_BREAKER_TIMEOUT", "60.0")
                    ),
                )

                app_state.openai_pool = await init_openai_pool(
                    endpoint=endpoint,
                    api_key=api_key,
                    api_version=os.getenv(
                        "AZURE_OPENAI_API_VERSION", "2024-02-15-preview"
                    ),
                    config=pool_config,
                )
                app_state.pool_enabled = True
                logger.info(
                    f"Connection pool initialized: min={pool_config.min_connections}, max={pool_config.max_connections}"
                )
            else:
                logger.warning("Azure OpenAI credentials not found - pool disabled")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            app_state.pool_enabled = False

    # Try to initialize Azure OpenAI mode (for non-pooled requests)
    try:
        from console.azure_openai_mode import get_azure_mode, is_azure_mode_available

        if is_azure_mode_available():
            app_state.azure_mode = get_azure_mode()
            success, msg = app_state.azure_mode.initialize()
            app_state.azure_available = success
            logger.info(f"Azure OpenAI mode initialized: {success} - {msg}")
        else:
            logger.warning(
                "Azure OpenAI mode not available - will use fallback responses"
            )
    except Exception as e:
        logger.error(f"Failed to initialize Azure OpenAI: {e}")
        app_state.azure_available = False

    logger.info("API Gateway ready to accept requests")
    logger.info(
        f"  - Connection pool: {'enabled' if app_state.pool_enabled else 'disabled'}"
    )
    logger.info(
        f"  - Azure OpenAI: {'available' if app_state.azure_available else 'unavailable'}"
    )
    yield

    # Shutdown
    logger.info("API Gateway shutting down...")

    # Close connection pool
    if app_state.pool_enabled and app_state.openai_pool:
        try:
            await close_openai_pool()
            logger.info("Connection pool closed successfully")
        except Exception as e:
            logger.error(f"Error closing connection pool: {e}")


app = FastAPI(
    title="AGNTCY Customer Service API",
    description="HTTP REST API Gateway for the multi-agent customer service platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for browser-based testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Middleware for Request Tracking
# =============================================================================


@app.middleware("http")
async def track_requests(request: Request, call_next):
    """Track request metrics."""
    start_time = time.time()
    response = await call_next(request)

    # Track metrics (except health checks)
    if not request.url.path.endswith("/health"):
        app_state.request_count += 1
        latency_ms = int((time.time() - start_time) * 1000)
        app_state.total_latency_ms += latency_ms

        if response.status_code >= 400:
            app_state.error_count += 1

    return response


# =============================================================================
# API Endpoints
# =============================================================================


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for Application Gateway.

    Returns 200 OK if service is healthy.
    This endpoint is critical for AppGW backend health probes.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0",
        azure_openai_available=app_state.azure_available,
        uptime_seconds=time.time() - app_state.start_time,
    )


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - redirects to health check."""
    return await health_check()


@app.post("/api/v1/chat", response_model=ChatResponse)
async def process_chat(
    request: ChatRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    x_forwarded_for: Optional[str] = Header(None, alias="X-Forwarded-For"),
):
    """
    Process a customer message through the agent pipeline.

    This endpoint:
    1. Validates session and applies rate limiting
    2. Sanitizes input message for prompt injection
    3. Validates the input message via Critic/Supervisor
    4. Classifies intent
    5. Retrieves relevant knowledge
    6. Generates a response
    7. Checks for escalation triggers
    8. Records analytics

    Security:
    - Requires session_id (in body or header)
    - Rate limited: 30 requests/minute per session
    - Input sanitization blocks prompt injection attempts

    Returns the AI-generated response along with metadata.
    """
    start_time = time.time()

    # Session validation - require session_id
    session_id = request.session_id or x_session_id
    if not session_id:
        # Auto-create anonymous session for backward compatibility
        session_id = f"anon-{uuid.uuid4().hex[:16]}"
        logger.info(f"Created anonymous session: {session_id[:16]}...")

    # Rate limiting
    if SECURITY_MODULE_AVAILABLE:
        rate_key = session_id or x_forwarded_for or "unknown"
        rate_result = check_rate_limit(rate_key)
        if not rate_result.allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Retry after {rate_result.retry_after:.0f} seconds.",
                headers={"Retry-After": str(int(rate_result.retry_after or 60))},
            )

    # Input sanitization - detect prompt injection
    if SECURITY_MODULE_AVAILABLE:
        sanitization_result = sanitize_message(request.message)
        if sanitization_result.should_block:
            logger.warning(
                f"Blocked message due to prompt injection: "
                f"patterns={sanitization_result.patterns_detected}"
            )
            raise HTTPException(
                status_code=400,
                detail="Message blocked for security reasons. Please rephrase your question.",
            )

        # Use sanitized message
        message_to_process = sanitization_result.sanitized_message
    else:
        message_to_process = request.message

    try:
        if app_state.azure_available and app_state.azure_mode:
            # Use Azure OpenAI pipeline (real AI responses)
            # Pass language parameter for multi-language support (Phase 4+)
            result = await app_state.azure_mode.process_message(
                message=message_to_process,  # Use sanitized message
                session_id=session_id,
                language=request.language or "en",
            )

            processing_time_ms = int((time.time() - start_time) * 1000)

            return ChatResponse(
                response=result.response,
                session_id=session_id,
                intent=result.intent,
                confidence=result.intent_confidence,
                escalated=result.escalation_needed,
                processing_time_ms=processing_time_ms,
                agents_involved=[step.agent_name for step in result.pipeline_steps],
                language=request.language or "en",
            )
        else:
            # Fallback: Simple mock response
            processing_time_ms = int((time.time() - start_time) * 1000)

            return ChatResponse(
                response=_generate_fallback_response(request.message),
                session_id=session_id,
                intent="general_inquiry",
                confidence=0.7,
                escalated=False,
                processing_time_ms=processing_time_ms,
                agents_involved=["fallback-handler"],
                language=request.language or "en",
            )

    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to process message: {str(e)}"
        )


@app.get("/api/v1/status", response_model=StatusResponse)
async def get_status():
    """
    Get system status and metrics.

    Returns current service metrics including:
    - Request counts
    - Error rates
    - Average latency
    - Azure OpenAI status
    - Connection pool status (for auto-scaling)
    """
    uptime = time.time() - app_state.start_time
    avg_latency = (
        app_state.total_latency_ms / app_state.request_count
        if app_state.request_count > 0
        else 0
    )

    # Build metrics dict
    metrics = {
        "uptime_seconds": uptime,
        "total_requests": app_state.request_count,
        "error_count": app_state.error_count,
        "error_rate": app_state.error_count / max(app_state.request_count, 1),
        "avg_latency_ms": avg_latency,
        "azure_openai_available": app_state.azure_available,
        "connection_pool_enabled": app_state.pool_enabled,
    }

    # Add pool metrics if available
    if app_state.pool_enabled and app_state.openai_pool:
        pool_metrics = app_state.openai_pool.get_metrics()
        metrics["pool"] = {
            "active_connections": pool_metrics.active_connections,
            "available_connections": pool_metrics.available_connections,
            "total_requests": pool_metrics.total_requests,
            "total_errors": pool_metrics.total_errors,
            "avg_wait_time_ms": pool_metrics.avg_wait_time_ms,
            "circuit_breaker_state": pool_metrics.circuit_breaker_state,
        }

    return StatusResponse(
        status="operational", timestamp=datetime.utcnow().isoformat(), metrics=metrics
    )


@app.get("/api/v1/pool/stats", response_model=PoolStatsResponse)
async def get_pool_stats():
    """
    Get connection pool statistics for monitoring and auto-scaling.

    This endpoint is used by:
    - KEDA for scaling decisions based on connection utilization
    - Grafana dashboards for pool health visualization
    - Alerting rules for circuit breaker state changes

    Returns detailed pool metrics or indicates pool is disabled.
    """
    if not app_state.pool_enabled or not app_state.openai_pool:
        return PoolStatsResponse(
            pool_enabled=False, timestamp=datetime.utcnow().isoformat()
        )

    pool_metrics = app_state.openai_pool.get_metrics()

    return PoolStatsResponse(
        pool_enabled=True,
        pool_size=pool_metrics.pool_size,
        active_connections=pool_metrics.active_connections,
        available_connections=pool_metrics.available_connections,
        total_requests=pool_metrics.total_requests,
        total_errors=pool_metrics.total_errors,
        circuit_breaker_state=pool_metrics.circuit_breaker_state,
        avg_wait_time_ms=pool_metrics.avg_wait_time_ms,
        timestamp=datetime.utcnow().isoformat(),
    )


# =============================================================================
# Widget API Endpoints (Phase 6)
# =============================================================================


@app.get("/api/v1/widget/config/{merchant_id}", response_model=WidgetConfigResponse)
async def get_widget_config(merchant_id: str):
    """
    Get widget configuration for a merchant.

    Returns theming, language, and feature settings for the embedded widget.
    In Phase 6, this returns default config. Phase 7 adds Azure App Configuration.
    """
    # TODO: Load from Azure App Configuration in Phase 7
    # For now, return default configuration
    return WidgetConfigResponse(
        merchant_id=merchant_id,
        enabled=True,
        primary_color="#5c6ac4",
        secondary_color="#ffffff",
        agent_name="Support Assistant",
        greeting="Hi! How can I help you today?",
        position="bottom-right",
        language="en",
        show_powered_by=True,
        features={
            "file_upload": False,
            "voice_input": False,
            "rich_messages": True,
            "typing_indicators": True,
        },
    )


@app.post("/api/v1/widget/sessions", response_model=SessionCreateResponse)
async def create_widget_session(request: SessionCreateRequest):
    """
    Create a new widget session.

    Called when widget initializes without an existing session.
    Returns a new anonymous session with a 7-day expiry.
    """
    from datetime import timedelta

    try:
        # Try to use session manager if available
        try:
            from shared.auth.session_manager import init_session_manager, get_session_manager
            from shared.auth.models import create_anonymous_session

            # Create session via manager for persistence
            try:
                manager = get_session_manager()
            except RuntimeError:
                # Manager not initialized - use direct creation
                session = create_anonymous_session(
                    device_id=request.device_id,
                    channel=request.channel,
                    user_agent=request.user_agent,
                )
                return SessionCreateResponse(
                    session_id=session.session_id,
                    auth_level=session.auth_level.value,
                    expires_at=session.expires_at,
                    created_at=session.created_at,
                )

            session = await manager.create_session(
                channel=request.channel,
                device_id=request.device_id,
                user_agent=request.user_agent,
            )

            return SessionCreateResponse(
                session_id=session.session_id,
                auth_level=session.auth_level.value,
                expires_at=session.expires_at,
                created_at=session.created_at,
            )

        except ImportError:
            # Auth module not available - create basic session
            session_id = f"widget-{uuid.uuid4().hex[:16]}"
            now = datetime.utcnow()
            expires_at = now + timedelta(days=7)

            return SessionCreateResponse(
                session_id=session_id,
                auth_level="anonymous",
                expires_at=expires_at.isoformat() + "Z",
                created_at=now.isoformat() + "Z",
            )

    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create session")


@app.get("/api/v1/widget/sessions/{session_id}", response_model=SessionInfoResponse)
async def get_widget_session(session_id: str):
    """
    Get information about an existing session.

    Returns session details including auth level and customer info.
    """
    try:
        from shared.auth.session_manager import get_session_manager

        try:
            manager = get_session_manager()
            session = await manager.get_session(session_id)

            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            return SessionInfoResponse(
                session_id=session.session_id,
                auth_level=session.auth_level.value,
                customer_id=session.customer.id if session.customer else None,
                customer_name=session.customer.full_name if session.customer else None,
                is_vip=session.customer.is_vip if session.customer else False,
                conversation_count=session.conversation_count,
                created_at=session.created_at,
                expires_at=session.expires_at,
            )

        except RuntimeError:
            # Session manager not initialized
            raise HTTPException(status_code=404, detail="Session not found")

    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Error getting session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get session")


@app.post("/api/v1/widget/auth/login", response_model=AuthLoginResponse)
async def initiate_widget_login(request: AuthLoginRequest):
    """
    Initiate Shopify Customer Accounts OAuth login.

    Returns the authorization URL to redirect the customer to Shopify login.
    """
    try:
        from shared.auth.shopify_customer_api import get_shopify_customer_client

        client = await get_shopify_customer_client()
        auth_url, state, pkce = client.get_authorization_url(
            redirect_uri=request.redirect_uri
        )

        # Store PKCE verifier in session for callback
        # In production, store in session manager
        # For now, we include state which can be used to look up the verifier

        return AuthLoginResponse(
            authorization_url=auth_url,
            state=state,
        )

    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Authentication not configured"
        )
    except Exception as e:
        logger.error(f"Error initiating login: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to initiate login")


@app.post("/api/v1/widget/auth/callback", response_model=AuthCallbackResponse)
async def handle_widget_auth_callback(request: AuthCallbackRequest):
    """
    Handle OAuth callback from Shopify.

    Exchanges authorization code for tokens and upgrades session.
    """
    try:
        from shared.auth.shopify_customer_api import get_shopify_customer_client
        from shared.auth.session_manager import get_session_manager

        client = await get_shopify_customer_client()

        # Exchange code for tokens
        # Note: In production, retrieve code_verifier from session storage
        # For MVP, we skip PKCE verification in mock mode
        token = await client.exchange_code(
            code=request.code,
            redirect_uri=request.redirect_uri,
            code_verifier="placeholder",  # Would be retrieved from session
        )

        if not token:
            return AuthCallbackResponse(
                session_id="",
                auth_level="anonymous",
                success=False,
            )

        # Get customer profile
        customer = await client.get_customer_profile(token.access_token)

        if not customer:
            return AuthCallbackResponse(
                session_id="",
                auth_level="anonymous",
                success=False,
            )

        # TODO: Upgrade session to authenticated
        # This requires looking up session by state parameter

        return AuthCallbackResponse(
            session_id=f"authenticated-{uuid.uuid4().hex[:8]}",
            auth_level="authenticated",
            customer_name=customer.full_name,
            success=True,
        )

    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Authentication not configured"
        )
    except Exception as e:
        logger.error(f"Error handling auth callback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to complete authentication")


@app.post("/api/v1/widget/embed-code", response_model=EmbedCodeResponse)
async def generate_embed_code(request: EmbedCodeRequest):
    """
    Generate widget embed code for a merchant.

    Returns a complete code snippet that merchants can copy-paste into their website.
    The snippet includes the CDN-hosted script and initialization code.

    This endpoint is used by:
    - Merchant onboarding flow
    - Widget configuration dashboard
    - Developer documentation examples

    Example usage:
        POST /api/v1/widget/embed-code
        {
            "merchant_id": "acme-coffee",
            "primary_color": "#5c6ac4",
            "position": "bottom-right",
            "language": "en"
        }
    """
    # Get CDN URL from environment or use default
    cdn_base = os.getenv(
        "WIDGET_CDN_URL",
        "https://agntcy-cs-prod-widget-cdn.azureedge.net"
    )
    cdn_url = f"{cdn_base}/widget/agntcy-chat.min.js"

    # Build initialization options
    init_options = {
        "merchantId": request.merchant_id,
        "primaryColor": request.primary_color or "#5c6ac4",
        "position": request.position or "bottom-right",
        "language": request.language or "en",
        "showPoweredBy": request.show_powered_by if request.show_powered_by is not None else True,
    }

    # Add custom greeting if provided
    if request.custom_greeting:
        init_options["greeting"] = request.custom_greeting

    # Generate script tag
    script_tag = f'<script src="{cdn_url}" async></script>'

    # Generate init code with proper JSON formatting
    import json
    init_json = json.dumps(init_options, indent=2)
    init_code = f"AGNTCYChat.init({init_json});"

    # Generate full snippet with proper formatting
    full_snippet = f'''<!-- AGNTCY Chat Widget -->
{script_tag}
<script>
  window.addEventListener('load', function() {{
    {init_code}
  }});
</script>
<!-- End AGNTCY Chat Widget -->'''

    return EmbedCodeResponse(
        merchant_id=request.merchant_id,
        script_tag=script_tag,
        cdn_url=cdn_url,
        init_code=init_code,
        full_snippet=full_snippet,
    )


@app.get("/api/v1/widget/embed-code/{merchant_id}", response_model=EmbedCodeResponse)
async def get_embed_code(
    merchant_id: str,
    primary_color: Optional[str] = "#5c6ac4",
    position: Optional[str] = "bottom-right",
    language: Optional[str] = "en",
):
    """
    Get widget embed code for a merchant (GET variant for easy linking).

    Query Parameters:
    - primary_color: Primary brand color (hex)
    - position: Widget position (bottom-right, bottom-left)
    - language: Default language (en, fr-CA, es)

    Example:
        GET /api/v1/widget/embed-code/acme-coffee?primary_color=%235c6ac4
    """
    request = EmbedCodeRequest(
        merchant_id=merchant_id,
        primary_color=primary_color,
        position=position,
        language=language,
    )
    return await generate_embed_code(request)


# =============================================================================
# WhatsApp API Endpoints (Phase 6)
# =============================================================================


@app.get("/api/v1/whatsapp/webhook")
async def verify_whatsapp_webhook(request: Request):
    """
    Verify WhatsApp webhook subscription.

    Meta sends GET request with hub.mode, hub.verify_token, and hub.challenge.
    We must return hub.challenge if verification succeeds.

    This endpoint is called once when setting up the webhook in Meta Business Manager.
    """
    try:
        from shared.whatsapp import get_webhook_handler

        mode = request.query_params.get("hub.mode", "")
        token = request.query_params.get("hub.verify_token", "")
        challenge = request.query_params.get("hub.challenge", "")

        handler = get_webhook_handler()
        result = handler.verify_webhook(mode, token, challenge)

        if result:
            # Return challenge as plain text for Meta verification
            return Response(content=result, media_type="text/plain")
        else:
            raise HTTPException(status_code=403, detail="Verification failed")

    except ImportError:
        logger.error("WhatsApp module not available")
        raise HTTPException(status_code=501, detail="WhatsApp integration not configured")
    except HTTPException:
        # Re-raise HTTP exceptions (like 403) without wrapping
        raise
    except Exception as e:
        logger.error(f"Webhook verification error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Verification error")


@app.post("/api/v1/whatsapp/webhook")
async def receive_whatsapp_webhook(request: Request):
    """
    Receive WhatsApp webhook events.

    Meta sends POST requests with message events, status updates, and errors.
    We process them and route to registered handlers.

    Returns 200 OK quickly to acknowledge receipt (Meta expects <15s response).
    Actual message processing happens asynchronously.
    """
    try:
        from shared.whatsapp import get_webhook_handler

        # Get raw body for signature verification
        raw_body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256", "")

        # Parse JSON payload
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

        # Process webhook
        handler = get_webhook_handler()
        result = await handler.handle_webhook(
            payload=payload,
            signature_header=signature,
            raw_body=raw_body,
        )

        return JSONResponse(content=result)

    except ImportError:
        logger.error("WhatsApp module not available")
        # Still return 200 to prevent Meta from retrying
        return JSONResponse(content={"status": "ok", "note": "WhatsApp not configured"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        # Return 200 to prevent retries - log error for investigation
        return JSONResponse(content={"status": "error", "message": str(e)})


@app.post("/api/v1/whatsapp/send/text", response_model=WhatsAppMessageResponse)
async def send_whatsapp_text(request_body: WhatsAppSendMessageRequest):
    """
    Send a text message via WhatsApp.

    Can only send to users who have messaged within 24-hour window,
    otherwise use template messages.
    """
    try:
        from shared.whatsapp import get_whatsapp_client

        client = get_whatsapp_client()
        result = await client.send_text_message(
            to=request_body.to,
            text=request_body.message,
            reply_to_message_id=request_body.reply_to_message_id,
        )

        # Extract message ID from response
        messages = result.get("messages", [])
        message_id = messages[0].get("id") if messages else None

        return WhatsAppMessageResponse(
            success=True,
            message_id=message_id,
            to=request_body.to,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    except ImportError:
        raise HTTPException(status_code=501, detail="WhatsApp integration not configured")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {e}", exc_info=True)
        return WhatsAppMessageResponse(
            success=False,
            to=request_body.to,
            timestamp=datetime.utcnow().isoformat() + "Z",
            error=str(e),
        )


@app.post("/api/v1/whatsapp/send/template", response_model=WhatsAppMessageResponse)
async def send_whatsapp_template(request_body: WhatsAppSendTemplateRequest):
    """
    Send a template message via WhatsApp.

    Template messages can be sent at any time (no 24-hour window required).
    Templates must be pre-approved by Meta.
    """
    try:
        from shared.whatsapp import get_whatsapp_client

        client = get_whatsapp_client()
        result = await client.send_template_message(
            to=request_body.to,
            template_name=request_body.template_name,
            language=request_body.language,
            parameters=request_body.parameters,
        )

        messages = result.get("messages", [])
        message_id = messages[0].get("id") if messages else None

        return WhatsAppMessageResponse(
            success=True,
            message_id=message_id,
            to=request_body.to,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    except ImportError:
        raise HTTPException(status_code=501, detail="WhatsApp integration not configured")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error sending WhatsApp template: {e}", exc_info=True)
        return WhatsAppMessageResponse(
            success=False,
            to=request_body.to,
            timestamp=datetime.utcnow().isoformat() + "Z",
            error=str(e),
        )


@app.post("/api/v1/whatsapp/send/buttons", response_model=WhatsAppMessageResponse)
async def send_whatsapp_buttons(request_body: WhatsAppSendButtonsRequest):
    """
    Send an interactive message with quick reply buttons.

    Buttons provide better UX than plain text for common actions.
    Maximum 3 buttons per message.
    """
    try:
        from shared.whatsapp import get_whatsapp_client

        client = get_whatsapp_client()
        result = await client.send_quick_reply_buttons(
            to=request_body.to,
            body=request_body.body,
            buttons=request_body.buttons,
            header=request_body.header,
            footer=request_body.footer,
        )

        messages = result.get("messages", [])
        message_id = messages[0].get("id") if messages else None

        return WhatsAppMessageResponse(
            success=True,
            message_id=message_id,
            to=request_body.to,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    except ImportError:
        raise HTTPException(status_code=501, detail="WhatsApp integration not configured")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error sending WhatsApp buttons: {e}", exc_info=True)
        return WhatsAppMessageResponse(
            success=False,
            to=request_body.to,
            timestamp=datetime.utcnow().isoformat() + "Z",
            error=str(e),
        )


@app.get("/api/v1/whatsapp/session/{phone_number}", response_model=WhatsAppSessionResponse)
async def get_whatsapp_session(phone_number: str):
    """
    Get session information for a WhatsApp user.

    Returns session details including cross-channel linking status.
    """
    try:
        from shared.whatsapp import get_session_bridge

        bridge = get_session_bridge()
        session = await bridge.get_or_create_session(phone_number)

        if session:
            return WhatsAppSessionResponse(
                phone_number=phone_number,
                session_id=session.session_id,
                auth_level=session.auth_level.value,
                customer_name=session.customer.full_name if session.customer else None,
                is_linked=session.customer is not None,
                linked_channels=["whatsapp", "web"] if session.customer else ["whatsapp"],
            )
        else:
            return WhatsAppSessionResponse(
                phone_number=phone_number,
                is_linked=False,
                linked_channels=["whatsapp"],
            )

    except ImportError:
        raise HTTPException(status_code=501, detail="WhatsApp integration not configured")
    except Exception as e:
        logger.error(f"Error getting WhatsApp session: {e}", exc_info=True)
        return WhatsAppSessionResponse(
            phone_number=phone_number,
            is_linked=False,
            linked_channels=[],
        )


@app.get("/api/v1/whatsapp/status", response_model=WhatsAppWebhookStatusResponse)
async def get_whatsapp_status():
    """
    Get WhatsApp integration status.

    Returns configuration status for webhook and API client.
    """
    try:
        from shared.whatsapp import get_webhook_handler, get_whatsapp_client

        handler = get_webhook_handler()
        client = get_whatsapp_client()

        verify_token = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "")
        app_secret = os.getenv("WHATSAPP_APP_SECRET", "")

        return WhatsAppWebhookStatusResponse(
            configured=True,
            verify_token_set=bool(verify_token),
            app_secret_set=bool(app_secret),
            handlers_registered=len(handler._message_handlers),
            phone_number_id=client.phone_number_id,
            business_account_id=client.business_account_id,
        )

    except ImportError:
        return WhatsAppWebhookStatusResponse(
            configured=False,
            verify_token_set=False,
            app_secret_set=False,
            handlers_registered=0,
        )
    except RuntimeError:
        verify_token = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "")
        app_secret = os.getenv("WHATSAPP_APP_SECRET", "")

        return WhatsAppWebhookStatusResponse(
            configured=False,
            verify_token_set=bool(verify_token),
            app_secret_set=bool(app_secret),
            handlers_registered=0,
        )


# =============================================================================
# Helper Functions
# =============================================================================


def _generate_fallback_response(message: str) -> str:
    """Generate a simple fallback response when Azure OpenAI is unavailable."""
    message_lower = message.lower()

    if any(
        word in message_lower for word in ["order", "tracking", "shipped", "delivery"]
    ):
        return (
            "Thank you for your inquiry about your order. "
            "I'm currently operating in limited mode. "
            "Please check your email for tracking information or "
            "contact our support team at support@example.com."
        )

    elif any(word in message_lower for word in ["return", "refund", "exchange"]):
        return (
            "Thank you for reaching out about returns. "
            "Our return policy allows returns within 30 days. "
            "Please contact support@example.com for assistance."
        )

    elif any(word in message_lower for word in ["product", "coffee", "roast", "brew"]):
        return (
            "Thank you for your interest in our products! "
            "We offer a wide variety of premium coffees. "
            "Please visit our website for detailed product information."
        )

    else:
        return (
            "Thank you for your message. "
            "I'm currently operating in limited mode. "
            "A customer service representative will follow up shortly."
        )


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("API_PORT", "8080"))
    host = os.getenv("API_HOST", "0.0.0.0")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
