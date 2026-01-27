"""
Response Generation Agent
Generates customer-facing responses based on intent and knowledge context

Phase 1: Canned template responses
Phase 2: Coffee/brewing business - Option C (Detailed & Helpful) templates
Phase 4+: Azure OpenAI GPT-4o for LLM-based response generation

Refactored to use BaseAgent pattern and modular formatters for reduced code duplication.
"""

from typing import List

from shared.base_agent import BaseAgent, run_agent
from shared.models import (
    ResponseRequest, GeneratedResponse, Intent, Sentiment,
    extract_message_content, generate_message_id
)

# Import modular formatters
from agents.response_generation.formatters import (
    format_order_status, format_refund_status, format_return_request,
    format_product_info, format_product_recommendation, format_product_comparison, format_brewer_support,
    format_shipping_question, format_subscription, format_gift_card, format_loyalty,
    format_escalation, format_general
)


# Production response generation prompt from Phase 3.5 optimization
# Achieved 88.4% quality score in evaluation (target was >80%)
RESPONSE_GENERATION_PROMPT = """You are a friendly, helpful customer service representative for BrewVi Coffee Company.

BRAND VOICE:
- Warm, approachable, and conversational (like talking to a knowledgeable friend)
- Use the customer's name when available
- Be thorough but not overwhelming
- Show genuine care for customer satisfaction

RESPONSE STRUCTURE:
1. Acknowledge the customer's question/concern
2. Provide clear, helpful information
3. Include relevant details (order status, product info, policy details)
4. Offer additional help or next steps
5. End with an open question to continue assisting

REGISTER MATCHING (CRITICAL):
- Match the customer's communication style and formality level
- If customer is brief and casual, be concise and friendly
- If customer is detailed and formal, provide comprehensive responses
- If customer is frustrated, be empathetic and solution-focused
- If customer is enthusiastic, mirror their positive energy

STYLE GUIDELINES:
- Use markdown formatting for clarity (bold for emphasis, lists for multiple items)
- Keep responses under 200 words unless complexity requires more
- Avoid corporate jargon - use plain, friendly language
- Never say "I cannot" or "Unfortunately" - focus on what you CAN do
- Don't apologize excessively - one apology is enough

KNOWLEDGE CONTEXT:
You will receive relevant information about:
- Order details (status, tracking, items)
- Product information (features, prices, availability)
- Policy details (returns, shipping, loyalty program)

Use this context to provide accurate, specific responses. If information is missing, acknowledge what you can help with and what additional info you need.

IMPORTANT:
- Never make up order numbers, tracking numbers, or specific details
- If you don't have specific information, say so and offer to help find it
- Always provide accurate policy information
- Be honest about what you can and cannot do"""


class ResponseGenerationAgent(BaseAgent):
    """
    Generates customer responses using templates (Phase 1-3) or LLM (Phase 4+).

    Phase 4+: Uses Azure OpenAI GPT-4o for natural, context-aware responses.
    Falls back to template responses when OpenAI is unavailable.
    """

    agent_name = "response-generation-agent"
    default_topic = "response-generator"

    def __init__(self):
        """Initialize the Response Generation Agent."""
        super().__init__()
        # Additional counters
        self.template_responses = 0

    async def process_message(self, content: dict, message: dict) -> dict:
        """
        Generate response based on intent and knowledge context.

        Args:
            content: Extracted message content
            message: Full A2A message

        Returns:
            GeneratedResponse as dict
        """
        request = ResponseRequest(
            request_id=content.get("request_id", generate_message_id()),
            context_id=message.get("contextId", "unknown"),
            customer_message=content.get("customer_message", ""),
            intent=Intent(content.get("intent", "general_inquiry")),
            knowledge_context=content.get("knowledge_context", []),
            sentiment=Sentiment(content.get("sentiment", "neutral")) if content.get("sentiment") else None
        )

        self.logger.info(f"Generating response for intent: {request.intent.value}")

        # Generate response using Azure OpenAI (Phase 4+) or templates (fallback)
        requires_escalation = False

        if self.openai_client:
            response_text = await self._generate_openai_response(request)
            confidence = 0.85
        else:
            response_data = self._generate_template_response(request)
            self.template_responses += 1
            confidence = 0.75

            # Handle tuple returns (response_text, requires_escalation) for returns
            if isinstance(response_data, tuple):
                response_text, requires_escalation = response_data
            else:
                response_text = response_data

        # Determine escalation need
        requires_escalation = requires_escalation or self._check_escalation_needed(request, response_text)

        result = GeneratedResponse(
            request_id=request.request_id,
            context_id=request.context_id,
            response_text=response_text,
            confidence=confidence,
            requires_escalation=requires_escalation
        )

        return result

    def get_demo_messages(self) -> List[dict]:
        """Return sample messages for demo mode - Phase 2 coffee/brewing examples."""
        return [
            {
                "contextId": "demo-001",
                "parts": [{
                    "type": "text",
                    "content": {
                        "customer_message": "Where is my order 10234?",
                        "intent": "order_status",
                        "knowledge_context": [{
                            "type": "order",
                            "order_number": "10234",
                            "status": "shipped",
                            "fulfillment_status": "in_transit",
                            "tracking": {
                                "carrier": "USPS",
                                "tracking_number": "9400123456789",
                                "shipped_date": "2026-01-20T14:30:00Z",
                                "expected_delivery": "2026-01-25T20:00:00Z",
                                "last_location": "Portland Distribution Center"
                            },
                            "items": [
                                {"quantity": 2, "name": "Lamill Signature Blend Coffee Pods (24 ct)"}
                            ],
                            "shipping_address": {"name": "Sarah Martinez"}
                        }]
                    }
                }]
            },
            {
                "contextId": "demo-002",
                "parts": [{
                    "type": "text",
                    "content": {
                        "customer_message": "Tell me about espresso pods",
                        "intent": "product_info",
                        "knowledge_context": [{
                            "type": "product",
                            "name": "Joyride Double Shot Espresso Pods",
                            "price": 29.99,
                            "description": "Premium Italian-style espresso. Bold, rich flavor with crema.",
                            "category": "espresso",
                            "features": ["15g coffee per pod", "Biodegradable", "Authentic Italian espresso"],
                            "in_stock": True
                        }]
                    }
                }]
            },
            {
                "contextId": "demo-003",
                "parts": [{
                    "type": "text",
                    "content": {
                        "customer_message": "I want to return my order",
                        "intent": "return_request",
                        "knowledge_context": [{
                            "type": "order",
                            "order_number": "10125",
                            "total": 35.99,
                            "customer_name": "John Doe",
                            "items": [{"quantity": 1, "name": "Medium Roast Variety Pack"}]
                        }]
                    }
                }]
            }
        ]

    def cleanup(self) -> None:
        """Cleanup with additional response stats."""
        self.logger.info(f"Template responses: {self.template_responses}")
        super().cleanup()

    # ========================================================================
    # Response Generation Methods
    # ========================================================================

    async def _generate_openai_response(self, request: ResponseRequest) -> str:
        """Generate response using Azure OpenAI GPT-4o."""
        try:
            context = self._build_llm_context(request)

            response = await self.openai_client.generate_response(
                context=context,
                system_prompt=RESPONSE_GENERATION_PROMPT,
                temperature=0.7,
                max_tokens=500
            )

            self.logger.debug(f"OpenAI response generated ({len(response)} chars)")
            return response

        except Exception as e:
            self.logger.error(f"OpenAI response generation error: {e}")
            # Fall back to template response
            self.logger.info("Falling back to template response")
            response_data = self._generate_template_response(request)
            if isinstance(response_data, tuple):
                return response_data[0]
            return response_data

    def _build_llm_context(self, request: ResponseRequest) -> str:
        """Build context string for the LLM from request data."""
        context_parts = []

        context_parts.append(f"Customer Message: {request.customer_message}")
        context_parts.append(f"Detected Intent: {request.intent.value}")

        if request.sentiment:
            context_parts.append(f"Customer Sentiment: {request.sentiment.value}")

        if request.knowledge_context:
            context_parts.append("\nRelevant Information:")
            for item in request.knowledge_context:
                item_type = item.get("type", "info")
                if item_type == "order":
                    context_parts.append(f"\nOrder Details:")
                    context_parts.append(f"  - Order Number: {item.get('order_number', 'N/A')}")
                    context_parts.append(f"  - Status: {item.get('status', 'N/A')}")
                    if item.get("tracking"):
                        tracking = item["tracking"]
                        context_parts.append(f"  - Carrier: {tracking.get('carrier', 'N/A')}")
                        context_parts.append(f"  - Tracking: {tracking.get('tracking_number', 'N/A')}")
                        context_parts.append(f"  - Expected Delivery: {tracking.get('expected_delivery', 'N/A')}")
                    if item.get("items"):
                        items_text = ", ".join([f"{i['quantity']}x {i['name']}" for i in item["items"]])
                        context_parts.append(f"  - Items: {items_text}")
                    if item.get("shipping_address", {}).get("name"):
                        context_parts.append(f"  - Customer Name: {item['shipping_address']['name']}")

                elif item_type == "product":
                    context_parts.append(f"\nProduct Information:")
                    context_parts.append(f"  - Name: {item.get('name', 'N/A')}")
                    context_parts.append(f"  - Price: ${item.get('price', 0):.2f}")
                    context_parts.append(f"  - Description: {item.get('description', 'N/A')}")
                    if item.get("features"):
                        context_parts.append(f"  - Features: {', '.join(item['features'][:3])}")
                    context_parts.append(f"  - In Stock: {'Yes' if item.get('in_stock', True) else 'No'}")

                elif item_type == "policy":
                    context_parts.append(f"\nPolicy Information:")
                    context_parts.append(f"  - Topic: {item.get('title', 'N/A')}")
                    context_parts.append(f"  - Details: {item.get('content', item.get('quick_answer', 'N/A'))[:300]}")

                else:
                    context_parts.append(f"\nAdditional Context ({item_type}):")
                    for key, value in item.items():
                        if key not in ["type", "source"] and value:
                            context_parts.append(f"  - {key}: {str(value)[:200]}")

        return "\n".join(context_parts)

    def _generate_template_response(self, request: ResponseRequest):
        """Generate response using template formatters."""
        # Route to intent-specific formatter
        intent_formatters = {
            Intent.ORDER_STATUS: lambda: format_order_status(request.knowledge_context),
            Intent.PRODUCT_INFO: lambda: format_product_info(request.knowledge_context),
            Intent.PRODUCT_RECOMMENDATION: lambda: format_product_recommendation(request.knowledge_context),
            Intent.PRODUCT_COMPARISON: lambda: format_product_comparison(request.knowledge_context),
            Intent.BREWER_SUPPORT: lambda: format_brewer_support(request.knowledge_context),
            Intent.RETURN_REQUEST: lambda: format_return_request(request.knowledge_context),
            Intent.REFUND_STATUS: lambda: format_refund_status(request.knowledge_context),
            Intent.SHIPPING_QUESTION: lambda: format_shipping_question(request.knowledge_context),
            Intent.AUTO_DELIVERY_MANAGEMENT: lambda: format_subscription(request.knowledge_context),
            Intent.GIFT_CARD: lambda: format_gift_card(request.knowledge_context),
            Intent.LOYALTY_PROGRAM: lambda: format_loyalty(request.knowledge_context),
            Intent.ESCALATION_NEEDED: lambda: format_escalation(request.knowledge_context),
        }

        formatter = intent_formatters.get(request.intent)
        if formatter:
            return formatter()
        else:
            return format_general(request.knowledge_context)

    def _check_escalation_needed(self, request: ResponseRequest, response_text: str) -> bool:
        """Determine if escalation is needed based on various factors."""
        if request.intent == Intent.ESCALATION_NEEDED:
            return True

        if request.sentiment == Sentiment.VERY_NEGATIVE:
            return True

        # High-value return check ($50 threshold)
        if request.intent == Intent.RETURN_REQUEST:
            for item in request.knowledge_context:
                if item.get("type") == "order":
                    total = item.get("total", 0)
                    if total > 50.00:
                        return True

        # Check knowledge context for escalation flags
        for item in request.knowledge_context:
            if item.get("escalation_needed") or item.get("escalation_reason"):
                return True

        return False


if __name__ == "__main__":
    run_agent(ResponseGenerationAgent)
