"""
Order-related response formatters.

Handles: ORDER_STATUS, REFUND_STATUS, RETURN_REQUEST

These formatters handle the most common customer service scenarios -
order tracking, returns, and refunds. They transform raw order data
into friendly, informative responses.

Educational Note:
- Order data comes from Shopify API via KnowledgeRetrievalAgent
- Return requests have business logic for auto-approval threshold
- All responses are designed to reduce follow-up questions

Business Rules:
- $50 auto-approval threshold for returns (no human review needed)
- 30-day return window from delivery
- Free return shipping labels provided
"""

from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional


def extract_order_from_context(
    knowledge_context: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Extract order data from knowledge context list.

    Helper function used by other formatters to find order information
    in the knowledge context returned by KnowledgeRetrievalAgent.

    Args:
        knowledge_context: List of context items, each with a "type" field

    Returns:
        Dict containing order data if found, empty dict otherwise
    """
    for item in knowledge_context:
        if item.get("type") == "order":
            return item
    return {}


def format_order_status(knowledge_context: List[Dict[str, Any]]) -> str:
    """
    Format detailed order status response with tracking info.

    Creates a comprehensive order status response including shipping
    status, tracking information, delivery estimates, and item details.

    Args:
        knowledge_context: List of context items from KnowledgeRetrievalAgent.
            Expected order format:
            {
                "type": "order",
                "order_number": str,
                "status": str (Pending/Shipped/Delivered),
                "fulfillment_status": str,
                "shipping_address": {"name": str, ...},
                "items": [{"name": str, "quantity": int}, ...],
                "tracking": {
                    "carrier": str,
                    "tracking_number": str,
                    "tracking_url": str,
                    "expected_delivery": str (ISO date),
                    "last_location": str,
                    "shipped_date": str,
                    "delivered_date": str,
                    "delivery_note": str
                }
            }

    Returns:
        str: Formatted order status response tailored to status:
            - Shipped: Full tracking details with link
            - Delivered: Confirmation with delivery location
            - Pending: Processing message with ship date estimate
            - Other: Generic status display

    Business Logic:
        - Extracts customer first name for personalized greeting
        - Formats dates for readability (e.g., "Jan 28")
        - Provides carrier-specific tracking URL fallback
        - Offers proactive help if delivery is delayed
    """
    order_data = extract_order_from_context(knowledge_context)

    if not order_data:
        return (
            "I'd be happy to help you track your order! To provide the most accurate information, "
            "could you please provide your order number? You can find it in your confirmation email "
            "(it looks like #10234 or ORD-10234)."
        )

    # Extract customer name if available
    customer_name = (
        order_data.get("shipping_address", {}).get("name", "").split()[0]
        if order_data.get("shipping_address")
        else ""
    )
    greeting = f"Hi {customer_name},\n\n" if customer_name else ""

    order_number = order_data.get("order_number", "")
    status = order_data.get("status", "").title()
    fulfillment_status = (
        order_data.get("fulfillment_status", "").replace("_", " ").title()
    )

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
        items_text = "\n".join(
            [f"- {item['quantity']}x {item['name']}" for item in items]
        )

        # Format expected delivery date
        if expected_delivery:
            try:
                delivery_date = datetime.fromisoformat(
                    expected_delivery.replace("Z", "+00:00")
                )
                delivery_str = delivery_date.strftime("%b %d")
            except (ValueError, TypeError):
                # Invalid date format - fall back to generic message
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


def format_refund_status(knowledge_context: List[Dict[str, Any]]) -> str:
    """
    Format refund status response.

    Provides information about refund processing timeline and status.
    Currently returns a generic response with refund timeline information.

    Args:
        knowledge_context: List of context items (currently unused,
            but kept for API consistency with other formatters)

    Returns:
        str: Generic refund timeline information including:
            - Request for order number
            - Processing timeline (2 business days)
            - Bank posting timeline (3-5 business days)

    Future Enhancement:
        Once refund tracking is integrated with payment processor,
        this can show real-time refund status by order number.
    """
    return (
        "I'd be happy to check on your refund status! To look this up for you, "
        "I'll need your order number or the email address associated with your order.\n\n"
        "Typically, refunds are processed within 2 business days of receiving your return, "
        "and appear in your account within 3-5 business days depending on your bank.\n\n"
        "What's your order number?"
    )


def format_return_request(knowledge_context: List[Dict[str, Any]]) -> Tuple[str, bool]:
    """
    Format return/refund request response with $50 auto-approval threshold.

    This formatter implements automated return processing logic that
    reduces support workload while maintaining quality control for
    higher-value orders.

    Args:
        knowledge_context: List of context items from KnowledgeRetrievalAgent.
            Expected order format:
            {
                "type": "order",
                "order_number": str,
                "total": float,
                "customer_name": str,
                "shipping_address": {"name": str, ...},
                "items": [{"name": str, "quantity": int}, ...]
            }

    Returns:
        Tuple[str, bool]: (response_text, requires_escalation)
            - response_text: Formatted return response
            - requires_escalation: True if order >$50 and needs human review

    Business Logic (Issue #29):
        Auto-Approval Path (order ≤ $50):
        - Generates RMA number immediately
        - Provides full refund amount
        - Sends prepaid return label via email
        - Customer drops at USPS

        Escalation Path (order > $50):
        - Forwards to support team
        - 24-hour response commitment
        - Human reviews before approval

        Policy Rules:
        - 30-day return window from delivery
        - Items must be unopened, original packaging
        - Free return shipping (prepaid USPS label)
        - Refund to original payment method
        - Processing: 2 business days after receipt
        - Funds available: 3-5 business days after processing

    Educational Note:
        The $50 threshold balances automation benefits (faster service,
        lower support costs) against fraud risk (higher-value returns
        warrant human review). This threshold can be adjusted in
        AUTO_APPROVAL_THRESHOLD constant based on business data.
    """
    order_data = extract_order_from_context(knowledge_context)

    if not order_data:
        return (
            (
                "I'm sorry to hear you need to return something! I'm here to make this process as easy as possible.\n\n"
                "We accept returns within 30 days of delivery for a full refund. "
                "Items should be unopened and in original condition.\n\n"
                "To process your return, I'll need:\n"
                "- Your order number (e.g., #10234)\n"
                "- Which item(s) you'd like to return\n"
                "- Reason for return (optional, but helps us improve)\n\n"
                "What's your order number?"
            ),
            False,
        )

    # Extract key order information
    order_number = order_data.get("order_number", "")
    order_total = order_data.get("total", 0.0)

    # Extract customer first name
    customer_full_name = order_data.get("customer_name") or order_data.get(
        "shipping_address", {}
    ).get("name", "")
    customer_name = customer_full_name.split()[0] if customer_full_name else ""
    greeting = f"Hi {customer_name},\n\n" if customer_name else ""

    # $50 Auto-Approval Threshold
    AUTO_APPROVAL_THRESHOLD = 50.00

    if order_total <= AUTO_APPROVAL_THRESHOLD:
        # AUTO-APPROVAL PATH
        today = datetime.now().strftime("%Y%m%d")
        rma_number = f"RMA-{today}-{order_number}"

        items = order_data.get("items", [])
        items_text = "\n".join(
            [f"- {item['quantity']}x {item['name']}" for item in items]
        )

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

Your satisfaction is our priority! If you have any questions about your return, just ask.

Is there anything else I can help you with today?"""

        return (response, False)

    else:
        # ESCALATION PATH
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

Our team prioritizes return requests and will get back to you as quickly as possible.

Is there anything else I can assist you with in the meantime?"""

        return (response, True)
