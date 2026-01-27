"""
Escalation Agent
Determines when to escalate to human agents based on sentiment and complexity

Phase 1: Simple rule-based escalation
Phase 2: Coffee/brewing business - defined thresholds and auto-approval logic
Phase 4+: Azure OpenAI GPT-4o-mini for intelligent escalation detection
"""

import sys
import os
import asyncio
import httpx
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared import (
    get_factory, shutdown_factory, setup_logging, load_config, handle_graceful_shutdown,
    get_openai_client, shutdown_openai_client
)
from shared.models import (
    EscalationDecision, Sentiment, Priority, create_a2a_message,
    extract_message_content, generate_message_id
)


# Production escalation detection prompt from Phase 3.5 optimization
# Achieved 100% precision and recall in evaluation (target was >90%/>95%)
ESCALATION_DETECTION_PROMPT = """You are an escalation detector for a customer service AI system.

TASK:
Analyze the conversation and determine if it should be escalated to a human agent.

MANDATORY ESCALATION TRIGGERS (always escalate):

1. HEALTH & SAFETY CONCERNS:
   - Allergic reactions, medical issues
   - Product contamination concerns
   - Physical harm or injury

2. EXPLICIT REQUESTS:
   - "I want to speak to a manager"
   - "Transfer me to a human"
   - "Let me talk to someone else"

3. REPEATED CONTACT FRUSTRATION:
   - "This is the Nth time I'm contacting you"
   - "I've already explained this multiple times"
   - Multiple unresolved attempts

4. THREATS OR LEGAL MENTIONS:
   - Legal action threats
   - Lawsuit mentions
   - Regulatory complaints (BBB, FTC)

5. SENSITIVE SITUATIONS (NEW - Critical):
   - Death or bereavement mentions
   - Serious illness context
   - Financial hardship indicators
   - Vulnerable customer signals

ESCALATION INDICATORS (consider escalating):

1. HIGH-VALUE TRANSACTIONS:
   - Returns/refunds over $50
   - Large orders with issues
   - VIP/loyalty members with problems

2. COMPLEX ISSUES:
   - Multiple problems in one conversation
   - Technical issues beyond basic troubleshooting
   - Account security concerns

3. EMOTIONAL INTENSITY:
   - Extreme frustration (beyond normal complaints)
   - Repeated negative sentiment
   - All-caps messages, excessive punctuation

DO NOT ESCALATE (AI can handle):

1. Standard inquiries (order status, product info)
2. Simple returns under $50
3. Basic troubleshooting
4. General questions about policies
5. Subscription changes
6. Normal complaints (one-time, not extreme)

IMPORTANT DISTINCTIONS:

- Frustrated ≠ Escalation needed (normal frustration is OK)
- Angry ≠ Escalation needed (one-time anger is OK)
- Repeated contact frustration = ALWAYS escalate
- Health/safety = ALWAYS escalate immediately
- Sensitive situations (death, illness) = ALWAYS escalate with empathy

OUTPUT FORMAT:
Respond with ONLY a JSON object:
{
  "escalate": true or false,
  "confidence": 0.0-1.0,
  "reason": "brief explanation",
  "priority": "critical" | "urgent" | "high" | "normal" | "low"
}

Do not include any other text."""


class EscalationAgent:
    """
    Decides when to escalate conversations to human agents.

    Phase 4+: Uses Azure OpenAI GPT-4o-mini for intelligent escalation detection.
    Falls back to rule-based escalation when OpenAI is unavailable.
    """

    def __init__(self):
        self.config = load_config()
        self.agent_topic = self.config.get("agent_topic", "escalation")
        self.logger = setup_logging(self.agent_topic, self.config.get("log_level", "INFO"))
        self.logger.info(f"Initializing Escalation Agent: {self.agent_topic}")
        self.factory = get_factory()
        self.transport, self.client = None, None

        # Azure OpenAI client
        self.openai_client = None
        self._use_openai = os.getenv("USE_AZURE_OPENAI", "true").lower() == "true"

        # Statistics
        self.decisions_made = 0
        self.openai_decisions = 0
        self.rule_decisions = 0
        self.escalations_triggered = 0

        self.http_client = httpx.AsyncClient(timeout=10.0)

    async def initialize(self):
        self.logger.info("Creating SLIM transport and A2A client...")
        try:
            self.transport = self.factory.create_slim_transport(f"{self.agent_topic}-transport")
            if self.transport:
                self.client = self.factory.create_a2a_client(self.agent_topic, self.transport)
                self.logger.info("Agent initialized")

            # Initialize Azure OpenAI client (Phase 4+)
            if self._use_openai:
                await self._initialize_openai()

        except Exception as e:
            self.logger.error(f"Init failed: {e}", exc_info=True)

    async def _initialize_openai(self):
        """Initialize Azure OpenAI client for escalation detection."""
        try:
            self.openai_client = get_openai_client()
            success = await self.openai_client.initialize()

            if success:
                self.logger.info("Azure OpenAI client initialized for escalation detection")
            else:
                self.logger.warning("Azure OpenAI not available. Using rule-based escalation.")
                self.openai_client = None
        except Exception as e:
            self.logger.warning(f"Failed to initialize Azure OpenAI: {e}. Using rule-based escalation.")
            self.openai_client = None
    
    async def handle_message(self, message: dict) -> dict:
        """
        Handle escalation decision for coffee/brewing business.
        Phase 4+: Uses Azure OpenAI for intelligent escalation detection.
        Falls back to rule-based logic when OpenAI is unavailable.
        """
        self.decisions_made += 1
        try:
            content = extract_message_content(message)
            customer_message = content.get("customer_message", "")
            intent = content.get("intent", "unknown")
            escalation_reason = content.get("escalation_reason")
            knowledge_context = content.get("knowledge_context", [])

            # Determine escalation using OpenAI (Phase 4+) or rules (fallback)
            if self.openai_client:
                escalation_result = await self._evaluate_escalation_openai(
                    customer_message=customer_message,
                    intent=intent,
                    escalation_reason=escalation_reason,
                    knowledge_context=knowledge_context
                )
                self.openai_decisions += 1
            else:
                escalation_result = self._evaluate_escalation_rules(
                    customer_message=customer_message,
                    intent=intent,
                    escalation_reason=escalation_reason,
                    knowledge_context=knowledge_context
                )
                self.rule_decisions += 1

            should_escalate = escalation_result["should_escalate"]
            reason = escalation_result["reason"]
            priority = escalation_result["priority"]
            auto_approved_action = escalation_result.get("auto_approved_action")

            if should_escalate:
                self.escalations_triggered += 1

            decision = EscalationDecision(
                decision_id=generate_message_id(),
                context_id=message.get("contextId", "unknown"),
                should_escalate=should_escalate,
                reason=reason,
                priority=priority,
                sentiment=self._detect_sentiment(customer_message),
                complexity_score=escalation_result.get("complexity_score", 0.5)
            )

            self.logger.info(f"Escalation decision: {'ESCALATE' if should_escalate else 'AUTO-HANDLE'} "
                           f"(reason={reason}, priority={priority.value})")

            # If escalating, create Zendesk ticket with context
            if should_escalate:
                ticket_id = await self._create_zendesk_ticket(
                    customer_message=customer_message,
                    intent=intent,
                    reason=reason,
                    priority=priority,
                    context=knowledge_context
                )
                decision.zendesk_ticket_id = ticket_id

            # If auto-approved, log the action
            if auto_approved_action:
                self.logger.info(f"Auto-approved action: {auto_approved_action}")
                decision.auto_approved_action = auto_approved_action

            return create_a2a_message(
                "assistant", decision, decision.context_id, message.get("taskId"),
                {
                    "agent": self.agent_topic,
                    "decisions_made": self.decisions_made,
                    "detection_method": "openai" if self.openai_client else "rules"
                }
            )
        except Exception as e:
            self.logger.error(f"Escalation decision error: {e}", exc_info=True)
            return create_a2a_message("assistant", {"error": str(e)}, message.get("contextId", "unknown"))

    async def _evaluate_escalation_openai(
        self, customer_message: str, intent: str,
        escalation_reason: str, knowledge_context: list
    ) -> dict:
        """Evaluate escalation using Azure OpenAI GPT-4o-mini."""
        try:
            # Build context for the LLM
            context_parts = [
                f"Customer Message: {customer_message}",
                f"Detected Intent: {intent}"
            ]

            if escalation_reason:
                context_parts.append(f"Pre-flagged Reason: {escalation_reason}")

            # Add relevant context
            if knowledge_context:
                context_parts.append("\nRelevant Context:")
                for item in knowledge_context:
                    if item.get("type") == "order":
                        context_parts.append(f"  - Order #{item.get('order_number')}: ${item.get('total', 0):.2f}")
                    elif item.get("escalation_reason"):
                        context_parts.append(f"  - Escalation Flag: {item.get('escalation_reason')}")

            context = "\n".join(context_parts)

            result = await self.openai_client.detect_escalation(
                conversation=context,
                system_prompt=ESCALATION_DETECTION_PROMPT,
                temperature=0.0
            )

            # Map priority string to enum
            priority_map = {
                "critical": Priority.URGENT,
                "urgent": Priority.URGENT,
                "high": Priority.HIGH,
                "normal": Priority.NORMAL,
                "low": Priority.LOW
            }
            priority = priority_map.get(result.get("priority", "normal"), Priority.NORMAL)

            return {
                "should_escalate": result.get("escalate", False),
                "reason": result.get("reason", "AI evaluation"),
                "priority": priority,
                "complexity_score": result.get("confidence", 0.5)
            }

        except Exception as e:
            self.logger.error(f"OpenAI escalation detection error: {e}")
            # Fall back to rule-based evaluation
            return self._evaluate_escalation_rules(
                customer_message, intent, escalation_reason, knowledge_context
            )
    
    def _evaluate_escalation_rules(self, customer_message: str, intent: str,
                                  escalation_reason: str, knowledge_context: list) -> dict:
        """
        Evaluate Phase 2 escalation rules for coffee/brewing business.

        Business Rules (from PHASE-2-IMPLEMENTATION-PLAN.md):
        - Missing/stolen deliveries: Always escalate
        - Refund auto-approval: <$50 AND within 30 days
        - Product defects: Always escalate
        - Frustrated customers: After 3 unclear exchanges (tracked in context)
        - Health/safety: IMMEDIATE escalation
        """
        text_lower = customer_message.lower()

        # Priority 1: Health/Safety - IMMEDIATE escalation
        if escalation_reason == "health_safety":
            return {
                "should_escalate": True,
                "reason": "Health/safety concern - allergic reaction or medical issue",
                "priority": Priority.URGENT,
                "complexity_score": 1.0
            }

        # Priority 2: Customer Frustration
        if escalation_reason == "customer_frustration":
            return {
                "should_escalate": True,
                "reason": "Customer frustration detected after multiple unclear exchanges",
                "priority": Priority.URGENT,
                "complexity_score": 0.85
            }

        # Priority 3: Brewer Defect
        if escalation_reason == "brewer_defect":
            return {
                "should_escalate": True,
                "reason": "Brewer defect reported - technical support and warranty replacement needed",
                "priority": Priority.HIGH,
                "complexity_score": 0.80
            }

        # Priority 4: Missing/Stolen Delivery
        if any(word in text_lower for word in ["stolen", "missing", "never received", "didn't receive"]):
            return {
                "should_escalate": True,
                "reason": "Missing or stolen delivery - requires investigation and replacement",
                "priority": Priority.HIGH,
                "complexity_score": 0.75
            }

        # Priority 5: Refund Requests - Check Auto-Approval Rules
        if intent == "refund_status" or intent == "return_request":
            # Check if refund qualifies for auto-approval
            order_amount = self._extract_order_amount(knowledge_context)
            days_since_order = self._extract_days_since_order(knowledge_context)

            if order_amount and days_since_order is not None:
                # Auto-approve if <$50 AND within 30 days
                if order_amount < 50.0 and days_since_order <= 30:
                    return {
                        "should_escalate": False,
                        "reason": f"Refund auto-approved: ${order_amount:.2f} within {days_since_order} days",
                        "priority": Priority.NORMAL,
                        "complexity_score": 0.30,
                        "auto_approved_action": "refund_approved"
                    }

            # Otherwise escalate for manual review
            return {
                "should_escalate": True,
                "reason": f"Refund requires manual review: ${order_amount:.2f if order_amount else 'unknown'}, {days_since_order} days since order",
                "priority": Priority.NORMAL,
                "complexity_score": 0.60
            }

        # Priority 6: Product Defects (non-brewer)
        if any(word in text_lower for word in ["defect", "damaged", "broken", "leak"]):
            return {
                "should_escalate": True,
                "reason": "Product defect reported - quality assurance review needed",
                "priority": Priority.HIGH,
                "complexity_score": 0.70
            }

        # Priority 7: B2B/Wholesale Inquiries (always escalate to sales)
        if any(word in text_lower for word in ["wholesale", "bulk", "business", "office", "company order"]):
            return {
                "should_escalate": True,
                "reason": "B2B/wholesale inquiry - routing to sales team",
                "priority": Priority.NORMAL,
                "complexity_score": 0.65
            }

        # No escalation needed - AI can handle
        return {
            "should_escalate": False,
            "reason": "Standard inquiry - AI-assisted response appropriate",
            "priority": Priority.LOW,
            "complexity_score": 0.40
        }

    def _detect_sentiment(self, text: str) -> Sentiment:
        """Detect customer sentiment from message text."""
        text_lower = text.lower()

        # Very negative sentiment
        if any(w in text_lower for w in ["angry", "furious", "terrible", "worst", "unacceptable", "ridiculous"]):
            return Sentiment.VERY_NEGATIVE

        # Negative sentiment
        elif any(w in text_lower for w in ["problem", "issue", "not working", "disappointed", "frustrated"]):
            return Sentiment.NEGATIVE

        # Positive sentiment
        elif any(w in text_lower for w in ["thanks", "thank you", "great", "love", "excellent", "perfect"]):
            return Sentiment.POSITIVE

        # Neutral default
        return Sentiment.NEUTRAL

    def _analyze_mock(self, message: str) -> tuple[Sentiment, float]:
        """
        Mock sentiment and complexity analysis for testing.
        Returns (sentiment, complexity_score) tuple.
        """
        text_lower = message.lower()
        
        # Determine sentiment using Sentiment enum
        if any(word in text_lower for word in ['terrible', 'awful', 'hate', 'worst', 'unacceptable']):
            sentiment = Sentiment.VERY_NEGATIVE
        elif any(word in text_lower for word in ['problem', 'issue', 'disappointed', 'frustrated']):
            sentiment = Sentiment.NEGATIVE
        elif any(word in text_lower for word in ['great', 'love', 'excellent', 'perfect', 'thanks']):
            sentiment = Sentiment.POSITIVE
        else:
            sentiment = Sentiment.NEUTRAL
        
        # Determine complexity as float score (0.0 to 1.0)
        if any(word in text_lower for word in ['complex', 'complicated', 'multiple', 'several', 'terrible', 'unacceptable']):
            complexity = 0.85  # High complexity
        elif any(word in text_lower for word in ['simple', 'easy', 'quick', 'thanks', 'great']):
            complexity = 0.3   # Low complexity
        else:
            complexity = 0.6   # Medium complexity
        
        return sentiment, complexity

    def _extract_order_amount(self, knowledge_context: list) -> float:
        """Extract order total amount from knowledge context."""
        for item in knowledge_context:
            if item.get("type") == "order":
                return float(item.get("total", 0))
        return None

    def _extract_days_since_order(self, knowledge_context: list) -> int:
        """Calculate days since order was placed."""
        from datetime import datetime

        for item in knowledge_context:
            if item.get("type") == "order":
                order_date_str = item.get("order_date", "")
                if order_date_str:
                    try:
                        order_date = datetime.fromisoformat(order_date_str.replace("Z", "+00:00"))
                        now = datetime.now(order_date.tzinfo)
                        delta = now - order_date
                        return delta.days
                    except:
                        pass
        return None

    async def _create_zendesk_ticket(self, customer_message: str, intent: str,
                                    reason: str, priority: Priority, context: list) -> int:
        """
        Create Zendesk ticket with full context for human agent.
        Phase 2: Enhanced with coffee business context.
        """
        try:
            zendesk_url = self.config.get("zendesk_url", "http://localhost:8002")

            # Build ticket description with context
            description = f"""Customer Inquiry Escalated

**Reason for Escalation:** {reason}

**Customer Message:**
{customer_message}

**Intent Detected:** {intent}

**Context Information:**
"""
            # Add relevant context
            for item in context:
                if item.get("type") == "order":
                    description += f"\n- Order #{item.get('order_number')}: {item.get('status')}"
                elif item.get("type") == "product":
                    description += f"\n- Product: {item.get('name')}"

            description += "\n\n**Recommended Action:** Review and respond within SLA timeframe based on priority."

            # Map priority to Zendesk priority
            zendesk_priority = {
                Priority.URGENT: "urgent",
                Priority.URGENT: "high",
                Priority.HIGH: "high",
                Priority.NORMAL: "normal",
                Priority.LOW: "low"
            }.get(priority, "normal")

            response = await self.http_client.post(
                f"{zendesk_url}/api/v2/tickets.json",
                json={
                    "subject": f"Escalated: {reason[:50]}",
                    "description": description,
                    "priority": zendesk_priority,
                    "type": "problem",
                    "tags": ["escalated", "ai-agent", intent.replace("_", "-")],
                    "requester_id": 5001  # Mock customer ID
                }
            )

            if response.status_code == 200 or response.status_code == 201:
                ticket = response.json().get("ticket", {})
                ticket_id = ticket.get("id", 9999)
                self.logger.info(f"Created Zendesk ticket {ticket_id} with priority {zendesk_priority}")
                return ticket_id
            else:
                self.logger.error(f"Zendesk API returned status {response.status_code}")

        except Exception as e:
            self.logger.error(f"Zendesk ticket creation failed: {e}", exc_info=True)

        return 9999  # Mock ticket ID on failure
    
    def cleanup(self):
        self.logger.info("Cleaning up Escalation Agent...")
        self.logger.info(
            f"Statistics - Total: {self.decisions_made}, "
            f"OpenAI: {self.openai_decisions}, "
            f"Rules: {self.rule_decisions}, "
            f"Escalations: {self.escalations_triggered}"
        )

        # Log token usage if available
        if self.openai_client:
            usage = self.openai_client.get_total_usage()
            self.logger.info(
                f"Token usage - Total: {usage['total_tokens']}, "
                f"Cost: ${usage['total_cost']:.4f}"
            )

        asyncio.create_task(self.http_client.aclose())
        shutdown_factory()
    
    async def run_demo_mode(self):
        """Run in demo mode - Phase 2 coffee/brewing escalation examples."""
        self.logger.info("Running in DEMO MODE - Phase 2 Coffee/Brewing Escalation Logic")

        samples = [
            {
                "contextId": "demo-001",
                "parts": [{
                    "type": "text",
                    "content": {
                        "customer_message": "I need a refund for my damaged coffee pods",
                        "intent": "refund_status",
                        "knowledge_context": [{
                            "type": "order",
                            "order_number": "10512",
                            "total": 49.98,
                            "order_date": "2026-01-10T13:20:00Z"
                        }]
                    }
                }]
            },
            {
                "contextId": "demo-002",
                "parts": [{
                    "type": "text",
                    "content": {
                        "customer_message": "My brewer stopped working completely!",
                        "intent": "brewer_support",
                        "escalation_reason": "brewer_defect"
                    }
                }]
            },
            {
                "contextId": "demo-003",
                "parts": [{
                    "type": "text",
                    "content": {
                        "customer_message": "I broke out in a rash after drinking your coffee",
                        "intent": "complaint",
                        "escalation_reason": "health_safety"
                    }
                }]
            }
        ]

        for msg in samples:
            self.logger.info("=" * 60)
            result = await self.handle_message(msg)
            decision_content = extract_message_content(result)
            self.logger.info(f"Decision: {'ESCALATE' if decision_content.get('should_escalate') else 'AUTO-HANDLE'}")
            self.logger.info(f"Reason: {decision_content.get('reason')}")
            self.logger.info(f"Priority: {decision_content.get('priority')}")
            if decision_content.get("zendesk_ticket_id"):
                self.logger.info(f"Zendesk Ticket: {decision_content.get('zendesk_ticket_id')}")
            if decision_content.get("auto_approved_action"):
                self.logger.info(f"Auto-Approved: {decision_content.get('auto_approved_action')}")
            await asyncio.sleep(2)

        self.logger.info("Demo complete. Keeping alive for health checks...")
        while True:
            await asyncio.sleep(30)

async def main():
    agent = EscalationAgent()
    handle_graceful_shutdown(agent.logger, agent.cleanup)
    try:
        await agent.initialize()
        await agent.run_demo_mode() if agent.client is None else await asyncio.sleep(float('inf'))
    except KeyboardInterrupt:
        pass
    finally:
        agent.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
