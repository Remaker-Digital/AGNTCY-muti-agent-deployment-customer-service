"""
Unit Tests: Response Formatters

Tests all response formatting functions across product, order, support,
and escalation formatters to ensure consistent, high-quality output.

Educational Project: Multi-Agent AI Customer Service Platform
Phase: Testing & Validation
Coverage Target: 100% for all formatter modules

Test Categories:
1. Product Formatters - product info, recommendations, comparisons, brewer support
2. Order Formatters - order status, refund status, return requests
3. Support Formatters - shipping, subscription, gift card, loyalty
4. Escalation Formatters - escalation reasons, general fallback

Author: Claude Code
License: MIT (Educational Use)
"""

import pytest
from typing import Dict, Any, List


# ============================================================================
# Product Formatter Tests
# ============================================================================


class TestProductInfoFormatter:
    """Test format_product_info function."""

    def test_empty_knowledge_context(self):
        """Test with no products in context - should return catalog overview."""
        from agents.response_generation.formatters.product import format_product_info

        result = format_product_info([])

        assert "What we offer" in result
        assert "Brewers" in result
        assert "Coffee Pods" in result
        assert "What specific product" in result

    def test_single_product_basic_info(self):
        """Test single product with minimal fields."""
        from agents.response_generation.formatters.product import format_product_info

        context = [
            {
                "type": "product",
                "name": "Test Coffee Pods",
                "price": 24.99,
                "description": "Delicious medium roast coffee.",
                "category": "coffee pods",
            }
        ]

        result = format_product_info(context)

        assert "Test Coffee Pods" in result
        assert "$24.99" in result
        assert "Delicious medium roast coffee" in result
        assert "Coffee Pods" in result  # Category capitalized

    def test_single_product_with_features(self):
        """Test product with features list."""
        from agents.response_generation.formatters.product import format_product_info

        context = [
            {
                "type": "product",
                "name": "Premium Brewer",
                "price": 299.00,
                "description": "Smart brewing technology.",
                "category": "brewers",
                "features": [
                    "WiFi connected",
                    "Programmable brewing",
                    "Auto shut-off",
                ],
            }
        ]

        result = format_product_info(context)

        assert "Key Features" in result
        assert "WiFi connected" in result
        assert "Programmable brewing" in result
        assert "Auto shut-off" in result

    def test_product_out_of_stock(self):
        """Test out-of-stock product messaging."""
        from agents.response_generation.formatters.product import format_product_info

        context = [
            {
                "type": "product",
                "name": "Popular Item",
                "price": 19.99,
                "description": "Very popular.",
                "category": "pods",
                "in_stock": False,
            }
        ]

        result = format_product_info(context)

        assert "out of stock" in result.lower()
        assert "notify you" in result.lower() or "similar products" in result.lower()

    def test_product_low_inventory(self):
        """Test low inventory warning."""
        from agents.response_generation.formatters.product import format_product_info

        context = [
            {
                "type": "product",
                "name": "Limited Edition",
                "price": 34.99,
                "description": "Special blend.",
                "category": "pods",
                "in_stock": True,
                "inventory_count": 3,
            }
        ]

        result = format_product_info(context)

        assert "3 left in stock" in result or "Only 3" in result

    def test_product_with_variant(self):
        """Test product with variant name."""
        from agents.response_generation.formatters.product import format_product_info

        context = [
            {
                "type": "product",
                "name": "Coffee Pods",
                "variant_name": "Dark Roast",
                "price": 26.99,
                "description": "Bold flavor.",
                "category": "pods",
            }
        ]

        result = format_product_info(context)

        assert "Coffee Pods" in result
        assert "Dark Roast" in result

    def test_product_with_sku(self):
        """Test product with SKU displayed."""
        from agents.response_generation.formatters.product import format_product_info

        context = [
            {
                "type": "product",
                "name": "Descaling Solution",
                "price": 12.99,
                "description": "Keeps brewer clean.",
                "category": "accessories",
                "sku": "ACC-DESC-001",
            }
        ]

        result = format_product_info(context)

        assert "SKU: ACC-DESC-001" in result

    def test_multiple_products_shows_recommendations(self):
        """Test that multiple products shows 'You might also like' section."""
        from agents.response_generation.formatters.product import format_product_info

        context = [
            {
                "type": "product",
                "name": "Main Product",
                "price": 29.99,
                "description": "Primary selection.",
                "category": "pods",
                "in_stock": True,
            },
            {
                "type": "product",
                "name": "Related Product 1",
                "price": 24.99,
                "description": "Also good.",
                "category": "pods",
                "in_stock": True,
            },
            {
                "type": "product",
                "name": "Related Product 2",
                "price": 27.99,
                "description": "Another option.",
                "category": "pods",
                "in_stock": False,
            },
        ]

        result = format_product_info(context)

        assert "You might also like" in result
        assert "Related Product 1" in result
        assert "$24.99" in result
        assert "In stock" in result
        assert "Out of stock" in result

    def test_ignores_non_product_items(self):
        """Test that non-product items in context are ignored."""
        from agents.response_generation.formatters.product import format_product_info

        context = [
            {"type": "policy", "title": "Return Policy", "content": "30 days"},
            {
                "type": "product",
                "name": "Actual Product",
                "price": 19.99,
                "description": "Real product.",
                "category": "pods",
            },
        ]

        result = format_product_info(context)

        assert "Actual Product" in result
        assert "Return Policy" not in result


class TestProductRecommendationFormatter:
    """Test format_product_recommendation function."""

    def test_no_recommendations(self):
        """Test with no recommendations - asks for preferences."""
        from agents.response_generation.formatters.product import (
            format_product_recommendation,
        )

        result = format_product_recommendation([])

        assert "preferences" in result.lower()
        assert "light, medium, or dark" in result.lower()

    def test_single_recommendation(self):
        """Test single product recommendation."""
        from agents.response_generation.formatters.product import (
            format_product_recommendation,
        )

        context = [
            {
                "type": "recommendation",
                "name": "Perfect Match Coffee",
                "price": 24.99,
                "description": "A wonderful coffee that matches your taste perfectly with notes of chocolate and caramel.",
                "why_recommended": "Based on your love of medium roasts.",
            }
        ]

        result = format_product_recommendation(context)

        assert "Perfect Match Coffee" in result
        assert "$24.99" in result
        assert "Based on your love of medium roasts" in result

    def test_multiple_recommendations(self):
        """Test multiple recommendations with numbering."""
        from agents.response_generation.formatters.product import (
            format_product_recommendation,
        )

        context = [
            {
                "type": "recommendation",
                "name": "Option 1",
                "price": 19.99,
                "description": "First choice.",
                "why_recommended": "Reason 1",
            },
            {
                "type": "recommendation",
                "name": "Option 2",
                "price": 24.99,
                "description": "Second choice.",
                "why_recommended": "Reason 2",
            },
            {
                "type": "recommendation",
                "name": "Option 3",
                "price": 29.99,
                "description": "Third choice.",
                "why_recommended": "Reason 3",
            },
        ]

        result = format_product_recommendation(context)

        assert "1. Option 1" in result
        assert "2. Option 2" in result
        assert "3. Option 3" in result
        assert "Guilt Free Toss" in result  # Biodegradable mention


class TestProductComparisonFormatter:
    """Test format_product_comparison function."""

    def test_insufficient_products_for_comparison(self):
        """Test with less than 2 products."""
        from agents.response_generation.formatters.product import (
            format_product_comparison,
        )

        result = format_product_comparison([{"type": "product", "name": "Single"}])

        assert "compare" in result.lower()
        assert "which items" in result.lower()

    def test_two_product_comparison(self):
        """Test comparing two products."""
        from agents.response_generation.formatters.product import (
            format_product_comparison,
        )

        context = [
            {
                "type": "product",
                "name": "Brewer A",
                "price": 199.00,
                "category": "brewers",
                "features": ["WiFi", "Auto-off"],
            },
            {
                "type": "product",
                "name": "Brewer B",
                "price": 299.00,
                "category": "brewers",
                "features": ["WiFi", "Voice control", "Schedule"],
            },
        ]

        result = format_product_comparison(context)

        assert "Brewer A" in result
        assert "$199.00" in result
        assert "Brewer B" in result
        assert "$299.00" in result
        assert "best choice depends" in result.lower()


class TestBrewerSupportFormatter:
    """Test format_brewer_support function."""

    def test_no_support_items_returns_common_issues(self):
        """Test with no support context."""
        from agents.response_generation.formatters.product import format_brewer_support

        result = format_brewer_support([])

        assert "won't turn on" in result.lower() or "power" in result.lower()
        assert "cleaning" in result.lower() or "descaling" in result.lower()

    def test_troubleshooting_response(self):
        """Test troubleshooting steps response."""
        from agents.response_generation.formatters.product import format_brewer_support

        context = [
            {
                "source": "brewer_support",
                "type": "troubleshooting",
                "issue": "Brewer won't power on",
                "solutions": [
                    "Check power cord connection",
                    "Try a different outlet",
                    "Check circuit breaker",
                ],
                "escalation_needed": False,
            }
        ]

        result = format_brewer_support(context)

        assert "Brewer won't power on" in result
        assert "Check power cord" in result
        assert "1." in result  # Numbered steps

    def test_troubleshooting_with_escalation(self):
        """Test troubleshooting that needs escalation."""
        from agents.response_generation.formatters.product import format_brewer_support

        context = [
            {
                "source": "brewer_support",
                "type": "troubleshooting",
                "issue": "Internal error",
                "solutions": ["Restart brewer", "Factory reset"],
                "escalation_needed": True,
            }
        ]

        result = format_brewer_support(context)

        assert "escalate" in result.lower() or "technical support" in result.lower()
        assert "warranty" in result.lower()

    def test_maintenance_response(self):
        """Test maintenance instruction response."""
        from agents.response_generation.formatters.product import format_brewer_support

        context = [
            {
                "source": "brewer_support",
                "type": "maintenance",
                "title": "Descaling Your Brewer",
                "instructions": "Run descaling solution through a brewing cycle.",
                "product_recommendation": "Bruvi Descaling Solution ($12.99)",
            }
        ]

        result = format_brewer_support(context)

        assert "Descaling Your Brewer" in result
        assert "Recommended Product" in result


# ============================================================================
# Order Formatter Tests
# ============================================================================


class TestOrderStatusFormatter:
    """Test format_order_status function."""

    def test_format_order_status_no_order(self):
        """Test with empty context - asks for order number."""
        from agents.response_generation.formatters.order import format_order_status

        result = format_order_status([])

        assert "order number" in result.lower()
        assert "confirmation email" in result.lower()

    def test_format_order_status_shipped(self):
        """Test shipped order with tracking info."""
        from agents.response_generation.formatters.order import format_order_status

        context = [
            {
                "type": "order",
                "order_number": "10234",
                "status": "shipped",
                "fulfillment_status": "in_transit",
                "items": [{"name": "Coffee Pods", "quantity": 2}],
                "tracking": {
                    "carrier": "USPS",
                    "tracking_number": "9400111899223033005484",
                    "shipped_date": "2026-01-25T10:00:00Z",
                    "expected_delivery": "2026-01-30T17:00:00Z",
                    "last_location": "Distribution Center, CA",
                },
                "shipping_address": {"name": "Sarah Martinez"},
            }
        ]

        result = format_order_status(context)

        assert "10234" in result
        assert "In Transit" in result
        assert "USPS" in result
        assert "9400111899223033005484" in result
        assert "Sarah" in result  # Personalized greeting

    def test_format_order_status_delivered(self):
        """Test delivered order status."""
        from agents.response_generation.formatters.order import format_order_status

        context = [
            {
                "type": "order",
                "order_number": "10235",
                "status": "Delivered",
                "tracking": {
                    "delivered_date": "2026-01-26T14:30:00Z",
                    "delivery_note": "Left at front door",
                },
            }
        ]

        result = format_order_status(context)

        assert "10235" in result
        assert "delivered" in result.lower()
        assert "front door" in result

    def test_format_order_status_pending(self):
        """Test pending order status."""
        from agents.response_generation.formatters.order import format_order_status

        context = [
            {
                "type": "order",
                "order_number": "10236",
                "status": "Pending",
            }
        ]

        result = format_order_status(context)

        assert "10236" in result
        assert "prepared for shipment" in result.lower() or "pending" in result.lower()


class TestRefundFormatter:
    """Test format_refund_status function."""

    def test_format_refund_status(self):
        """Test refund status generic response."""
        from agents.response_generation.formatters.order import format_refund_status

        result = format_refund_status([])

        assert "refund status" in result.lower()
        assert "order number" in result.lower()
        assert "2 business days" in result or "3-5 business days" in result


class TestReturnRequestFormatter:
    """Test format_return_request function with $50 threshold."""

    def test_return_no_order_asks_for_info(self):
        """Test return request with no order context."""
        from agents.response_generation.formatters.order import format_return_request

        response, escalated = format_return_request([])

        assert "order number" in response.lower()
        assert "30 days" in response
        assert escalated is False

    def test_return_under_50_auto_approved(self):
        """Test return auto-approval for orders ≤$50."""
        from agents.response_generation.formatters.order import format_return_request

        context = [
            {
                "type": "order",
                "order_number": "10237",
                "total": 45.99,
                "customer_name": "Sarah Martinez",
                "items": [{"name": "Coffee Pods", "quantity": 1}],
            }
        ]

        response, escalated = format_return_request(context)

        assert "RMA" in response
        assert "10237" in response
        assert "$45.99" in response
        assert "approved" in response.lower()
        assert "prepaid" in response.lower()
        assert escalated is False

    def test_return_exactly_50_auto_approved(self):
        """Test return auto-approval at exactly $50 threshold."""
        from agents.response_generation.formatters.order import format_return_request

        context = [
            {
                "type": "order",
                "order_number": "10238",
                "total": 50.00,
                "items": [{"name": "Brewer Accessory", "quantity": 1}],
            }
        ]

        response, escalated = format_return_request(context)

        assert "RMA" in response
        assert "$50.00" in response
        assert escalated is False

    def test_return_over_50_escalated(self):
        """Test return escalation for orders >$50."""
        from agents.response_generation.formatters.order import format_return_request

        context = [
            {
                "type": "order",
                "order_number": "10239",
                "total": 86.37,
                "customer_name": "Mike Thompson",
                "items": [{"name": "Premium Brewer", "quantity": 1}],
            }
        ]

        response, escalated = format_return_request(context)

        assert "10239" in response
        assert "$86.37" in response
        assert "support team" in response.lower()
        assert "review" in response.lower()
        assert escalated is True


# ============================================================================
# Support Formatter Tests
# ============================================================================


class TestShippingFormatter:
    """Test format_shipping_question function."""

    def test_shipping_no_context(self):
        """Test shipping info with no context."""
        from agents.response_generation.formatters.support import format_shipping_question

        result = format_shipping_question([])

        assert "FREE" in result
        assert "$75" in result
        assert "auto-delivery" in result.lower()
        assert "Express" in result or "2-Day" in result

    def test_shipping_with_context(self):
        """Test shipping with knowledge context."""
        from agents.response_generation.formatters.support import format_shipping_question

        context = [
            {
                "source": "shipping_info",
                "title": "International Shipping",
                "content": "We ship to Canada and Mexico.",
                "quick_answer": "Yes, we offer international shipping!",
            }
        ]

        result = format_shipping_question(context)

        assert "International Shipping" in result
        assert "international" in result.lower()


class TestSubscriptionFormatter:
    """Test format_subscription function."""

    def test_subscription_no_context(self):
        """Test subscription info with no context."""
        from agents.response_generation.formatters.support import format_subscription

        result = format_subscription([])

        assert "Auto-Delivery" in result
        assert "Free shipping" in result or "free shipping" in result.lower()
        assert "cancel anytime" in result.lower()

    def test_subscription_with_benefits(self):
        """Test subscription with benefits context."""
        from agents.response_generation.formatters.support import format_subscription

        context = [
            {
                "source": "subscription_info",
                "benefits": [
                    "Free shipping always",
                    "10% discount",
                    "Flexible scheduling",
                ],
            }
        ]

        result = format_subscription(context)

        assert "Free shipping always" in result or "free shipping" in result.lower()
        assert "Managing Your Subscription" in result


class TestGiftCardFormatter:
    """Test format_gift_card function."""

    def test_gift_card_no_context(self):
        """Test gift card info with no context."""
        from agents.response_generation.formatters.support import format_gift_card

        result = format_gift_card([])

        assert "gift card" in result.lower()


class TestLoyaltyFormatter:
    """Test format_loyalty function."""

    def test_loyalty_no_context(self):
        """Test loyalty program info with no context."""
        from agents.response_generation.formatters.support import format_loyalty

        result = format_loyalty([])

        assert "rewards" in result.lower() or "loyalty" in result.lower()


# ============================================================================
# Escalation Formatter Tests
# ============================================================================


class TestEscalationFormatter:
    """Test format_escalation function."""

    def test_escalation_health_safety(self):
        """Test health/safety escalation response."""
        from agents.response_generation.formatters.escalation import format_escalation

        context = [{"escalation_reason": "health_safety"}]

        result = format_escalation(context)

        assert "safety" in result.lower()
        assert "15 minutes" in result
        assert "911" in result or "medical" in result.lower()

    def test_escalation_customer_frustration(self):
        """Test frustrated customer escalation response."""
        from agents.response_generation.formatters.escalation import format_escalation

        context = [{"escalation_reason": "customer_frustration"}]

        result = format_escalation(context)

        assert "apologize" in result.lower()
        assert "senior" in result.lower() or "specialist" in result.lower()
        assert "1 hour" in result

    def test_escalation_brewer_defect(self):
        """Test brewer defect escalation response."""
        from agents.response_generation.formatters.escalation import format_escalation

        context = [{"escalation_reason": "brewer_defect"}]

        result = format_escalation(context)

        assert "technical support" in result.lower()
        assert "warranty" in result.lower()
        assert "replacement" in result.lower()

    def test_escalation_default(self):
        """Test default escalation response."""
        from agents.response_generation.formatters.escalation import format_escalation

        context = []

        result = format_escalation(context)

        assert "specialist" in result.lower()


class TestGeneralFormatter:
    """Test format_general function."""

    def test_general_no_context(self):
        """Test general response with no context."""
        from agents.response_generation.formatters.escalation import format_general

        result = format_general([])

        assert "Order tracking" in result
        assert "Product information" in result
        assert "Returns and refunds" in result

    def test_general_with_products_uses_product_formatter(self):
        """Test that products in context use product formatter."""
        from agents.response_generation.formatters.escalation import format_general

        context = [
            {
                "type": "product",
                "name": "Coffee Pods",
                "price": 24.99,
                "description": "Great coffee.",
                "category": "pods",
            }
        ]

        result = format_general(context)

        assert "Coffee Pods" in result
        assert "$24.99" in result


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestFormatterEdgeCases:
    """Test edge cases across all formatters."""

    def test_product_with_zero_price(self):
        """Test product with zero price (free item)."""
        from agents.response_generation.formatters.product import format_product_info

        context = [
            {
                "type": "product",
                "name": "Free Sample",
                "price": 0.00,
                "description": "Try our coffee free!",
                "category": "samples",
            }
        ]

        result = format_product_info(context)

        assert "Free Sample" in result
        assert "$0.00" in result

    def test_product_with_special_characters(self):
        """Test product with special characters in name."""
        from agents.response_generation.formatters.product import format_product_info

        context = [
            {
                "type": "product",
                "name": "Café Blend™ - Special Edition (2024)",
                "price": 29.99,
                "description": "Special chars: é, ®, ©",
                "category": "pods",
            }
        ]

        result = format_product_info(context)

        assert "Café Blend™" in result
        assert "é, ®, ©" in result

    def test_missing_optional_fields(self):
        """Test products with missing optional fields don't crash."""
        from agents.response_generation.formatters.product import format_product_info

        context = [
            {
                "type": "product",
                # Only required fields, everything else missing
                "name": "Minimal Product",
                "price": 9.99,
            }
        ]

        result = format_product_info(context)

        assert "Minimal Product" in result
        assert "$9.99" in result


# Test execution
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
