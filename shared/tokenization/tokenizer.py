"""
PII Tokenizer Module

Replaces PII in text with tokens for safe transmission to third-party AI services.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .pii_detector import PIIDetector, PIIField, PIIType
from .token_store import TokenMapping, TokenStore, get_token_store

logger = logging.getLogger(__name__)


@dataclass
class TokenizationResult:
    """Result of tokenizing text."""
    original_text: str
    tokenized_text: str
    tokens_created: List[str]
    pii_fields_found: int
    token_mappings: Dict[str, str] = field(default_factory=dict)  # token -> pii_type
    processing_time_ms: float = 0.0
    context_id: Optional[str] = None


class PIITokenizer:
    """
    Tokenizes PII in text by replacing detected PII with secure tokens.

    Usage:
        tokenizer = PIITokenizer()
        result = await tokenizer.tokenize("Contact john@email.com")
        # result.tokenized_text = "Contact TOKEN_abc123..."
    """

    def __init__(
        self,
        token_store: Optional[TokenStore] = None,
        detector: Optional[PIIDetector] = None,
        min_confidence: float = 0.7
    ):
        """
        Initialize the tokenizer.

        Args:
            token_store: Storage backend for token mappings
            detector: PII detector instance
            min_confidence: Minimum confidence for PII detection
        """
        self._store = token_store
        self._detector = detector or PIIDetector(min_confidence=min_confidence)

    def _get_store(self) -> TokenStore:
        """Get the token store (lazy initialization)."""
        if self._store is None:
            self._store = get_token_store()
        return self._store

    async def tokenize(
        self,
        text: str,
        context_id: Optional[str] = None,
        pii_types: Optional[List[PIIType]] = None
    ) -> TokenizationResult:
        """
        Tokenize all PII in the given text.

        Args:
            text: Text containing PII to tokenize
            context_id: Optional context ID for grouping tokens (conversation/session)
            pii_types: Optional list of specific PII types to tokenize (None = all)

        Returns:
            TokenizationResult with tokenized text and metadata
        """
        import time
        start_time = time.time()

        if not text:
            return TokenizationResult(
                original_text=text,
                tokenized_text=text,
                tokens_created=[],
                pii_fields_found=0,
                context_id=context_id
            )

        # Detect PII
        detected = self._detector.detect(text)

        # Filter by requested PII types
        if pii_types:
            detected = [f for f in detected if f.pii_type in pii_types]

        if not detected:
            return TokenizationResult(
                original_text=text,
                tokenized_text=text,
                tokens_created=[],
                pii_fields_found=0,
                processing_time_ms=(time.time() - start_time) * 1000,
                context_id=context_id
            )

        # Create tokens and store mappings
        store = self._get_store()
        tokens_created: List[str] = []
        token_mappings: Dict[str, str] = {}
        replacements: List[Tuple[int, int, str]] = []

        for pii_field in detected:
            # Generate a unique token
            token = store.generate_token()

            # Create mapping
            mapping = TokenMapping(
                token=token,
                original_value=pii_field.value,
                pii_type=pii_field.pii_type.value,
                created_at=datetime.utcnow(),
                context_id=context_id
            )

            # Store the mapping
            if await store.store(mapping):
                tokens_created.append(token)
                token_mappings[token] = pii_field.pii_type.value
                replacements.append((pii_field.start, pii_field.end, token))
            else:
                logger.warning(f"Failed to store token mapping for {pii_field.pii_type}")

        # Apply replacements (working backwards to preserve positions)
        tokenized_text = text
        for start, end, token in sorted(replacements, reverse=True):
            tokenized_text = tokenized_text[:start] + token + tokenized_text[end:]

        processing_time = (time.time() - start_time) * 1000

        logger.info(
            f"Tokenized {len(detected)} PII fields in {processing_time:.2f}ms "
            f"(context: {context_id})"
        )

        return TokenizationResult(
            original_text=text,
            tokenized_text=tokenized_text,
            tokens_created=tokens_created,
            pii_fields_found=len(detected),
            token_mappings=token_mappings,
            processing_time_ms=processing_time,
            context_id=context_id
        )

    async def tokenize_dict(
        self,
        data: Dict,
        context_id: Optional[str] = None,
        fields_to_tokenize: Optional[List[str]] = None
    ) -> Tuple[Dict, TokenizationResult]:
        """
        Tokenize PII in specific fields of a dictionary.

        Args:
            data: Dictionary containing fields to tokenize
            context_id: Optional context ID
            fields_to_tokenize: List of field names to check (None = all string fields)

        Returns:
            Tuple of (tokenized dictionary, combined result)
        """
        result_data = data.copy()
        all_tokens: List[str] = []
        all_mappings: Dict[str, str] = {}
        total_pii = 0
        total_time = 0.0

        fields = fields_to_tokenize or [
            k for k, v in data.items() if isinstance(v, str)
        ]

        for field_name in fields:
            if field_name not in data or not isinstance(data[field_name], str):
                continue

            result = await self.tokenize(data[field_name], context_id)
            result_data[field_name] = result.tokenized_text
            all_tokens.extend(result.tokens_created)
            all_mappings.update(result.token_mappings)
            total_pii += result.pii_fields_found
            total_time += result.processing_time_ms

        combined_result = TokenizationResult(
            original_text="",  # Not applicable for dict tokenization
            tokenized_text="",
            tokens_created=all_tokens,
            pii_fields_found=total_pii,
            token_mappings=all_mappings,
            processing_time_ms=total_time,
            context_id=context_id
        )

        return result_data, combined_result

    async def tokenize_message(
        self,
        message: Dict,
        context_id: Optional[str] = None
    ) -> Tuple[Dict, TokenizationResult]:
        """
        Tokenize PII in a customer service message.

        Handles common message format with 'content', 'customer_name',
        'customer_email', etc.

        Args:
            message: Message dictionary
            context_id: Conversation context ID

        Returns:
            Tuple of (tokenized message, result)
        """
        # Common fields that may contain PII
        pii_fields = [
            "content",
            "message",
            "customer_name",
            "customer_email",
            "customer_phone",
            "customer_address",
            "order_id",
            "tracking_number",
            "notes",
        ]

        return await self.tokenize_dict(
            message,
            context_id,
            fields_to_tokenize=pii_fields
        )


# Convenience function for simple tokenization
async def tokenize_pii(
    text: str,
    context_id: Optional[str] = None
) -> TokenizationResult:
    """
    Convenience function to tokenize PII in text.

    Args:
        text: Text to tokenize
        context_id: Optional context ID

    Returns:
        TokenizationResult
    """
    tokenizer = PIITokenizer()
    return await tokenizer.tokenize(text, context_id)
