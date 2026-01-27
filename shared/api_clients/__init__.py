"""
API Client Package for AGNTCY Multi-Agent Customer Service Platform

This package provides unified API clients for external service integrations:
- Shopify: Order management and product catalog
- Zendesk: Customer support ticket management
- Mailchimp: Email marketing and automation
- Google Analytics: Customer analytics and reporting

All clients support both mock (Phase 1-3) and real API (Phase 4-5) modes.

Usage:
    from shared.api_clients import get_shopify_client, get_zendesk_client

    # Clients auto-detect mock vs real API based on configuration
    shopify = await get_shopify_client()
    order = await shopify.get_order("ORD-12345")
"""

from .base import BaseAPIClient, APIClientConfig
from .shopify import ShopifyClient, get_shopify_client
from .zendesk import ZendeskClient, get_zendesk_client
from .mailchimp import MailchimpClient, get_mailchimp_client
from .google_analytics import GoogleAnalyticsClient, get_google_analytics_client

__all__ = [
    # Base
    "BaseAPIClient",
    "APIClientConfig",
    # Shopify
    "ShopifyClient",
    "get_shopify_client",
    # Zendesk
    "ZendeskClient",
    "get_zendesk_client",
    # Mailchimp
    "MailchimpClient",
    "get_mailchimp_client",
    # Google Analytics
    "GoogleAnalyticsClient",
    "get_google_analytics_client",
]
