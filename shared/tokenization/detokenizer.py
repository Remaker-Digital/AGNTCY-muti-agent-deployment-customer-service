"""
PII De-tokenizer Module

Replaces tokens in text with original PII values for responses to customers.
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
import time

from .token_store import TokenStore, get_token_store

logger = logging.getLogger(__name__)


@dataclass
class DetokenizationResult:
    """Result of de-tokenizing text."""
    tokenized_text: str
    detokenized_text: str
    tokens_resolved: int
    tokens_not_found: List[str]
    processing_time_ms: float = 0.0


class PIIDetokenizer:
    """
    De-tokenizes text by replacing tokens with original PII values.

    Usage:
        detokenizer = PIIDetokenizer()
        result = await detokenizer.detokenize("Contact TOKEN_abc123...")
        # result.detokenized_text = "Contact john@email.com"
    """

    # Pattern to match our token format
    TOKEN_PATTERN = re.compile(r'TOKEN_[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}')

    def __init__(self, token_store: Optional[TokenStore] = None):
        """
        Initialize the de-tokenizer.

        Args:
            token_store: Storage backend for token mappings
        """
        self._store = token_store

    def _get_store(self) -> TokenStore:
        """Get the token store (lazy initialization)."""
        if self._store is None:
            self._store = get_token_store()
        return self._store

    async def detokenize(self, text: str) -> DetokenizationResult:
        """
        De-tokenize all tokens in the given text.

        Args:
            text: Text containing tokens to de-tokenize

        Returns:
            DetokenizationResult with original PII restored
        """
        start_time = time.time()

        if not text:
            return DetokenizationResult(
                tokenized_text=text,
                detokenized_text=text,
                tokens_resolved=0,
                tokens_not_found=[]
            )

        # Find all tokens in the text
        tokens = self.TOKEN_PATTERN.findall(text)

        if not tokens:
            return DetokenizationResult(
                tokenized_text=text,
                detokenized_text=text,
                tokens_resolved=0,
                tokens_not_found=[],
                processing_time_ms=(time.time() - start_time) * 1000
            )

        # Remove duplicates while preserving order
        unique_tokens = list(dict.fromkeys(tokens))

        # Look up all tokens
        store = self._get_store()
        resolved: Dict[str, str] = {}
        not_found: List[str] = []

        for token in unique_tokens:
            mapping = await store.retrieve(token)
            if mapping:
                resolved[token] = mapping.original_value
            else:
                not_found.append(token)
                logger.warning(f"Token not found in store: {token[:30]}...")

        # Replace tokens with original values
        detokenized_text = text
        for token, original in resolved.items():
            detokenized_text = detokenized_text.replace(token, original)

        processing_time = (time.time() - start_time) * 1000

        logger.info(
            f"De-tokenized {len(resolved)} tokens in {processing_time:.2f}ms "
            f"({len(not_found)} not found)"
        )

        return DetokenizationResult(
            tokenized_text=text,
            detokenized_text=detokenized_text,
            tokens_resolved=len(resolved),
            tokens_not_found=not_found,
            processing_time_ms=processing_time
        )

    async def detokenize_dict(
        self,
        data: Dict,
        fields_to_detokenize: Optional[List[str]] = None
    ) -> DetokenizationResult:
        """
        De-tokenize tokens in specific fields of a dictionary.

        Args:
            data: Dictionary containing fields to de-tokenize
            fields_to_detokenize: List of field names to check (None = all string fields)

        Returns:
            DetokenizationResult with de-tokenized dictionary
        """
        # Collect all tokens from all fields first
        all_tokens: Set[str] = set()
        fields = fields_to_detokenize or [
            k for k, v in data.items() if isinstance(v, str)
        ]

        for field_name in fields:
            if field_name not in data or not isinstance(data[field_name], str):
                continue
            tokens = self.TOKEN_PATTERN.findall(data[field_name])
            all_tokens.update(tokens)

        if not all_tokens:
            return DetokenizationResult(
                tokenized_text="",
                detokenized_text="",
                tokens_resolved=0,
                tokens_not_found=[]
            )

        # Look up all tokens once
        store = self._get_store()
        resolved: Dict[str, str] = {}
        not_found: List[str] = []

        start_time = time.time()

        for token in all_tokens:
            mapping = await store.retrieve(token)
            if mapping:
                resolved[token] = mapping.original_value
            else:
                not_found.append(token)

        # Apply replacements to each field
        result_data = data.copy()
        for field_name in fields:
            if field_name not in data or not isinstance(data[field_name], str):
                continue
            field_value = data[field_name]
            for token, original in resolved.items():
                field_value = field_value.replace(token, original)
            result_data[field_name] = field_value

        processing_time = (time.time() - start_time) * 1000

        return DetokenizationResult(
            tokenized_text=str(data),
            detokenized_text=str(result_data),
            tokens_resolved=len(resolved),
            tokens_not_found=not_found,
            processing_time_ms=processing_time
        )

    async def detokenize_response(self, response: Dict) -> Dict:
        """
        De-tokenize a customer service response.

        Args:
            response: Response dictionary with possible tokens

        Returns:
            Dictionary with tokens replaced by original PII
        """
        result = response.copy()

        # Common response fields
        response_fields = [
            "content",
            "message",
            "response",
            "reply",
            "body",
        ]

        for field in response_fields:
            if field in result and isinstance(result[field], str):
                detok_result = await self.detokenize(result[field])
                result[field] = detok_result.detokenized_text

        return result

    def contains_tokens(self, text: str) -> bool:
        """
        Check if text contains any tokens.

        Args:
            text: Text to check

        Returns:
            True if tokens are found
        """
        return bool(self.TOKEN_PATTERN.search(text))

    def extract_tokens(self, text: str) -> List[str]:
        """
        Extract all tokens from text.

        Args:
            text: Text containing tokens

        Returns:
            List of token strings found
        """
        return self.TOKEN_PATTERN.findall(text)


# Convenience function for simple de-tokenization
async def detokenize_pii(text: str) -> DetokenizationResult:
    """
    Convenience function to de-tokenize text.

    Args:
        text: Text containing tokens

    Returns:
        DetokenizationResult
    """
    detokenizer = PIIDetokenizer()
    return await detokenizer.detokenize(text)
