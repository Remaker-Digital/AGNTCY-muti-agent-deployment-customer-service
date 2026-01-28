"""
Shared data models for AGNTCY Multi-Agent Customer Service Platform
Defines message formats, agent cards, and data structures for inter-agent communication
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

# =============================================================================
# Enumerations
# =============================================================================


class Intent(str, Enum):
    """Customer intent categories for classification - Phase 2 coffee/brewing business."""

    # Order-related intents
    ORDER_STATUS = "order_status"
    ORDER_MODIFICATION = "order_modification"
    REFUND_STATUS = "refund_status"

    # Product-related intents
    PRODUCT_INFO = "product_info"
    PRODUCT_INQUIRY = "product_inquiry"  # Kept for backwards compatibility
    PRODUCT_RECOMMENDATION = "product_recommendation"
    PRODUCT_COMPARISON = "product_comparison"

    # Coffee/brewing specific
    BREWER_SUPPORT = "brewer_support"
    AUTO_DELIVERY_MANAGEMENT = "auto_delivery_management"

    # Customer service
    RETURN_REQUEST = "return_request"
    SHIPPING_QUESTION = "shipping_question"
    GIFT_CARD = "gift_card"
    LOYALTY_PROGRAM = "loyalty_program"

    # Legacy/General
    PAYMENT_ISSUE = "payment_issue"
    ACCOUNT_SUPPORT = "account_support"
    GENERAL_INQUIRY = "general_inquiry"
    COMPLAINT = "complaint"

    # Escalation
    ESCALATION_NEEDED = "escalation_needed"
    UNKNOWN = "unknown"


class Sentiment(str, Enum):
    """Customer sentiment analysis results."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class Priority(str, Enum):
    """Issue priority levels for escalation."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Language(str, Enum):
    """Supported languages for multi-language support (Phase 4)."""

    EN = "en"  # English (Phase 1-5)
    FR_CA = "fr-ca"  # Canadian French (Phase 4+)
    ES = "es"  # Spanish (Phase 4+)


# =============================================================================
# Agent Cards (AGNTCY SDK Agent Metadata)
# =============================================================================


@dataclass
class AgentCard:
    """
    Agent metadata card for AGNTCY directory registration.

    Used to describe agent capabilities, topics, and protocols
    for service discovery and routing.
    """

    name: str
    topic: str
    protocol: str  # "A2A" or "MCP"
    transport: str  # "SLIM" or "NATS"
    description: str
    capabilities: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    language: Language = Language.EN

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


# =============================================================================
# Customer Messages
# =============================================================================


@dataclass
class CustomerMessage:
    """
    Incoming customer message from any channel (chat, email, etc.).

    This is the entry point to the multi-agent system, typically
    received by the Intent Classification Agent.
    """

    message_id: str
    customer_id: str
    content: str
    channel: str  # "chat", "email", "phone"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    context_id: Optional[str] = None  # Conversation thread ID
    language: Language = Language.EN
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for AGNTCY message payload."""
        return asdict(self)


# =============================================================================
# Intent Classification Messages
# =============================================================================


@dataclass
class IntentClassificationResult:
    """
    Output from Intent Classification Agent.

    Determines what the customer wants and routes to appropriate handlers.
    """

    message_id: str
    context_id: str
    intent: Intent
    confidence: float  # 0.0 to 1.0
    extracted_entities: Dict[str, Any] = field(default_factory=dict)
    language: Language = Language.EN
    routing_suggestion: Optional[str] = None  # Which agent topic to route to
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for AGNTCY message payload."""
        return asdict(self)


# =============================================================================
# Knowledge Retrieval Messages
# =============================================================================


@dataclass
class KnowledgeQuery:
    """
    Query sent to Knowledge Retrieval Agent.

    Searches internal documentation, FAQs, product catalogs, etc.
    """

    query_id: str
    context_id: str
    query_text: str
    intent: Intent
    filters: Dict[str, Any] = field(default_factory=dict)
    max_results: int = 5
    language: Language = Language.EN

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for AGNTCY message payload."""
        return asdict(self)


@dataclass
class KnowledgeResult:
    """
    Knowledge base search results returned to requesting agent.
    """

    query_id: str
    context_id: str
    results: List[Dict[str, Any]] = field(default_factory=list)
    total_results: int = 0
    search_time_ms: float = 0.0
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for AGNTCY message payload."""
        return asdict(self)


# =============================================================================
# Response Generation Messages
# =============================================================================


@dataclass
class ResponseRequest:
    """
    Request to Response Generation Agent to create customer response.

    Combines intent, knowledge, and context to generate appropriate reply.
    """

    request_id: str
    context_id: str
    customer_message: str
    intent: Intent
    knowledge_context: List[Dict[str, Any]] = field(default_factory=list)
    sentiment: Optional[Sentiment] = None
    language: Language = Language.EN
    personalization: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for AGNTCY message payload."""
        return asdict(self)


@dataclass
class GeneratedResponse:
    """
    Generated response from Response Generation Agent.
    """

    request_id: str
    context_id: str
    response_text: str
    confidence: float
    requires_escalation: bool = False
    suggested_actions: List[str] = field(default_factory=list)
    response_type: str = "text"  # "text", "template", "rich_card"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for AGNTCY message payload."""
        return asdict(self)


# =============================================================================
# Escalation Messages
# =============================================================================


@dataclass
class EscalationDecision:
    """
    Decision from Escalation Agent on whether to escalate to human.

    Based on sentiment analysis, complexity scoring, and business rules.
    """

    decision_id: str
    context_id: str
    should_escalate: bool
    reason: str
    priority: Priority
    sentiment: Sentiment
    complexity_score: float  # 0.0 (simple) to 1.0 (complex)
    assigned_queue: Optional[str] = None  # Zendesk queue name
    zendesk_ticket_id: Optional[int] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for AGNTCY message payload."""
        return asdict(self)


# =============================================================================
# Analytics Messages
# =============================================================================


@dataclass
class AnalyticsEvent:
    """
    Event sent to Analytics Agent for KPI tracking and reporting.

    Analytics Agent listens passively to all agent traffic to collect metrics.
    """

    event_id: str
    event_type: (
        str  # "conversation_started", "intent_classified", "response_generated", etc.
    )
    context_id: str
    agent_source: str  # Which agent generated this event
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metrics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for AGNTCY message payload."""
        return asdict(self)


# =============================================================================
# AGNTCY Message Wrappers
# =============================================================================


def create_a2a_message(
    role: str,
    content: Any,
    context_id: str,
    task_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create an A2A protocol message for agent-to-agent communication.

    A2A messages follow AGNTCY SDK Message format with:
    - messageId: Unique message identifier
    - role: Message role (user, assistant, system)
    - parts: Message content parts
    - contextId: Conversation/session identifier
    - taskId: Optional task tracking identifier
    - metadata: Additional metadata

    Args:
        role: Message role ("user", "assistant", "system")
        content: Message payload (will be converted to dict if dataclass)
        context_id: Conversation context ID
        task_id: Optional task tracking ID
        metadata: Optional additional metadata

    Returns:
        Dictionary formatted as AGNTCY A2A message

    Example:
        intent_result = IntentClassificationResult(...)
        message = create_a2a_message(
            role="assistant",
            content=intent_result,
            context_id="conv-123",
            task_id="classify-456"
        )
    """
    import uuid

    # Convert dataclass to dict if needed
    if hasattr(content, "to_dict"):
        content_dict = content.to_dict()
    elif isinstance(content, dict):
        content_dict = content
    else:
        content_dict = {"value": str(content)}

    return {
        "messageId": str(uuid.uuid4()),
        "role": role,
        "parts": [{"type": "text", "content": content_dict}],
        "contextId": context_id,
        "taskId": task_id or str(uuid.uuid4()),
        "metadata": metadata or {},
    }


def extract_message_content(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract content payload from AGNTCY A2A message.

    Args:
        message: AGNTCY A2A message dictionary

    Returns:
        Content dictionary from first message part

    Example:
        def handle_message(message):
            content = extract_message_content(message)
            intent = Intent(content["intent"])
    """
    if "parts" in message and len(message["parts"]) > 0:
        first_part = message["parts"][0]
        return first_part.get("content", {})
    return {}


# =============================================================================
# Utility Functions
# =============================================================================


def generate_message_id() -> str:
    """Generate unique message ID for tracking."""
    import uuid

    return f"msg-{uuid.uuid4().hex[:12]}"


def generate_context_id() -> str:
    """Generate unique conversation context ID."""
    import uuid

    return f"ctx-{uuid.uuid4().hex[:12]}"


def generate_task_id() -> str:
    """Generate unique task ID for request tracking."""
    import uuid

    return f"task-{uuid.uuid4().hex[:12]}"
