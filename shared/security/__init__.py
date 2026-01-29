"""
Security Utilities Module

This module provides security utilities for the AGNTCY Customer Service Platform:
- Input sanitization and prompt injection detection
- Rate limiting (sliding window algorithm)
- PII scrubbing for logs
- Session validation

Educational Notes:
- Defense in depth: Multiple layers of validation
- Input validation happens before AI processing
- Rate limiting prevents abuse and controls costs
- PII scrubbing protects customer privacy in logs

See: docs/SECURITY-REMEDIATION-2026-01-28.md for security findings and remediation
"""

from .input_sanitizer import (
    InputSanitizer,
    sanitize_message,
    detect_prompt_injection,
    SanitizationResult,
)
from .rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    RateLimitResult,
)
from .pii_scrubber import (
    PIIScrubber,
    scrub_pii,
)

__all__ = [
    # Input Sanitization
    "InputSanitizer",
    "sanitize_message",
    "detect_prompt_injection",
    "SanitizationResult",
    # Rate Limiting
    "RateLimiter",
    "RateLimitConfig",
    "RateLimitResult",
    # PII Scrubbing
    "PIIScrubber",
    "scrub_pii",
]
