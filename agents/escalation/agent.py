"""
Escalation Agent
Determines when to escalate to human agents based on sentiment and complexity

Phase 1: Simple rule-based escalation
Phase 2: Coffee/brewing business - defined thresholds and auto-approval logic
Phase 4+: Azure OpenAI GPT-4o-mini for intelligent escalation detection

Refactored to use BaseAgent pattern for reduced code duplication.
"""

import asyncio
import httpx
from datetime import datetime
from typing import Dict, Any, List

from shared.base_agent import BaseAgent, run_agent
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


class EscalationAgent(BaseAgent):
    """
    Decides when to escalate conversations to human agents.

    Phase 4+: Uses Azure OpenAI GPT-4o-mini for intelligent escalation detection.
    Falls back to rule-based escalation when OpenAI is unavailable.
    """

    agent_name = "escalation-agent"
    default_topic = "escalation"

    def __init__(self):
        """Initialize the Escalation Agent."""
        super().__init__()
        # Additional counters for escalation tracking
        self.openai_decisions = 0
        self.rule_decisions = 0
        self.escalations_triggered = 0
        # HTTP client for Zendesk API
        self.http_client = httpx.AsyncClient(timeout=10.0)

    async def process_message(self, content: dict, message: dict) -> dict:
        """
        Handle escalation decision for coffee/brewing business.

        Args:
            content: Extracted message content
            message: Full A2A message

        Returns:
            EscalationDecision as dict
        """
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

        return decision

    def get_demo_messages(self) -> List[dict]:
        """Return sample messages for demo mode - Phase 2 coffee/brewing escalation examples."""
        return [
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

    def cleanup(self) -> None:
        """Cleanup with additional escalation stats."""
        self.logger.info(
            f"Escalation stats - OpenAI: {self.openai_decisions}, "
            f"Rules: {self.rule_decisions}, "
            f"Escalations: {self.escalations_triggered}"
        )
        # Close HTTP client safely
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.http_client.aclose())
        except RuntimeError:
            # No running event loop - close synchronously or skip
            pass
        super().cleanup()

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

    def _analyze_mock(self, text: str) -> tuple:
        """
        Legacy method for test compatibility.
        Returns (sentiment, complexity_score) tuple.
        """
        sentiment = self._detect_sentiment(text)

        # Calculate complexity score based on message characteristics
        text_lower = text.lower()
        complexity = 0.5  # Base complexity

        # Very negative = high complexity
        if sentiment == Sentiment.VERY_NEGATIVE:
            complexity = 0.9
        elif sentiment == Sentiment.NEGATIVE:
            complexity = 0.7
        elif sentiment == Sentiment.POSITIVE:
            complexity = 0.3

        return sentiment, complexity

    def _extract_order_amount(self, knowledge_context: list) -> float:
        """Extract order total amount from knowledge context."""
        for item in knowledge_context:
            if item.get("type") == "order":
                return float(item.get("total", 0))
        return None

    def _extract_days_since_order(self, knowledge_context: list) -> int:
        """Calculate days since order was placed."""
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


if __name__ == "__main__":
    run_agent(EscalationAgent)
