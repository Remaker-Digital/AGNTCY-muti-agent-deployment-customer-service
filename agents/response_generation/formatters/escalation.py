"""
Escalation and general response formatters.

Handles: ESCALATION_NEEDED, GENERAL_INQUIRY
"""

from typing import List, Dict, Any

from agents.response_generation.formatters.product import format_product_info


def format_escalation(knowledge_context: List[Dict[str, Any]]) -> str:
    """Format escalation response when routing to human agent."""
    escalation_reason = None
    for item in knowledge_context:
        if item.get("escalation_reason"):
            escalation_reason = item.get("escalation_reason")
            break

    if escalation_reason == "health_safety":
        return (
            "I'm very concerned about what you've described. For your safety, I'm immediately "
            "connecting you with our customer care team who can assist you right away.\n\n"
            "**Please do not use the product.** A specialist will contact you within 15 minutes.\n\n"
            "If this is a medical emergency, please call 911 or seek immediate medical attention."
        )

    elif escalation_reason == "customer_frustration":
        return (
            "I sincerely apologize for the frustration you're experiencing. This isn't the level of service "
            "we pride ourselves on, and I want to make this right for you.\n\n"
            "I'm connecting you with a senior customer care specialist who will personally handle your case "
            "and has the authority to resolve this to your satisfaction. They'll reach out to you within 1 hour.\n\n"
            "Thank you for your patience, and again, I apologize for this experience."
        )

    elif escalation_reason == "brewer_defect":
        return (
            "I'm sorry to hear your brewer isn't working properly. Since you've tried troubleshooting, "
            "let me escalate this to our technical support team.\n\n"
            "They'll review your case and likely arrange a replacement under warranty. "
            "A specialist will contact you within 2 hours to coordinate next steps.\n\n"
            "Your brewer is covered by our 2-year warranty, so you're fully protected."
        )

    else:
        return (
            "I want to make sure you get the best possible help with this. I'm connecting you with "
            "a specialist who can give your situation the attention it deserves.\n\n"
            "They'll reach out to you shortly. Thank you for your patience!"
        )


def format_general(knowledge_context: List[Dict[str, Any]]) -> str:
    """Format general/fallback response."""
    # Check if products were found in knowledge context
    products = [item for item in knowledge_context if item.get("type") == "product"]

    if products:
        return format_product_info(knowledge_context)

    # No products found, return generic greeting/menu
    return (
        "Thank you for contacting us! I'm here to help you with:\n\n"
        "✓ Order tracking and status\n"
        "✓ Product information and recommendations\n"
        "✓ Brewer support and troubleshooting\n"
        "✓ Returns and refunds\n"
        "✓ Shipping information\n"
        "✓ Auto-delivery subscription management\n"
        "✓ Gift cards and loyalty rewards\n\n"
        "What can I help you with today?"
    )
