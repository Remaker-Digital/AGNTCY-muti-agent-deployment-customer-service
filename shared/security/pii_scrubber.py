"""
PII Scrubber for Logs and Telemetry

This module provides PII (Personally Identifiable Information) scrubbing to:
1. Remove sensitive data from log messages
2. Protect customer privacy in telemetry
3. Comply with GDPR and data protection requirements

Educational Notes:
- PII includes: names, emails, phones, addresses, IDs
- We use regex patterns to detect and replace PII
- Replacement uses consistent tokens for correlation without exposure
- This is a defense layer - don't log PII in the first place when possible

Pattern Categories:
1. Email addresses
2. Phone numbers (various formats)
3. Credit card numbers
4. IP addresses
5. Order/Customer IDs (project-specific patterns)

See: docs/SECURITY-REMEDIATION-2026-01-28.md
"""

import re
import hashlib
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ScrubResult:
    """Result of PII scrubbing."""

    original_length: int
    scrubbed_text: str
    pii_found: List[str]  # Types of PII found (not the values!)
    scrub_count: int


# =============================================================================
# PII Patterns
# =============================================================================

PII_PATTERNS = {
    "email": (
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "[EMAIL_REDACTED]"
    ),
    "phone_us": (
        r'\b(?:\+1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
        "[PHONE_REDACTED]"
    ),
    "phone_intl": (
        r'\+[0-9]{1,3}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,9}',
        "[PHONE_REDACTED]"
    ),
    "credit_card": (
        r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
        "[CC_REDACTED]"
    ),
    "ssn": (
        r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
        "[SSN_REDACTED]"
    ),
    "ipv4": (
        r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        "[IP_REDACTED]"
    ),
    "ipv6": (
        r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b',
        "[IP_REDACTED]"
    ),
    # Project-specific patterns
    "order_id": (
        r'\b(?:ORD|ORDER)[-_]?[A-Z0-9]{5,12}\b',
        "[ORDER_ID_REDACTED]"
    ),
    "customer_id": (
        r'\b(?:CUST|CID)[-_]?[A-Z0-9]{6,12}\b',
        "[CUSTOMER_ID_REDACTED]"
    ),
    "session_id": (
        r'\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b',
        "[SESSION_REDACTED]"
    ),
}


class PIIScrubber:
    """
    PII scrubber with configurable patterns.

    Usage:
        scrubber = PIIScrubber()
        result = scrubber.scrub("Contact john@example.com for order ORD-123456")
        print(result.scrubbed_text)
        # "Contact [EMAIL_REDACTED] for order [ORDER_ID_REDACTED]"
    """

    def __init__(
        self,
        enabled_patterns: Optional[Set[str]] = None,
        use_hashed_tokens: bool = False,
        hash_salt: Optional[str] = None,
    ):
        """
        Initialize the scrubber.

        Args:
            enabled_patterns: Set of pattern names to enable (None = all)
            use_hashed_tokens: Whether to use hashed tokens for correlation
            hash_salt: Salt for hashing (required if use_hashed_tokens=True)
        """
        self.use_hashed_tokens = use_hashed_tokens
        self.hash_salt = hash_salt or "agntcy-pii-salt"

        # Compile patterns
        if enabled_patterns:
            self._patterns = {
                name: (re.compile(pattern, re.IGNORECASE), replacement)
                for name, (pattern, replacement) in PII_PATTERNS.items()
                if name in enabled_patterns
            }
        else:
            self._patterns = {
                name: (re.compile(pattern, re.IGNORECASE), replacement)
                for name, (pattern, replacement) in PII_PATTERNS.items()
            }

    def scrub(self, text: str) -> ScrubResult:
        """
        Scrub PII from text.

        Args:
            text: Text to scrub

        Returns:
            ScrubResult with scrubbed text and metadata
        """
        if not text:
            return ScrubResult(
                original_length=0,
                scrubbed_text="",
                pii_found=[],
                scrub_count=0,
            )

        original_length = len(text)
        scrubbed = text
        pii_found = []
        scrub_count = 0

        for pattern_name, (pattern, replacement) in self._patterns.items():
            matches = pattern.findall(scrubbed)
            if matches:
                pii_found.append(pattern_name)
                scrub_count += len(matches)

                if self.use_hashed_tokens:
                    # Replace with hashed tokens for correlation
                    def replace_with_hash(match):
                        value = match.group(0)
                        hash_input = f"{self.hash_salt}:{value}"
                        hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:8]
                        base_replacement = replacement.rstrip("]")
                        return f"{base_replacement}:{hash_value}]"

                    scrubbed = pattern.sub(replace_with_hash, scrubbed)
                else:
                    # Replace with static token
                    scrubbed = pattern.sub(replacement, scrubbed)

        return ScrubResult(
            original_length=original_length,
            scrubbed_text=scrubbed,
            pii_found=pii_found,
            scrub_count=scrub_count,
        )

    def contains_pii(self, text: str) -> bool:
        """
        Check if text contains PII without modifying it.

        Args:
            text: Text to check

        Returns:
            True if PII detected
        """
        for _, (pattern, _) in self._patterns.items():
            if pattern.search(text):
                return True
        return False


# =============================================================================
# Module-level instance and convenience functions
# =============================================================================

_default_scrubber: Optional[PIIScrubber] = None


def get_pii_scrubber() -> PIIScrubber:
    """Get or create the default PII scrubber instance."""
    global _default_scrubber
    if _default_scrubber is None:
        _default_scrubber = PIIScrubber()
    return _default_scrubber


def scrub_pii(text: str) -> str:
    """
    Scrub PII from text using the default scrubber.

    Args:
        text: Text to scrub

    Returns:
        Scrubbed text
    """
    result = get_pii_scrubber().scrub(text)
    return result.scrubbed_text


# =============================================================================
# Logging Integration
# =============================================================================

class PIIScrubFilter(logging.Filter):
    """
    Logging filter that scrubs PII from log messages.

    Usage:
        logger = logging.getLogger("my_module")
        logger.addFilter(PIIScrubFilter())
    """

    def __init__(self, scrubber: Optional[PIIScrubber] = None):
        super().__init__()
        self.scrubber = scrubber or get_pii_scrubber()

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and scrub log record."""
        if isinstance(record.msg, str):
            result = self.scrubber.scrub(record.msg)
            record.msg = result.scrubbed_text

            # Also scrub args if present
            if record.args:
                scrubbed_args = []
                for arg in record.args:
                    if isinstance(arg, str):
                        scrubbed_args.append(self.scrubber.scrub(arg).scrubbed_text)
                    else:
                        scrubbed_args.append(arg)
                record.args = tuple(scrubbed_args)

        return True  # Always allow the record through
