"""
PII Detection Module

Detects PII (Personally Identifiable Information) in text using
regex patterns and simple entity recognition.

Detected PII types:
- Customer Information: names, emails, phones, addresses
- Order/Transaction Data: order IDs, tracking numbers, payment info
- Support Data: ticket IDs
- Other: IP addresses, device IDs
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class PIIType(Enum):
    """Types of PII that can be detected."""
    EMAIL = "email"
    PHONE = "phone"
    CREDIT_CARD = "credit_card"
    SSN = "ssn"
    ADDRESS = "address"
    ORDER_ID = "order_id"
    TRACKING_NUMBER = "tracking_number"
    TICKET_ID = "ticket_id"
    CUSTOMER_ID = "customer_id"
    IP_ADDRESS = "ip_address"
    NAME = "name"
    ZIP_CODE = "zip_code"
    ACCOUNT_NUMBER = "account_number"


@dataclass
class PIIField:
    """Represents a detected PII field in text."""
    pii_type: PIIType
    value: str
    start: int
    end: int
    confidence: float = 1.0


class PIIDetector:
    """
    Detects PII in text using regex patterns.

    This is a rule-based detector that identifies common PII patterns.
    For production use, consider augmenting with ML-based NER models.
    """

    # Regex patterns for PII detection
    PATTERNS = {
        PIIType.EMAIL: (
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            1.0  # High confidence for email
        ),
        PIIType.PHONE: (
            r'\b(?:\+?1[-.\s]?)?(?:\(?[0-9]{3}\)?[-.\s]?)?[0-9]{3}[-.\s]?[0-9]{4}\b',
            0.9  # Phone patterns can have false positives
        ),
        PIIType.CREDIT_CARD: (
            r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b',
            1.0  # High confidence for credit cards (Visa, MC, Amex, Discover)
        ),
        PIIType.CREDIT_CARD: (
            r'\b(?:4[0-9]{3}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}|'
            r'5[1-5][0-9]{2}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}|'
            r'3[47][0-9]{2}[-\s]?[0-9]{6}[-\s]?[0-9]{5}|'
            r'6(?:011|5[0-9]{2})[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4})\b',
            1.0
        ),
        PIIType.SSN: (
            r'\b(?!000|666|9\d{2})\d{3}[-\s]?(?!00)\d{2}[-\s]?(?!0000)\d{4}\b',
            0.85  # SSN patterns can match other numbers
        ),
        PIIType.IP_ADDRESS: (
            r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
            1.0
        ),
        PIIType.ZIP_CODE: (
            r'\b[0-9]{5}(?:-[0-9]{4})?\b',
            0.7  # Low confidence - many 5-digit numbers aren't zip codes
        ),
        PIIType.ORDER_ID: (
            r'\b(?:ORD|ORDER)[-_]?[A-Z0-9]{6,12}\b|#[A-Z0-9]{6,15}\b',
            0.95
        ),
        PIIType.TRACKING_NUMBER: (
            # UPS, FedEx, USPS patterns
            r'\b(?:1Z[A-Z0-9]{16}|'  # UPS
            r'[0-9]{12,22}|'  # FedEx/USPS
            r'[A-Z]{2}[0-9]{9}[A-Z]{2})\b',  # International
            0.8
        ),
        PIIType.TICKET_ID: (
            r'\b(?:TKT|TICKET|CASE|INC)[-_]?[A-Z0-9]{6,12}\b',
            0.95
        ),
        PIIType.CUSTOMER_ID: (
            r'\b(?:CUST|CID|CUSTOMER)[-_]?[A-Z0-9]{6,12}\b',
            0.95
        ),
        PIIType.ACCOUNT_NUMBER: (
            r'\b(?:ACCT|ACC|ACCOUNT)[-_#]?[0-9]{8,12}\b',
            0.9
        ),
    }

    # Context keywords that increase confidence for certain PII types
    CONTEXT_KEYWORDS = {
        PIIType.PHONE: ["phone", "call", "tel", "mobile", "cell", "contact"],
        PIIType.EMAIL: ["email", "mail", "contact", "reach"],
        PIIType.ORDER_ID: ["order", "purchase", "bought", "ordered"],
        PIIType.TRACKING_NUMBER: ["tracking", "shipment", "delivery", "shipped"],
        PIIType.ADDRESS: ["address", "deliver", "ship to", "street", "apt"],
        PIIType.CREDIT_CARD: ["card", "payment", "visa", "mastercard", "credit"],
        PIIType.CUSTOMER_ID: ["customer", "account", "member"],
    }

    def __init__(self, min_confidence: float = 0.7):
        """
        Initialize the PII detector.

        Args:
            min_confidence: Minimum confidence threshold for detection (0.0-1.0)
        """
        self.min_confidence = min_confidence
        self._compiled_patterns = {
            pii_type: re.compile(pattern, re.IGNORECASE)
            for pii_type, (pattern, _) in self.PATTERNS.items()
        }

    def detect(self, text: str) -> List[PIIField]:
        """
        Detect all PII fields in the given text.

        Args:
            text: The text to scan for PII

        Returns:
            List of PIIField objects representing detected PII
        """
        if not text:
            return []

        detected: List[PIIField] = []
        text_lower = text.lower()

        for pii_type, pattern in self._compiled_patterns.items():
            base_confidence = self.PATTERNS[pii_type][1]

            for match in pattern.finditer(text):
                # Adjust confidence based on context
                confidence = self._adjust_confidence(
                    pii_type, base_confidence, text_lower, match.start()
                )

                if confidence >= self.min_confidence:
                    detected.append(PIIField(
                        pii_type=pii_type,
                        value=match.group(),
                        start=match.start(),
                        end=match.end(),
                        confidence=confidence
                    ))

        # Sort by position in text
        detected.sort(key=lambda x: x.start)

        # Remove overlapping detections (keep higher confidence)
        return self._remove_overlaps(detected)

    def _adjust_confidence(
        self,
        pii_type: PIIType,
        base_confidence: float,
        text_lower: str,
        position: int
    ) -> float:
        """Adjust confidence based on context keywords."""
        keywords = self.CONTEXT_KEYWORDS.get(pii_type, [])
        if not keywords:
            return base_confidence

        # Check for context keywords within 50 characters of the match
        context_start = max(0, position - 50)
        context_end = min(len(text_lower), position + 50)
        context = text_lower[context_start:context_end]

        for keyword in keywords:
            if keyword in context:
                # Boost confidence by 10% for each keyword found
                base_confidence = min(1.0, base_confidence + 0.1)

        return base_confidence

    def _remove_overlaps(self, detected: List[PIIField]) -> List[PIIField]:
        """Remove overlapping detections, keeping higher confidence ones."""
        if len(detected) <= 1:
            return detected

        result: List[PIIField] = []
        for field in detected:
            overlaps = False
            for existing in result:
                if self._overlaps(field, existing):
                    if field.confidence > existing.confidence:
                        result.remove(existing)
                    else:
                        overlaps = True
                        break

            if not overlaps:
                result.append(field)

        return result

    def _overlaps(self, a: PIIField, b: PIIField) -> bool:
        """Check if two PIIField ranges overlap."""
        return not (a.end <= b.start or b.end <= a.start)

    def detect_by_type(self, text: str, pii_type: PIIType) -> List[PIIField]:
        """
        Detect specific type of PII in text.

        Args:
            text: The text to scan
            pii_type: The specific PII type to detect

        Returns:
            List of PIIField objects of the specified type
        """
        return [f for f in self.detect(text) if f.pii_type == pii_type]

    def contains_pii(self, text: str) -> bool:
        """
        Quick check if text contains any PII.

        Args:
            text: The text to check

        Returns:
            True if any PII is detected
        """
        return len(self.detect(text)) > 0

    def mask_pii(self, text: str, mask_char: str = "*") -> str:
        """
        Mask all detected PII in text with asterisks.

        Args:
            text: The text to mask
            mask_char: Character to use for masking

        Returns:
            Text with PII replaced by mask characters
        """
        detected = self.detect(text)
        if not detected:
            return text

        # Work backwards to preserve positions
        result = text
        for field in reversed(detected):
            mask = mask_char * len(field.value)
            result = result[:field.start] + mask + result[field.end:]

        return result
