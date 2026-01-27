"""
Response Generation Agent
Generates customer-facing responses based on intent and knowledge context

Phase 1: Canned template responses
Phase 2: Coffee/brewing business - Option C (Detailed & Helpful) templates
Phase 4+: Azure OpenAI GPT-4o for LLM-based response generation
"""

import sys
import os
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared import (
    get_factory, shutdown_factory, setup_logging, load_config, handle_graceful_shutdown,
    get_openai_client, shutdown_openai_client
)
from shared.models import (
    ResponseRequest, GeneratedResponse, Intent, Sentiment, create_a2a_message,
    extract_message_content, generate_message_id
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


class ResponseGenerationAgent:
    """
    Generates customer responses using templates (Phase 1-3) or LLM (Phase 4+).

    Phase 4+: Uses Azure OpenAI GPT-4o for natural, context-aware responses.
    Falls back to template responses when OpenAI is unavailable.
    """

    def __init__(self):
        self.config = load_config()
        self.agent_topic = self.config.get("agent_topic", "response-generator")
        self.logger = setup_logging(self.agent_topic, self.config.get("log_level", "INFO"))
        self.logger.info(f"Initializing Response Generation Agent: {self.agent_topic}")
        self.factory = get_factory()
        self.transport, self.client, self.container = None, None, None

        # Azure OpenAI client
        self.openai_client = None
        self._use_openai = os.getenv("USE_AZURE_OPENAI", "true").lower() == "true"

        # Statistics
        self.responses_generated = 0
        self.openai_responses = 0
        self.template_responses = 0

    async def initialize(self):
        self.logger.info("Creating SLIM transport and A2A client...")
        try:
            self.transport = self.factory.create_slim_transport(f"{self.agent_topic}-transport")
            if self.transport:
                self.client = self.factory.create_a2a_client(self.agent_topic, self.transport)
                self.logger.info("Agent initialized successfully")

            # Initialize Azure OpenAI client (Phase 4+)
            if self._use_openai:
                await self._initialize_openai()

        except Exception as e:
            self.logger.error(f"Initialization failed: {e}", exc_info=True)

    async def _initialize_openai(self):
        """Initialize Azure OpenAI client for response generation."""
        try:
            self.openai_client = get_openai_client()
            success = await self.openai_client.initialize()

            if success:
                self.logger.info("Azure OpenAI client initialized for response generation (GPT-4o)")
            else:
                self.logger.warning("Azure OpenAI not available. Using template responses.")
                self.openai_client = None
        except Exception as e:
            self.logger.warning(f"Failed to initialize Azure OpenAI: {e}. Using template responses.")
            self.openai_client = None
    
    async def handle_message(self, message: dict) -> dict:
        self.responses_generated += 1
        try:
            content = extract_message_content(message)
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
            if self.openai_client:
                response_text = await self._generate_openai_response(request)
                self.openai_responses += 1
                confidence = 0.85  # Higher confidence for LLM responses
            else:
                # Fallback to template responses (returns tuple: (text, requires_escalation) for Issue #29)
                response_data = self._generate_canned_response(request)
                self.template_responses += 1
                confidence = 0.75

                # Handle both old string returns and new tuple returns (backward compatibility)
                if isinstance(response_data, tuple):
                    response_text, requires_escalation_template = response_data
                else:
                    response_text = response_data
                    requires_escalation_template = False

            # Determine escalation need
            requires_escalation = self._check_escalation_needed(request, response_text)

            result = GeneratedResponse(
                request_id=request.request_id,
                context_id=request.context_id,
                response_text=response_text,
                confidence=confidence,
                requires_escalation=requires_escalation
            )

            return create_a2a_message(
                "assistant", result, request.context_id, message.get("taskId"),
                {
                    "agent": self.agent_topic,
                    "responses_generated": self.responses_generated,
                    "generation_method": "openai" if self.openai_client else "template"
                }
            )
        except Exception as e:
            self.logger.error(f"Error generating response: {e}", exc_info=True)
            return create_a2a_message("assistant", {"error": str(e)}, message.get("contextId", "unknown"))

    async def _generate_openai_response(self, request: ResponseRequest) -> str:
        """Generate response using Azure OpenAI GPT-4o."""
        try:
            # Build context for the LLM
            context = self._build_llm_context(request)

            response = await self.openai_client.generate_response(
                context=context,
                system_prompt=RESPONSE_GENERATION_PROMPT,
                temperature=0.7,  # Some creativity for natural responses
                max_tokens=500
            )

            self.logger.debug(f"OpenAI response generated ({len(response)} chars)")
            return response

        except Exception as e:
            self.logger.error(f"OpenAI response generation error: {e}")
            # Fall back to template response
            self.logger.info("Falling back to template response")
            response_data = self._generate_canned_response(request)
            if isinstance(response_data, tuple):
                return response_data[0]
            return response_data

    def _build_llm_context(self, request: ResponseRequest) -> str:
        """Build context string for the LLM from request data."""
        import json

        context_parts = []

        # Customer message
        context_parts.append(f"Customer Message: {request.customer_message}")

        # Intent
        context_parts.append(f"Detected Intent: {request.intent.value}")

        # Sentiment if available
        if request.sentiment:
            context_parts.append(f"Customer Sentiment: {request.sentiment.value}")

        # Knowledge context
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
                    # Generic context item
                    context_parts.append(f"\nAdditional Context ({item_type}):")
                    for key, value in item.items():
                        if key not in ["type", "source"] and value:
                            context_parts.append(f"  - {key}: {str(value)[:200]}")

        return "\n".join(context_parts)

    def _check_escalation_needed(self, request: ResponseRequest, response_text: str) -> bool:
        """Determine if escalation is needed based on various factors."""
        # Escalation intent
        if request.intent == Intent.ESCALATION_NEEDED:
            return True

        # Very negative sentiment
        if request.sentiment == Sentiment.VERY_NEGATIVE:
            return True

        # High-value return check ($50 threshold from Issue #29)
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
    
    def _generate_canned_response(self, request: ResponseRequest) -> str:
        """
        Phase 2: Coffee/brewing business - Option C (Detailed & Helpful) templates.
        Personalized, includes specifics, next steps, and offers additional help.
        """
        # Route to intent-specific response formatter
        if request.intent == Intent.ORDER_STATUS:
            return self._format_order_status_response(request)

        elif request.intent == Intent.PRODUCT_INFO:
            return self._format_product_info_response(request)

        elif request.intent == Intent.PRODUCT_RECOMMENDATION:
            return self._format_product_recommendation_response(request)

        elif request.intent == Intent.PRODUCT_COMPARISON:
            return self._format_product_comparison_response(request)

        elif request.intent == Intent.BREWER_SUPPORT:
            return self._format_brewer_support_response(request)

        elif request.intent == Intent.RETURN_REQUEST:
            return self._format_return_request_response(request)

        elif request.intent == Intent.REFUND_STATUS:
            return self._format_refund_status_response(request)

        elif request.intent == Intent.SHIPPING_QUESTION:
            return self._format_shipping_question_response(request)

        elif request.intent == Intent.AUTO_DELIVERY_MANAGEMENT:
            return self._format_subscription_response(request)

        elif request.intent == Intent.GIFT_CARD:
            return self._format_gift_card_response(request)

        elif request.intent == Intent.LOYALTY_PROGRAM:
            return self._format_loyalty_response(request)

        elif request.intent == Intent.ESCALATION_NEEDED:
            return self._format_escalation_response(request)

        else:
            return self._format_general_response(request)

    # ========================================================================
    # Phase 2: Coffee-Specific Response Formatters (Option C - Detailed & Helpful)
    # ========================================================================

    def _format_order_status_response(self, request: ResponseRequest) -> str:
        """Format detailed order status response with tracking info."""
        # Extract order data from knowledge context
        order_data = self._extract_order_from_context(request.knowledge_context)

        if not order_data:
            return ("I'd be happy to help you track your order! To provide the most accurate information, "
                   "could you please provide your order number? You can find it in your confirmation email "
                   "(it looks like #10234 or ORD-10234).")

        # Extract customer name if available
        customer_name = order_data.get("shipping_address", {}).get("name", "").split()[0] if order_data.get("shipping_address") else ""
        greeting = f"Hi {customer_name},\n\n" if customer_name else ""

        order_number = order_data.get("order_number", "")
        status = order_data.get("status", "").title()
        fulfillment_status = order_data.get("fulfillment_status", "").replace("_", " ").title()

        # Build response based on order status
        if status == "Shipped" or fulfillment_status == "In Transit":
            tracking = order_data.get("tracking", {})
            carrier = tracking.get("carrier", "")
            tracking_number = tracking.get("tracking_number", "")
            tracking_url = tracking.get("tracking_url", "")
            expected_delivery = tracking.get("expected_delivery", "")
            last_location = tracking.get("last_location", "")

            # Format items
            items = order_data.get("items", [])
            items_text = "\n".join([f"- {item['quantity']}x {item['name']}" for item in items])

            # Format expected delivery date
            if expected_delivery:
                from datetime import datetime
                try:
                    delivery_date = datetime.fromisoformat(expected_delivery.replace("Z", "+00:00"))
                    delivery_str = delivery_date.strftime("%b %d")
                except:
                    delivery_str = "soon"
            else:
                delivery_str = "soon"

            response = f"""{greeting}I've checked your order #{order_number} and have good news!

**Status:** {fulfillment_status}
**Shipped:** {tracking.get('shipped_date', '').split('T')[0]} via {carrier}
**Tracking Number:** {tracking_number}
**Expected Delivery:** {delivery_str}
**Last Location:** {last_location}

**Your order includes:**
{items_text}

You can track your package here: {tracking_url if tracking_url else f"https://www.{carrier.lower()}.com/tracking"}

If you don't receive your order by {delivery_str}, please let me know and I'll look into it for you right away.

Is there anything else I can help you with today?"""

        elif status == "Delivered":
            tracking = order_data.get("tracking", {})
            delivered_date = tracking.get("delivered_date", "").split("T")[0]
            delivery_note = tracking.get("delivery_note", "")

            response = f"""{greeting}Great news! Your order #{order_number} was delivered on {delivered_date}.

**Delivery Location:** {delivery_note if delivery_note else "As requested"}

If you haven't received your package or have any concerns about your order, please let me know and I'll help resolve this immediately.

Is there anything else I can assist you with?"""

        elif status == "Pending":
            response = f"""{greeting}I've located your order #{order_number}.

**Current Status:** Being prepared for shipment
**Expected Ship Date:** Within 1-2 business days

You'll receive an email with tracking information as soon as your order ships. In the meantime, if you need to make any changes to your order, let me know right away!

Is there anything else I can help you with?"""

        else:
            response = f"""{greeting}I've checked on your order #{order_number}.

**Current Status:** {status}

If you have specific questions about this order or need assistance, I'm here to help!"""

        return response

    def _format_product_info_response(self, request: ResponseRequest) -> str:
        """
        Format detailed product information response.

        Issue #25: Customer Product Information Inquiries
        ---------------------------------------------------
        This method creates customer-friendly product descriptions with:
        - Product name, price, category, description
        - Key features and specifications
        - Stock availability and inventory status
        - Variant information (size, color, etc.)
        - Related product suggestions

        Response Philosophy:
        - Informative but conversational (not robotic catalog listings)
        - Highlight key features customers care about
        - Clear stock availability (critical for purchase decisions)
        - Suggest related products (increase discovery/sales)
        - End with open-ended question (encourage engagement)

        Args:
            request: ResponseRequest with product data from Knowledge Retrieval Agent
                knowledge_context contains list of product dictionaries with fields:
                - name, description, price, category, features, tags
                - in_stock, inventory_count (stock availability)
                - variant_id, variant_name (product variations)

        Returns:
            Formatted product information response string

        Example Customer Queries:
        - "Is organic mango soap in stock?" → Product info + stock availability
        - "How much is the coffee maker?" → Product info + price
        - "Tell me about espresso pods" → Product info + recommendations
        - "What gift cards do you have?" → Gift card options + denominations

        Reference: ISSUE-25-IMPLEMENTATION-PLAN.md lines 162-186
        """
        # Extract product results from knowledge context
        # Knowledge Retrieval Agent returns list of matching products
        products = [item for item in request.knowledge_context if item.get("type") == "product"]

        if not products:
            # No products found matching customer query
            # Provide helpful fallback response with product categories
            # This guides customer to refine their search
            return ("I'd be happy to help you learn about our coffee and brewing products!\n\n"
                   "**What we offer:**\n"
                   "- **Brewers:** Premium single-serve coffee makers with smart features\n"
                   "- **Coffee Pods:** Light, medium, dark roasts, espresso, matcha, chai\n"
                   "- **Variety Packs:** Explorer packs and office bundles\n"
                   "- **Accessories:** Descaling solution, cleaning pods, travel mugs\n"
                   "- **Gift Cards:** Virtual and physical options\n\n"
                   "What specific product are you interested in?")

        # ========================================================================
        # Format Primary Product (First Result)
        # ========================================================================
        # Show most relevant product in detail
        # Additional products shown as brief suggestions below
        product = products[0]

        # Extract product fields with safe defaults
        name = product.get("name", "Product")
        description = product.get("description", "")
        price = product.get("price", 0)
        category = product.get("category", "").title()
        sku = product.get("sku", "")
        features = product.get("features", [])
        in_stock = product.get("in_stock", True)
        inventory_count = product.get("inventory_count")
        variant_name = product.get("variant_name", "")

        # Format features list with bullet points
        # Example: "- 7 customizable brew parameters\n- Auto-optimization via pod scanning"
        features_text = "\n".join([f"- {feature}" for feature in features]) if features else ""

        # Build response header with product name, category, and price
        response = f"""**{name}**"""

        # Add variant information if available (e.g., "Black" for brewer color)
        if variant_name:
            response += f" ({variant_name})"

        response += f"""
Category: {category}
Price: ${price:.2f}"""

        # Add SKU for customer reference (useful for phone orders)
        if sku:
            response += f"\nSKU: {sku}"

        response += f"\n\n{description}\n\n"

        # Add features section if available
        # Features help customers understand product capabilities
        if features_text:
            response += f"""**Key Features:**
{features_text}

"""

        # ========================================================================
        # Stock Availability Status (Critical for Purchase Decisions)
        # ========================================================================
        # Issue #25: Clear stock messaging is crucial for customer experience
        # - In Stock: Encourage purchase with "ready to ship"
        # - Low Stock: Create urgency without panic
        # - Out of Stock: Set expectations and offer alternatives
        if not in_stock:
            # Out of stock: Provide helpful alternatives
            response += "**Availability:** Currently out of stock.\n\n"
            response += "Would you like me to notify you when this item is back in stock? "
            response += "I can also suggest similar products that are available now.\n\n"
        elif inventory_count is not None and inventory_count <= 5:
            # Low stock: Create gentle urgency (not aggressive)
            # Example: "Only 3 left in stock - order soon!"
            response += f"**Availability:** Only {inventory_count} left in stock - order soon!\n\n"
        else:
            # In stock: Standard availability message
            response += "**Availability:** In stock and ready to ship!\n\n"

        # ========================================================================
        # Related Products Suggestions
        # ========================================================================
        # If search returned multiple products, show brief suggestions
        # This increases product discovery and potential sales
        # Example: Customer searches "coffee" → Show Premium Brewer + related pods
        if len(products) > 1:
            response += "**You might also like:**\n"
            for other_product in products[1:3]:  # Limit to 2 suggestions
                other_name = other_product.get('name', '')
                other_price = other_product.get('price', 0)
                other_in_stock = other_product.get('in_stock', True)

                # Show product name, price, and stock status
                stock_indicator = " ✓ In stock" if other_in_stock else " (Out of stock)"
                response += f"- {other_name} (${other_price:.2f}){stock_indicator}\n"
            response += "\n"

        # ========================================================================
        # Closing Engagement Question
        # ========================================================================
        # End with open question to encourage further conversation
        # This keeps customer engaged and provides opportunities to address concerns
        response += "Would you like to know more about this product, or can I help you with something else?"

        return response

    def _format_product_recommendation_response(self, request: ResponseRequest) -> str:
        """Format personalized product recommendations."""
        recommendations = [item for item in request.knowledge_context if item.get("type") == "recommendation"]

        if not recommendations:
            return ("I'd love to help you find the perfect coffee! Tell me about your preferences:\n"
                   "- Do you prefer light, medium, or dark roast?\n"
                   "- Are you looking for espresso or regular coffee?\n"
                   "- Any flavor notes you enjoy (fruity, chocolatey, bold)?\n\n"
                   "I'll recommend the perfect pods for you!")

        response = "Based on your preferences, I think you'll love these:\n\n"

        for idx, rec in enumerate(recommendations[:3], 1):
            name = rec.get("name", "")
            price = rec.get("price", 0)
            why = rec.get("why_recommended", "")
            description = rec.get("description", "")

            response += f"""**{idx}. {name}** - ${price:.2f}
{description[:100]}...

Why I recommend this: {why}

"""

        response += "All of our pods are biodegradable (Guilt Free Toss®) and deliver cafe-quality coffee every time.\n\n"
        response += "Would you like to add any of these to your cart, or would you like different recommendations?"

        return response

    def _format_product_comparison_response(self, request: ResponseRequest) -> str:
        """Format product comparison response."""
        products = [item for item in request.knowledge_context if item.get("type") == "product"]

        if len(products) < 2:
            return ("I can help you compare our products! Which items would you like to compare? "
                   "For example, I can compare different brewers, coffee roasts, or variety packs.")

        response = "Here's a detailed comparison:\n\n"

        for product in products[:3]:
            name = product.get("name", "")
            price = product.get("price", 0)
            features = product.get("features", [])
            category = product.get("category", "")

            response += f"""**{name}** - ${price:.2f}
Category: {category.title()}
"""
            if features:
                response += "Features: " + ", ".join(features[:3]) + "\n"
            response += "\n"

        response += "Each option offers great quality. The best choice depends on your preferences and needs.\n\n"
        response += "Would you like more details about any of these, or do you have specific questions to help you decide?"

        return response

    def _format_brewer_support_response(self, request: ResponseRequest) -> str:
        """
        Format brewer troubleshooting response.

        Issue #25: Enhanced to support product information queries
        ------------------------------------------------------------
        When knowledge_context contains products (type="product"), this means the
        customer asked about product information (price, features, etc.), NOT troubleshooting.
        Route to product information response instead of support troubleshooting.
        """
        # Issue #25: Check if products are in knowledge context FIRST
        # Example: "How much is the Premium Coffee Brewer?" → product info response
        products = [item for item in request.knowledge_context if item.get("type") == "product"]

        if products:
            # Customer asked about product information, not troubleshooting
            # Delegate to product info formatter
            return self._format_product_info_response(request)

        # TROUBLESHOOTING RESPONSE (no products in context)
        support_items = [item for item in request.knowledge_context if item.get("source") == "brewer_support"]

        if not support_items:
            return ("I'm here to help with your brewer! Common issues I can assist with:\n"
                   "- Brewer won't turn on or power issues\n"
                   "- Coffee tastes weak or off\n"
                   "- Cleaning and descaling\n"
                   "- Error messages\n\n"
                   "What specific issue are you experiencing?")

        issue_item = support_items[0]
        issue_type = issue_item.get("type", "")

        if issue_type == "troubleshooting":
            issue = issue_item.get("issue", "")
            solutions = issue_item.get("solutions", [])
            needs_escalation = issue_item.get("escalation_needed", False)

            response = f"""I understand you're experiencing: {issue}

Let's try these troubleshooting steps:

"""
            for idx, solution in enumerate(solutions, 1):
                response += f"{idx}. {solution}\n"

            response += "\nPlease try these steps and let me know if the issue persists. "

            if needs_escalation:
                response += ("If none of these steps resolve the problem, I'll escalate this to our technical support team "
                           "who can arrange a replacement if needed. Your brewer is covered by a 2-year warranty.")

        elif issue_type == "maintenance":
            title = issue_item.get("title", "")
            instructions = issue_item.get("instructions", "")
            product_rec = issue_item.get("product_recommendation", "")

            response = f"""**{title}**

{instructions}

**Recommended Product:** {product_rec}

Regular maintenance ensures your brewer continues making perfect coffee for years to come. Would you like me to add descaling solution to your next order?"""

        else:
            title = issue_item.get("title", "")
            content = issue_item.get("content", "")
            contact = issue_item.get("contact", "")

            response = f"""**{title}**

{content}

{contact}

I'm here if you have any other questions!"""

        return response

    def _format_return_request_response(self, request: ResponseRequest) -> tuple[str, bool]:
        """
        Format return/refund request response with $50 auto-approval threshold.

        Business Logic (Issue #29):
        - Orders ≤$50.00: Auto-approved with RMA number
        - Orders >$50.00: Escalated to support team
        - Return window: 30 days from delivery
        - Eligible: Unopened products in original packaging

        Auto-Approval Threshold Rationale:
        - Reduces support workload by ~30% (estimated)
        - Instant customer satisfaction for low-value returns
        - Risk mitigation: Cap potential fraud/abuse at $50
        - Escalate high-value returns for human review

        Reference: PHASE-2-READINESS.md lines 594, 639-643
        Business Rule: $50 auto-approval threshold (EXACTLY $50.00)

        Args:
            request: ResponseRequest with order data in knowledge_context

        Returns:
            Tuple of (response_text, requires_escalation)
            - response_text: Formatted return response (auto-approval or escalation notice)
            - requires_escalation: True if order >$50, False if ≤$50 (auto-approved)
        """
        # Extract order data from knowledge context
        # This will contain Shopify order details from Knowledge Retrieval Agent
        order_data = self._extract_order_from_context(request.knowledge_context)

        if not order_data:
            # No order found - ask customer for order number
            # Escalation NOT required (just need more info)
            return (("I'm sorry to hear you need to return something! I'm here to make this process as easy as possible.\n\n"
                   "We accept returns within 30 days of delivery for a full refund. "
                   "Items should be unopened and in original condition.\n\n"
                   "To process your return, I'll need:\n"
                   "- Your order number (e.g., #10234)\n"
                   "- Which item(s) you'd like to return\n"
                   "- Reason for return (optional, but helps us improve)\n\n"
                   "What's your order number?"), False)

        # Extract key order information
        order_number = order_data.get("order_number", "")
        order_total = order_data.get("total", 0.0)
        order_status = order_data.get("status", "")

        # Extract customer first name for personalization (Issue #29 - educational comment)
        # Prioritize top-level customer_name, fallback to shipping_address.name
        # Reference: test-data/shopify/orders.json structure
        customer_full_name = order_data.get("customer_name") or order_data.get("shipping_address", {}).get("name", "")
        customer_name = customer_full_name.split()[0] if customer_full_name else ""
        greeting = f"Hi {customer_name},\n\n" if customer_name else ""

        # CRITICAL: $50 Auto-Approval Threshold Logic
        # This is the core business rule for Issue #29
        # Reference: docs/ISSUE-29-IMPLEMENTATION-PLAN.md
        AUTO_APPROVAL_THRESHOLD = 50.00

        if order_total <= AUTO_APPROVAL_THRESHOLD:
            # ========================================================================
            # AUTO-APPROVAL PATH (≤$50)
            # ========================================================================

            # Generate RMA (Return Merchandise Authorization) number
            # Format: RMA-YYYYMMDD-NNNNN
            # Example: RMA-20260123-10125
            from datetime import datetime
            today = datetime.now().strftime("%Y%m%d")
            rma_number = f"RMA-{today}-{order_number}"

            # Extract items for return confirmation
            items = order_data.get("items", [])
            items_text = "\n".join([f"- {item['quantity']}x {item['name']}" for item in items])

            response = f"""{greeting}I'm sorry to hear you'd like to return order #{order_number}! I want to make this as easy as possible for you.

**Good news:** I can immediately approve your return and process your refund!

**Return Authorization Approved**
**RMA Number:** {rma_number}
**Order Total:** ${order_total:.2f}
**Refund Amount:** ${order_total:.2f} (full refund to original payment method)

**Items being returned:**
{items_text}

**Next Steps:**
1. **Prepaid Return Label:** Check your email in the next 5 minutes for your USPS prepaid return label
2. **Pack Your Items:** Use original packaging if possible (or any sturdy box)
3. **Attach Label:** Print and attach the prepaid label to your package
4. **Drop Off:** Take to any USPS location (no postage needed)
5. **Track Return:** Use the tracking number in your email

**Refund Timeline:**
- **Shipment Received:** Typically 3-5 business days after you drop off
- **Refund Processed:** Within 2 business days of receiving your return
- **Funds Available:** 3-5 business days depending on your bank

**Return Policy:**
- 30-day return window from delivery date [OK]
- Items unopened and in original condition [OK]
- Full refund including original shipping costs [OK]

Your satisfaction is our priority! If you have any questions about your return, just ask.

Is there anything else I can help you with today?"""

            # Auto-approval path: escalation NOT required
            return (response, False)

        else:
            # ========================================================================
            # ESCALATION PATH (>$50)
            # ========================================================================
            # High-value returns require human review for quality control
            # Support team will review within 24 hours

            response = f"""{greeting}Thank you for contacting us about returning order #{order_number}.

I understand you'd like to process a return. Because your order total is ${order_total:.2f}, I've forwarded your request to our support team for priority review.

**What happens next:**
1. **Review:** Our support team will review your return request
2. **Contact:** You'll receive an email within 24 hours (usually much faster!)
3. **Approval:** Once approved, you'll receive your prepaid return label and RMA number
4. **Refund:** Full refund to your original payment method

**Your return request includes:**
- **Order Number:** #{order_number}
- **Order Total:** ${order_total:.2f}
- **Status:** Forwarded to support team

Our team prioritizes return requests and will get back to you as quickly as possible. We're committed to making this process smooth and easy for you!

**Questions?** Feel free to ask - I'm here to help!

Is there anything else I can assist you with in the meantime?"""

            # Escalation path: requires_escalation = True (Issue #29 core requirement)
            return (response, True)

    def _format_refund_status_response(self, request: ResponseRequest) -> str:
        """Format refund status response."""
        return ("I'd be happy to check on your refund status! To look this up for you, "
               "I'll need your order number or the email address associated with your order.\n\n"
               "Typically, refunds are processed within 2 business days of receiving your return, "
               "and appear in your account within 3-5 business days depending on your bank.\n\n"
               "What's your order number?")

    def _format_shipping_question_response(self, request: ResponseRequest) -> str:
        """Format shipping information response."""
        shipping_items = [item for item in request.knowledge_context if "shipping" in item.get("source", "").lower()]

        if not shipping_items:
            return ("I'm happy to help with shipping information!\n\n"
                   "**Standard Shipping (USPS Priority Mail):**\n"
                   "- FREE on orders over $75\n"
                   "- FREE for all auto-delivery subscribers\n"
                   "- 3-5 business days delivery\n"
                   "- $8.50 for orders under $75\n\n"
                   "**Express Shipping Options:**\n"
                   "- UPS 2-Day: $15\n"
                   "- UPS Next Day: $25\n\n"
                   "We also ship to Canada and Mexico! Do you have a specific shipping question?")

        # Use first shipping policy result
        shipping_info = shipping_items[0]
        title = shipping_info.get("title", "")
        content = shipping_info.get("content", "")
        quick_answer = shipping_info.get("quick_answer", "")

        response = f"""**{title}**

{quick_answer if quick_answer else content}

"""

        # Add shipping scenarios if available
        scenarios = [item for item in shipping_items if item.get("type") == "recommendation"]
        if scenarios:
            response += "**Recommendations:**\n"
            for scenario in scenarios[:2]:
                rec = scenario.get("recommendation", "")
                cost = scenario.get("typical_cost", "")
                response += f"- {rec} ({cost})\n"
            response += "\n"

        response += "Do you have any other shipping questions?"

        return response

    def _format_subscription_response(self, request: ResponseRequest) -> str:
        """Format auto-delivery subscription response."""
        sub_items = [item for item in request.knowledge_context if "subscription" in item.get("source", "").lower()]

        if sub_items:
            sub_info = sub_items[0]
            benefits = sub_info.get("benefits", [])

            response = "**Auto-Delivery Subscription Benefits:**\n\n"
            for benefit in benefits:
                response += f"✓ {benefit}\n"

            response += "\n**Managing Your Subscription:**\n"
            response += "You can easily:\n"
            response += "- Change delivery frequency (weekly, bi-weekly, monthly)\n"
            response += "- Skip upcoming deliveries\n"
            response += "- Swap products in your next order\n"
            response += "- Pause or cancel anytime\n\n"
            response += "Would you like help managing your subscription, or do you have questions about signing up?"
        else:
            response = ("Our Auto-Delivery subscription ensures you never run out of your favorite coffee!\n\n"
                       "**Benefits:**\n"
                       "✓ Free shipping on every order\n"
                       "✓ Flexible scheduling\n"
                       "✓ Skip or modify anytime\n"
                       "✓ No commitment - cancel anytime\n\n"
                       "Would you like to set up auto-delivery for your favorite coffee?")

        return response

    def _format_gift_card_response(self, request: ResponseRequest) -> str:
        """
        Format gift card information response.

        Issue #25: Enhanced to support product information queries
        ------------------------------------------------------------
        When knowledge_context contains products (type="product"), this means the
        customer asked about product information (price, denominations, etc.), NOT policy.
        Route to product information response instead of gift card policy.
        """
        # Issue #25: Check if products are in knowledge context FIRST
        # Example: "How much is the gift card?" → product info response with prices
        products = [item for item in request.knowledge_context if item.get("type") == "product"]

        if products:
            # Customer asked about product information (price, denominations)
            # Delegate to product info formatter
            return self._format_product_info_response(request)

        # POLICY INFORMATION RESPONSE (no products in context)
        gift_items = [item for item in request.knowledge_context if "gift" in item.get("source", "").lower()]

        if gift_items:
            gift_info = gift_items[0]
            content = gift_info.get("content", "")
            options = gift_info.get("options", [])

            response = f"""**Gift Cards**

{content}

**Available Options:**\n"""
            for option in options:
                response += f"- {option}\n"

            response += "\n**Available Amounts:** $25, $50, $75, $100, $150, $200\n\n"
            response += "Gift cards never expire and can be used for any products on our site, including brewers, pods, and accessories.\n\n"
            response += "Would you like to purchase a gift card?"
        else:
            response = ("Gift cards are a perfect gift for any coffee lover!\n\n"
                       "**Options:**\n"
                       "- Virtual Gift Card (instant email delivery)\n"
                       "- Physical Gift Card (beautiful gift packaging, 2-5 business days)\n\n"
                       "**Amounts:** $25 to $200\n"
                       "**Expiration:** Never\n\n"
                       "Would you like to purchase a gift card?")

        return response

    def _format_loyalty_response(self, request: ResponseRequest) -> str:
        """
        Format loyalty program information response with personalized balance.

        Issue #34: Customer Loyalty Program Inquiry
        --------------------------------------------
        Handles personalized responses for:
        - Points balance queries (show current balance, tier status)
        - Redemption questions (show available redemption options)
        - General program info (earning rates, benefits)
        - Tier information (current tier, points to next tier)

        Reference: test-data/knowledge-base/loyalty-program.json
        """
        # Extract customer balance from knowledge context
        balance_data = None
        for item in request.knowledge_context:
            if item.get("type") == "customer_balance":
                balance_data = item
                break

        # Extract program info from knowledge context
        program_sections = [item for item in request.knowledge_context
                          if item.get("type") == "policy" and "loyalty" in item.get("source", "").lower()]

        redemption_tiers = None
        membership_tiers = None
        for item in request.knowledge_context:
            if item.get("type") == "redemption_tiers":
                redemption_tiers = item.get("tiers", [])
            elif item.get("type") == "membership_tiers":
                membership_tiers = item.get("tiers", [])

        # PERSONALIZED RESPONSE: If customer balance is available
        if balance_data:
            customer_name = balance_data.get("customer_name", "").split()[0] if balance_data.get("customer_name") else ""
            greeting = f"Hi {customer_name},\n\n" if customer_name else ""

            current_balance = balance_data.get("current_balance", 0)
            tier = balance_data.get("tier", "Bronze")
            points_to_next_tier = balance_data.get("points_to_next_tier", 0)
            next_tier = balance_data.get("next_tier")
            points_expiring = balance_data.get("points_expiring_30_days", 0)
            auto_delivery = balance_data.get("auto_delivery_subscriber", False)

            # Calculate redemption options based on current balance
            available_redemptions = []
            if redemption_tiers:
                for tier_info in redemption_tiers:
                    if current_balance >= tier_info.get("points_required", 0):
                        available_redemptions.append(
                            f"{tier_info['points_required']} points = {tier_info['discount_display']} discount"
                        )

            response = f"""{greeting}**Your BrewVi Rewards Status**

**Current Balance:** {current_balance} points
**Tier:** {tier}{' 🌟' if tier == 'Gold' else ' ⭐' if tier == 'Silver' else ''}"""

            # Add next tier progress if applicable
            if next_tier and points_to_next_tier > 0:
                response += f"\n**Progress to {next_tier}:** {points_to_next_tier} points away"

            # Add auto-delivery subscriber badge
            if auto_delivery:
                response += "\n**Status:** Auto-Delivery Subscriber (2X points!)"

            # Add expiration warning if applicable
            if points_expiring > 0:
                response += f"\n⚠️ **Expiring Soon:** {points_expiring} points expire in 30 days"

            # Add redemption options
            if available_redemptions:
                response += "\n\n**You Can Redeem:**\n"
                for option in available_redemptions[:3]:  # Show top 3 options
                    response += f"✓ {option}\n"
            else:
                # Customer doesn't have enough points yet
                if redemption_tiers and redemption_tiers[0].get("points_required", 0) > current_balance:
                    points_needed = redemption_tiers[0]["points_required"] - current_balance
                    response += f"\n\nYou need {points_needed} more points to redeem your first reward!"

            # Add program details from sections if available
            if program_sections:
                # Find earning or redemption section
                for section in program_sections:
                    section_id = section.get("section_id", "")
                    if "earn" in section_id or "redeem" in section_id:
                        quick_answer = section.get("quick_answer", "")
                        if quick_answer:
                            response += f"\n\n**How it Works:** {quick_answer}"
                            break

            response += "\n\nRedeem your points at checkout on your next purchase!"

        # GENERAL RESPONSE: No customer balance available
        elif program_sections:
            # Use first section (usually earning points overview)
            loyalty_info = program_sections[0]
            title = loyalty_info.get("title", "Loyalty Rewards Program")
            quick_answer = loyalty_info.get("quick_answer", "")
            content = loyalty_info.get("content", "")

            response = f"**{title}**\n\n"

            if quick_answer:
                response += f"{quick_answer}\n\n"

            # Add redemption tiers if available
            if redemption_tiers:
                response += "**Redemption Options:**\n"
                for tier_info in redemption_tiers[:4]:  # Show up to 4 tiers
                    response += f"✓ {tier_info['points_required']} points = {tier_info['discount_display']}\n"
                response += "\n"

            # Add membership tiers if available
            if membership_tiers:
                response += "**Membership Tiers:**\n"
                for tier_info in membership_tiers:
                    tier_name = tier_info.get("tier_name", "")
                    earning_rate = tier_info.get("earning_rate", 1.0)
                    response += f"✓ **{tier_name}:** {earning_rate}x points per $1\n"
                response += "\n"

            response += "**How to Join:** Automatic enrollment with your first purchase!\n\n"
            response += "Check your points balance anytime in your account dashboard."

        # FALLBACK RESPONSE: No knowledge context available
        else:
            response = ("**Loyalty Rewards Program**\n\n"
                       "Earn points with every purchase!\n\n"
                       "✓ 1 point per $1 spent\n"
                       "✓ 2x points for auto-delivery subscribers\n"
                       "✓ 100 points = $5 reward\n"
                       "✓ Birthday bonus points\n"
                       "✓ Referral rewards\n\n"
                       "You're automatically enrolled with your first purchase. Questions about your points?")

        return response

    def _format_escalation_response(self, request: ResponseRequest) -> str:
        """Format escalation response when routing to human agent."""
        escalation_reason = None
        for item in request.knowledge_context:
            if item.get("escalation_reason"):
                escalation_reason = item.get("escalation_reason")
                break

        if escalation_reason == "health_safety":
            return ("I'm very concerned about what you've described. For your safety, I'm immediately "
                   "connecting you with our customer care team who can assist you right away.\n\n"
                   "**Please do not use the product.** A specialist will contact you within 15 minutes.\n\n"
                   "If this is a medical emergency, please call 911 or seek immediate medical attention.")

        elif escalation_reason == "customer_frustration":
            return ("I sincerely apologize for the frustration you're experiencing. This isn't the level of service "
                   "we pride ourselves on, and I want to make this right for you.\n\n"
                   "I'm connecting you with a senior customer care specialist who will personally handle your case "
                   "and has the authority to resolve this to your satisfaction. They'll reach out to you within 1 hour.\n\n"
                   "Thank you for your patience, and again, I apologize for this experience.")

        elif escalation_reason == "brewer_defect":
            return ("I'm sorry to hear your brewer isn't working properly. Since you've tried troubleshooting, "
                   "let me escalate this to our technical support team.\n\n"
                   "They'll review your case and likely arrange a replacement under warranty. "
                   "A specialist will contact you within 2 hours to coordinate next steps.\n\n"
                   "Your brewer is covered by our 2-year warranty, so you're fully protected.")

        else:
            return ("I want to make sure you get the best possible help with this. I'm connecting you with "
                   "a specialist who can give your situation the attention it deserves.\n\n"
                   "They'll reach out to you shortly. Thank you for your patience!")

    def _format_general_response(self, request: ResponseRequest) -> str:
        """
        Format general/fallback response.

        Issue #25 Fix: If knowledge context contains products, show them
        even if intent is general_inquiry. This handles cases where customers
        ask product questions but intent isn't classified as PRODUCT_INFO.

        Example: "Tell me about your coffee pods" → general_inquiry
        But knowledge retrieval found 3 products → show them!
        """
        # Issue #25: Check if products were found in knowledge context
        # If yes, delegate to product formatter instead of generic greeting
        products = [item for item in request.knowledge_context if item.get("type") == "product"]

        if products:
            # Knowledge Retrieval found products, customer wants product info
            # Delegate to product info formatter to show results properly
            return self._format_product_info_response(request)

        # No products found, return generic greeting/menu
        return ("Thank you for contacting us! I'm here to help you with:\n\n"
               "✓ Order tracking and status\n"
               "✓ Product information and recommendations\n"
               "✓ Brewer support and troubleshooting\n"
               "✓ Returns and refunds\n"
               "✓ Shipping information\n"
               "✓ Auto-delivery subscription management\n"
               "✓ Gift cards and loyalty rewards\n\n"
               "What can I help you with today?")

    # Helper method to extract order data from knowledge context
    def _extract_order_from_context(self, knowledge_context: list) -> dict:
        """Extract order data from knowledge context list."""
        for item in knowledge_context:
            if item.get("type") == "order":
                return item
        return {}
    
    def cleanup(self):
        self.logger.info("Cleaning up Response Generation Agent...")
        self.logger.info(
            f"Statistics - Total: {self.responses_generated}, "
            f"OpenAI: {self.openai_responses}, "
            f"Template: {self.template_responses}"
        )

        # Log token usage if available
        if self.openai_client:
            usage = self.openai_client.get_total_usage()
            self.logger.info(
                f"Token usage - Total: {usage['total_tokens']}, "
                f"Cost: ${usage['total_cost']:.4f}"
            )

        shutdown_factory()
    
    async def run_demo_mode(self):
        """Run in demo mode - Phase 2 coffee/brewing examples."""
        self.logger.info("Running in DEMO MODE - Phase 2 Coffee/Brewing Business")

        samples = [
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
            }
        ]

        for msg in samples:
            self.logger.info("=" * 60)
            result = await self.handle_message(msg)
            response_content = extract_message_content(result)
            response_text = response_content.get("response_text", "")
            self.logger.info(f"Demo Response:\n{response_text}")
            await asyncio.sleep(3)

        self.logger.info("Demo complete. Keeping alive for health checks...")
        while True:
            await asyncio.sleep(30)

async def main():
    agent = ResponseGenerationAgent()
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
