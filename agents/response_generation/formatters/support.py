"""
Support-related response formatters.

Handles: SHIPPING_QUESTION, AUTO_DELIVERY_MANAGEMENT, GIFT_CARD, LOYALTY_PROGRAM
"""

from typing import List, Dict, Any

from agents.response_generation.formatters.product import format_product_info


def format_shipping_question(knowledge_context: List[Dict[str, Any]]) -> str:
    """Format shipping information response."""
    shipping_items = [
        item
        for item in knowledge_context
        if "shipping" in item.get("source", "").lower()
    ]

    if not shipping_items:
        return (
            "I'm happy to help with shipping information!\n\n"
            "**Standard Shipping (USPS Priority Mail):**\n"
            "- FREE on orders over $75\n"
            "- FREE for all auto-delivery subscribers\n"
            "- 3-5 business days delivery\n"
            "- $8.50 for orders under $75\n\n"
            "**Express Shipping Options:**\n"
            "- UPS 2-Day: $15\n"
            "- UPS Next Day: $25\n\n"
            "We also ship to Canada and Mexico! Do you have a specific shipping question?"
        )

    shipping_info = shipping_items[0]
    title = shipping_info.get("title", "")
    content = shipping_info.get("content", "")
    quick_answer = shipping_info.get("quick_answer", "")

    response = f"""**{title}**

{quick_answer if quick_answer else content}

"""

    scenarios = [
        item for item in shipping_items if item.get("type") == "recommendation"
    ]
    if scenarios:
        response += "**Recommendations:**\n"
        for scenario in scenarios[:2]:
            rec = scenario.get("recommendation", "")
            cost = scenario.get("typical_cost", "")
            response += f"- {rec} ({cost})\n"
        response += "\n"

    response += "Do you have any other shipping questions?"

    return response


def format_subscription(knowledge_context: List[Dict[str, Any]]) -> str:
    """Format auto-delivery subscription response."""
    sub_items = [
        item
        for item in knowledge_context
        if "subscription" in item.get("source", "").lower()
    ]

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
        response = (
            "Our Auto-Delivery subscription ensures you never run out of your favorite coffee!\n\n"
            "**Benefits:**\n"
            "✓ Free shipping on every order\n"
            "✓ Flexible scheduling\n"
            "✓ Skip or modify anytime\n"
            "✓ No commitment - cancel anytime\n\n"
            "Would you like to set up auto-delivery for your favorite coffee?"
        )

    return response


def format_gift_card(knowledge_context: List[Dict[str, Any]]) -> str:
    """Format gift card information response."""
    # Check if products are in context (product info query)
    products = [item for item in knowledge_context if item.get("type") == "product"]

    if products:
        return format_product_info(knowledge_context)

    # Policy information response
    gift_items = [
        item for item in knowledge_context if "gift" in item.get("source", "").lower()
    ]

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
        response = (
            "Gift cards are a perfect gift for any coffee lover!\n\n"
            "**Options:**\n"
            "- Virtual Gift Card (instant email delivery)\n"
            "- Physical Gift Card (beautiful gift packaging, 2-5 business days)\n\n"
            "**Amounts:** $25 to $200\n"
            "**Expiration:** Never\n\n"
            "Would you like to purchase a gift card?"
        )

    return response


def format_loyalty(knowledge_context: List[Dict[str, Any]]) -> str:
    """Format loyalty program information response with personalized balance."""
    # Extract customer balance
    balance_data = None
    for item in knowledge_context:
        if item.get("type") == "customer_balance":
            balance_data = item
            break

    # Extract program info
    program_sections = [
        item
        for item in knowledge_context
        if item.get("type") == "policy" and "loyalty" in item.get("source", "").lower()
    ]

    redemption_tiers = None
    membership_tiers = None
    for item in knowledge_context:
        if item.get("type") == "redemption_tiers":
            redemption_tiers = item.get("tiers", [])
        elif item.get("type") == "membership_tiers":
            membership_tiers = item.get("tiers", [])

    # Personalized response
    if balance_data:
        customer_name = (
            balance_data.get("customer_name", "").split()[0]
            if balance_data.get("customer_name")
            else ""
        )
        greeting = f"Hi {customer_name},\n\n" if customer_name else ""

        current_balance = balance_data.get("current_balance", 0)
        tier = balance_data.get("tier", "Bronze")
        points_to_next_tier = balance_data.get("points_to_next_tier", 0)
        next_tier = balance_data.get("next_tier")
        points_expiring = balance_data.get("points_expiring_30_days", 0)
        auto_delivery = balance_data.get("auto_delivery_subscriber", False)

        # Calculate redemption options
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

        if next_tier and points_to_next_tier > 0:
            response += (
                f"\n**Progress to {next_tier}:** {points_to_next_tier} points away"
            )

        if auto_delivery:
            response += "\n**Status:** Auto-Delivery Subscriber (2X points!)"

        if points_expiring > 0:
            response += (
                f"\n⚠️ **Expiring Soon:** {points_expiring} points expire in 30 days"
            )

        if available_redemptions:
            response += "\n\n**You Can Redeem:**\n"
            for option in available_redemptions[:3]:
                response += f"✓ {option}\n"
        else:
            if (
                redemption_tiers
                and redemption_tiers[0].get("points_required", 0) > current_balance
            ):
                points_needed = redemption_tiers[0]["points_required"] - current_balance
                response += f"\n\nYou need {points_needed} more points to redeem your first reward!"

        if program_sections:
            for section in program_sections:
                section_id = section.get("section_id", "")
                if "earn" in section_id or "redeem" in section_id:
                    quick_answer = section.get("quick_answer", "")
                    if quick_answer:
                        response += f"\n\n**How it Works:** {quick_answer}"
                        break

        response += "\n\nRedeem your points at checkout on your next purchase!"

    # General response
    elif program_sections:
        loyalty_info = program_sections[0]
        title = loyalty_info.get("title", "Loyalty Rewards Program")
        quick_answer = loyalty_info.get("quick_answer", "")

        response = f"**{title}**\n\n"

        if quick_answer:
            response += f"{quick_answer}\n\n"

        if redemption_tiers:
            response += "**Redemption Options:**\n"
            for tier_info in redemption_tiers[:4]:
                response += f"✓ {tier_info['points_required']} points = {tier_info['discount_display']}\n"
            response += "\n"

        if membership_tiers:
            response += "**Membership Tiers:**\n"
            for tier_info in membership_tiers:
                tier_name = tier_info.get("tier_name", "")
                earning_rate = tier_info.get("earning_rate", 1.0)
                response += f"✓ **{tier_name}:** {earning_rate}x points per $1\n"
            response += "\n"

        response += (
            "**How to Join:** Automatic enrollment with your first purchase!\n\n"
        )
        response += "Check your points balance anytime in your account dashboard."

    # Fallback response
    else:
        response = (
            "**Loyalty Rewards Program**\n\n"
            "Earn points with every purchase!\n\n"
            "✓ 1 point per $1 spent\n"
            "✓ 2x points for auto-delivery subscribers\n"
            "✓ 100 points = $5 reward\n"
            "✓ Birthday bonus points\n"
            "✓ Referral rewards\n\n"
            "You're automatically enrolled with your first purchase. Questions about your points?"
        )

    return response
