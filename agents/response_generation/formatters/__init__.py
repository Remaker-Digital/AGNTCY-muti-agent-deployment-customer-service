"""
Response Formatters Package

Modular response formatting functions for each intent type.
Split from agent.py to reduce file size and improve maintainability.

Usage:
    from agents.response_generation.formatters import (
        format_order_status,
        format_product_info,
        format_return_request,
        ...
    )
"""

from agents.response_generation.formatters.order import (
    format_order_status,
    format_refund_status,
    format_return_request,
    extract_order_from_context,
)
from agents.response_generation.formatters.product import (
    format_product_info,
    format_product_recommendation,
    format_product_comparison,
    format_brewer_support,
)
from agents.response_generation.formatters.support import (
    format_shipping_question,
    format_subscription,
    format_gift_card,
    format_loyalty,
)
from agents.response_generation.formatters.escalation import (
    format_escalation,
    format_general,
)

__all__ = [
    # Order formatters
    "format_order_status",
    "format_refund_status",
    "format_return_request",
    "extract_order_from_context",
    # Product formatters
    "format_product_info",
    "format_product_recommendation",
    "format_product_comparison",
    "format_brewer_support",
    # Support formatters
    "format_shipping_question",
    "format_subscription",
    "format_gift_card",
    "format_loyalty",
    # Escalation formatters
    "format_escalation",
    "format_general",
]
