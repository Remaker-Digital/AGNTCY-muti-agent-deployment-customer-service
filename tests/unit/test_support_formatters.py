# ============================================================================
# Unit Tests for Support Response Formatters
# ============================================================================
# Purpose: Test support-related response formatters for shipping, subscription,
# gift cards, and loyalty programs
#
# Test Categories:
# 1. Shipping Question - Verify shipping info formatting
# 2. Subscription - Verify auto-delivery subscription formatting
# 3. Gift Card - Verify gift card info formatting
# 4. Loyalty Program - Verify loyalty/rewards formatting with personalization
#
# Related Documentation:
# - Support Formatters: agents/response_generation/formatters/support.py
# ============================================================================

import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.response_generation.formatters.support import (
    format_shipping_question,
    format_subscription,
    format_gift_card,
    format_loyalty,
)


# =============================================================================
# Test: Shipping Question Formatter
# =============================================================================


class TestShippingQuestionFormatter:
    """Tests for format_shipping_question function."""

    def test_default_shipping_response(self):
        """Verify default shipping response when no context."""
        result = format_shipping_question([])
        assert "Standard Shipping" in result
        assert "FREE" in result
        assert "$75" in result
        assert "3-5 business days" in result

    def test_default_includes_express_options(self):
        """Verify default includes express shipping options."""
        result = format_shipping_question([])
        assert "Express" in result
        assert "UPS 2-Day" in result or "2-Day" in result
        assert "Next Day" in result

    def test_default_includes_international(self):
        """Verify default includes international shipping mention."""
        result = format_shipping_question([])
        assert "Canada" in result or "Mexico" in result

    def test_with_shipping_context(self):
        """Verify formatting with shipping context."""
        context = [
            {
                "source": "shipping_policy",
                "title": "Free Shipping Policy",
                "content": "Free shipping on orders over $75",
                "quick_answer": "Orders over $75 ship free!",
            }
        ]
        result = format_shipping_question(context)
        assert "Free Shipping Policy" in result
        assert "Orders over $75 ship free!" in result

    def test_with_recommendations(self):
        """Verify recommendations are included."""
        context = [
            {
                "source": "shipping_policy",
                "title": "Shipping Options",
                "content": "Multiple shipping options available",
            },
            {
                "source": "shipping_recommendation",
                "type": "recommendation",
                "recommendation": "Standard shipping for regular orders",
                "typical_cost": "$8.50",
            },
        ]
        result = format_shipping_question(context)
        assert "Recommendations" in result
        assert "Standard shipping" in result
        assert "$8.50" in result

    def test_ends_with_question(self):
        """Verify response ends with follow-up question."""
        result = format_shipping_question([])
        assert "?" in result

    def test_non_shipping_source_ignored(self):
        """Verify non-shipping sources are ignored."""
        context = [
            {
                "source": "product_info",
                "title": "Coffee Pods",
                "content": "Premium coffee pods",
            }
        ]
        result = format_shipping_question(context)
        # Should return default since no shipping sources
        assert "Standard Shipping" in result


# =============================================================================
# Test: Subscription Formatter
# =============================================================================


class TestSubscriptionFormatter:
    """Tests for format_subscription function."""

    def test_default_subscription_response(self):
        """Verify default subscription response when no context."""
        result = format_subscription([])
        assert "Auto-Delivery" in result
        assert "Free shipping" in result
        assert "cancel anytime" in result.lower()

    def test_with_subscription_context(self):
        """Verify formatting with subscription context."""
        context = [
            {
                "source": "subscription_policy",
                "benefits": [
                    "Save 15% on every order",
                    "Free shipping always",
                    "Exclusive member perks",
                ],
            }
        ]
        result = format_subscription(context)
        assert "Save 15%" in result
        assert "Free shipping" in result
        assert "Exclusive member" in result

    def test_includes_management_options(self):
        """Verify management options are included."""
        context = [
            {
                "source": "subscription_policy",
                "benefits": ["Great savings"],
            }
        ]
        result = format_subscription(context)
        assert "Managing Your Subscription" in result
        assert "frequency" in result.lower() or "weekly" in result.lower()
        assert "skip" in result.lower() or "Skip" in result

    def test_ends_with_offer(self):
        """Verify response ends with helpful offer."""
        result = format_subscription([])
        assert "?" in result

    def test_non_subscription_source_ignored(self):
        """Verify non-subscription sources are ignored."""
        context = [
            {
                "source": "product_info",
                "title": "Coffee Pods",
            }
        ]
        result = format_subscription(context)
        # Should return default
        assert "Auto-Delivery" in result
        assert "never run out" in result.lower() or "subscription" in result.lower()


# =============================================================================
# Test: Gift Card Formatter
# =============================================================================


class TestGiftCardFormatter:
    """Tests for format_gift_card function."""

    def test_default_gift_card_response(self):
        """Verify default gift card response when no context."""
        result = format_gift_card([])
        assert "Gift" in result
        assert "Virtual" in result or "Physical" in result
        assert "$25" in result or "25" in result

    def test_with_product_context(self):
        """Verify product context returns product info format."""
        context = [
            {
                "type": "product",
                "name": "Gift Card $50",
                "price": 50.00,
                "description": "A gift card worth $50",
            }
        ]
        result = format_gift_card(context)
        # Should use product formatter
        assert "Gift Card" in result or "$50" in result

    def test_with_gift_policy_context(self):
        """Verify gift policy context formatting."""
        context = [
            {
                "source": "gift_card_policy",
                "content": "Gift cards are perfect for coffee lovers",
                "options": ["Digital gift card", "Physical gift card"],
            }
        ]
        result = format_gift_card(context)
        assert "Gift Cards" in result
        assert "Digital gift card" in result
        assert "Physical gift card" in result

    def test_includes_amounts(self):
        """Verify available amounts are shown."""
        context = [
            {
                "source": "gift_card_policy",
                "content": "Multiple denominations available",
                "options": [],
            }
        ]
        result = format_gift_card(context)
        assert "$25" in result or "$50" in result or "$100" in result

    def test_never_expire_mention(self):
        """Verify gift cards never expire is mentioned."""
        result = format_gift_card([])
        assert "Never" in result or "never" in result or "expire" in result.lower()

    def test_ends_with_purchase_offer(self):
        """Verify response ends with purchase offer."""
        result = format_gift_card([])
        assert "?" in result


# =============================================================================
# Test: Loyalty Program Formatter
# =============================================================================


class TestLoyaltyFormatter:
    """Tests for format_loyalty function."""

    def test_default_loyalty_response(self):
        """Verify default loyalty response when no context."""
        result = format_loyalty([])
        assert "Loyalty" in result or "Rewards" in result
        assert "points" in result.lower()

    def test_default_includes_earning_rate(self):
        """Verify default shows how to earn points."""
        result = format_loyalty([])
        assert "1 point" in result.lower() or "$1" in result

    def test_personalized_response_with_balance(self):
        """Verify personalized response with customer balance."""
        context = [
            {
                "type": "customer_balance",
                "customer_name": "John Smith",
                "current_balance": 500,
                "tier": "Silver",
                "points_to_next_tier": 250,
                "next_tier": "Gold",
                "points_expiring_30_days": 0,
                "auto_delivery_subscriber": False,
            }
        ]
        result = format_loyalty(context)
        assert "John" in result or "Hi" in result
        assert "500" in result
        assert "Silver" in result

    def test_shows_next_tier_progress(self):
        """Verify next tier progress is shown."""
        context = [
            {
                "type": "customer_balance",
                "current_balance": 500,
                "tier": "Silver",
                "points_to_next_tier": 250,
                "next_tier": "Gold",
            }
        ]
        result = format_loyalty(context)
        assert "Gold" in result
        assert "250" in result

    def test_shows_auto_delivery_bonus(self):
        """Verify auto-delivery subscriber status is shown."""
        context = [
            {
                "type": "customer_balance",
                "current_balance": 300,
                "tier": "Bronze",
                "auto_delivery_subscriber": True,
            }
        ]
        result = format_loyalty(context)
        assert "Auto-Delivery" in result
        assert "2X" in result or "2x" in result

    def test_shows_expiring_points_warning(self):
        """Verify expiring points warning is shown."""
        context = [
            {
                "type": "customer_balance",
                "current_balance": 200,
                "tier": "Bronze",
                "points_expiring_30_days": 50,
            }
        ]
        result = format_loyalty(context)
        assert "50" in result
        assert "expir" in result.lower()

    def test_shows_available_redemptions(self):
        """Verify available redemptions are shown."""
        context = [
            {
                "type": "customer_balance",
                "current_balance": 500,
                "tier": "Silver",
            },
            {
                "type": "redemption_tiers",
                "tiers": [
                    {"points_required": 100, "discount_display": "$5 off"},
                    {"points_required": 250, "discount_display": "$15 off"},
                    {"points_required": 500, "discount_display": "$30 off"},
                ],
            },
        ]
        result = format_loyalty(context)
        assert "Redeem" in result
        assert "$5" in result or "$15" in result or "$30" in result

    def test_shows_points_needed_if_below_minimum(self):
        """Verify points needed message for low balance."""
        context = [
            {
                "type": "customer_balance",
                "current_balance": 50,
                "tier": "Bronze",
            },
            {
                "type": "redemption_tiers",
                "tiers": [
                    {"points_required": 100, "discount_display": "$5 off"},
                ],
            },
        ]
        result = format_loyalty(context)
        assert "50" in result  # Points needed
        assert "more" in result.lower() or "need" in result.lower()

    def test_with_program_sections(self):
        """Verify formatting with program sections."""
        context = [
            {
                "type": "policy",
                "source": "loyalty_program",
                "title": "BrewVi Rewards",
                "quick_answer": "Earn points on every purchase!",
            }
        ]
        result = format_loyalty(context)
        assert "BrewVi" in result
        assert "Earn points" in result

    def test_with_membership_tiers(self):
        """Verify membership tiers are shown."""
        context = [
            {
                "type": "policy",
                "source": "loyalty_program",
                "title": "Loyalty Program",
            },
            {
                "type": "membership_tiers",
                "tiers": [
                    {"tier_name": "Bronze", "earning_rate": 1.0},
                    {"tier_name": "Silver", "earning_rate": 1.25},
                    {"tier_name": "Gold", "earning_rate": 1.5},
                ],
            },
        ]
        result = format_loyalty(context)
        assert "Bronze" in result
        assert "Silver" in result
        assert "Gold" in result

    def test_gold_tier_emoji(self):
        """Verify Gold tier shows special emoji."""
        context = [
            {
                "type": "customer_balance",
                "current_balance": 1000,
                "tier": "Gold",
            }
        ]
        result = format_loyalty(context)
        assert "🌟" in result or "Gold" in result

    def test_silver_tier_emoji(self):
        """Verify Silver tier shows star emoji."""
        context = [
            {
                "type": "customer_balance",
                "current_balance": 500,
                "tier": "Silver",
            }
        ]
        result = format_loyalty(context)
        assert "⭐" in result or "Silver" in result


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestFormatterEdgeCases:
    """Tests for edge cases in formatters."""

    def test_shipping_empty_title(self):
        """Verify empty title in shipping context is handled."""
        context = [
            {
                "source": "shipping_info",
                "title": "",
                "content": "Ships fast!",
            }
        ]
        result = format_shipping_question(context)
        assert "Ships fast!" in result or "shipping" in result.lower()

    def test_subscription_empty_benefits(self):
        """Verify empty benefits list is handled."""
        context = [
            {
                "source": "subscription_info",
                "benefits": [],
            }
        ]
        result = format_subscription(context)
        assert "Managing Your Subscription" in result

    def test_loyalty_empty_customer_name(self):
        """Verify empty customer name is handled."""
        context = [
            {
                "type": "customer_balance",
                "customer_name": "",
                "current_balance": 100,
                "tier": "Bronze",
            }
        ]
        result = format_loyalty(context)
        # Should not have greeting with empty name
        assert "Hi ," not in result

    def test_loyalty_zero_balance(self):
        """Verify zero balance is handled."""
        context = [
            {
                "type": "customer_balance",
                "current_balance": 0,
                "tier": "Bronze",
            }
        ]
        result = format_loyalty(context)
        assert "0" in result
        assert "points" in result.lower()

    def test_loyalty_no_next_tier(self):
        """Verify missing next_tier is handled."""
        context = [
            {
                "type": "customer_balance",
                "current_balance": 2000,
                "tier": "Gold",
                "next_tier": None,  # Already at top tier
            }
        ]
        result = format_loyalty(context)
        assert "Gold" in result

    def test_unicode_in_context(self):
        """Verify unicode characters in context are handled."""
        context = [
            {
                "source": "shipping_info",
                "title": "Envío Rápido",
                "content": "Café ☕ ships fast!",
            }
        ]
        result = format_shipping_question(context)
        # Should not raise exception
        assert "Envío" in result or "Café" in result

    def test_very_long_content(self):
        """Verify very long content is handled."""
        long_content = "This is shipping information. " * 100
        context = [
            {
                "source": "shipping_policy",
                "title": "Shipping",
                "content": long_content,
            }
        ]
        result = format_shipping_question(context)
        # Should not raise exception
        assert len(result) > 0
