"""
Product-related response formatters.

Handles: PRODUCT_INFO, PRODUCT_RECOMMENDATION, PRODUCT_COMPARISON, BREWER_SUPPORT
"""

from typing import List, Dict, Any


def format_product_info(knowledge_context: List[Dict[str, Any]]) -> str:
    """Format detailed product information response."""
    products = [item for item in knowledge_context if item.get("type") == "product"]

    if not products:
        return (
            "I'd be happy to help you learn about our coffee and brewing products!\n\n"
            "**What we offer:**\n"
            "- **Brewers:** Premium single-serve coffee makers with smart features\n"
            "- **Coffee Pods:** Light, medium, dark roasts, espresso, matcha, chai\n"
            "- **Variety Packs:** Explorer packs and office bundles\n"
            "- **Accessories:** Descaling solution, cleaning pods, travel mugs\n"
            "- **Gift Cards:** Virtual and physical options\n\n"
            "What specific product are you interested in?"
        )

    product = products[0]

    # Extract product fields
    name = product.get("name", "Product")
    description = product.get("description", "")
    price = product.get("price", 0)
    category = product.get("category", "").title()
    sku = product.get("sku", "")
    features = product.get("features", [])
    in_stock = product.get("in_stock", True)
    inventory_count = product.get("inventory_count")
    variant_name = product.get("variant_name", "")

    features_text = (
        "\n".join([f"- {feature}" for feature in features]) if features else ""
    )

    response = f"""**{name}**"""

    if variant_name:
        response += f" ({variant_name})"

    response += f"""
Category: {category}
Price: ${price:.2f}"""

    if sku:
        response += f"\nSKU: {sku}"

    response += f"\n\n{description}\n\n"

    if features_text:
        response += f"""**Key Features:**
{features_text}

"""

    # Stock availability
    if not in_stock:
        response += "**Availability:** Currently out of stock.\n\n"
        response += "Would you like me to notify you when this item is back in stock? "
        response += "I can also suggest similar products that are available now.\n\n"
    elif inventory_count is not None and inventory_count <= 5:
        response += (
            f"**Availability:** Only {inventory_count} left in stock - order soon!\n\n"
        )
    else:
        response += "**Availability:** In stock and ready to ship!\n\n"

    # Related products
    if len(products) > 1:
        response += "**You might also like:**\n"
        for other_product in products[1:3]:
            other_name = other_product.get("name", "")
            other_price = other_product.get("price", 0)
            other_in_stock = other_product.get("in_stock", True)
            stock_indicator = " ✓ In stock" if other_in_stock else " (Out of stock)"
            response += f"- {other_name} (${other_price:.2f}){stock_indicator}\n"
        response += "\n"

    response += "Would you like to know more about this product, or can I help you with something else?"

    return response


def format_product_recommendation(knowledge_context: List[Dict[str, Any]]) -> str:
    """Format personalized product recommendations."""
    recommendations = [
        item for item in knowledge_context if item.get("type") == "recommendation"
    ]

    if not recommendations:
        return (
            "I'd love to help you find the perfect coffee! Tell me about your preferences:\n"
            "- Do you prefer light, medium, or dark roast?\n"
            "- Are you looking for espresso or regular coffee?\n"
            "- Any flavor notes you enjoy (fruity, chocolatey, bold)?\n\n"
            "I'll recommend the perfect pods for you!"
        )

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


def format_product_comparison(knowledge_context: List[Dict[str, Any]]) -> str:
    """Format product comparison response."""
    products = [item for item in knowledge_context if item.get("type") == "product"]

    if len(products) < 2:
        return (
            "I can help you compare our products! Which items would you like to compare? "
            "For example, I can compare different brewers, coffee roasts, or variety packs."
        )

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


def format_brewer_support(knowledge_context: List[Dict[str, Any]]) -> str:
    """Format brewer troubleshooting response."""
    # Check if products are in context (product info query, not troubleshooting)
    products = [item for item in knowledge_context if item.get("type") == "product"]

    if products:
        return format_product_info(knowledge_context)

    # Troubleshooting response
    support_items = [
        item for item in knowledge_context if item.get("source") == "brewer_support"
    ]

    if not support_items:
        return (
            "I'm here to help with your brewer! Common issues I can assist with:\n"
            "- Brewer won't turn on or power issues\n"
            "- Coffee tastes weak or off\n"
            "- Cleaning and descaling\n"
            "- Error messages\n\n"
            "What specific issue are you experiencing?"
        )

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
            response += (
                "If none of these steps resolve the problem, I'll escalate this to our technical support team "
                "who can arrange a replacement if needed. Your brewer is covered by a 2-year warranty."
            )

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
