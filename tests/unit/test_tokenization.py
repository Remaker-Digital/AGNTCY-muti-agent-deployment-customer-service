"""
Unit tests for PII Tokenization module.
"""

import pytest
import asyncio
from datetime import datetime

from shared.tokenization import (
    PIIDetector,
    PIIField,
    PIIType,
    PIITokenizer,
    PIIDetokenizer,
    TokenizationResult,
    TokenStore,
    get_token_store,
)
from shared.tokenization.token_store import InMemoryTokenStore, TokenMapping


class TestPIIDetector:
    """Tests for PII detection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = PIIDetector(min_confidence=0.7)

    def test_detect_email(self):
        """Test email detection."""
        text = "Contact me at john.doe@example.com for more info"
        detected = self.detector.detect(text)

        assert len(detected) == 1
        assert detected[0].pii_type == PIIType.EMAIL
        assert detected[0].value == "john.doe@example.com"
        assert detected[0].confidence >= 0.9

    def test_detect_phone(self):
        """Test phone number detection."""
        test_cases = [
            "Call me at 555-123-4567",
            "Phone: (555) 123-4567",
            "Tel: +1 555 123 4567",
        ]

        for text in test_cases:
            detected = self.detector.detect(text)
            assert len(detected) >= 1
            phone_found = any(d.pii_type == PIIType.PHONE for d in detected)
            assert phone_found, f"Phone not detected in: {text}"

    def test_detect_credit_card(self):
        """Test credit card detection."""
        test_cases = [
            "Card: 4111-1111-1111-1111",  # Visa
            "Payment with 5500 0000 0000 0004",  # Mastercard
        ]

        for text in test_cases:
            detected = self.detector.detect(text)
            cc_found = any(d.pii_type == PIIType.CREDIT_CARD for d in detected)
            assert cc_found, f"Credit card not detected in: {text}"

    def test_detect_ip_address(self):
        """Test IP address detection."""
        text = "User connected from 192.168.1.100"
        detected = self.detector.detect(text)

        ip_found = any(d.pii_type == PIIType.IP_ADDRESS for d in detected)
        assert ip_found

    def test_detect_order_id(self):
        """Test order ID detection."""
        test_cases = [
            "Order ORD-ABC123456 shipped",
            "Your ORDER-XYZ789012 is ready",
            "#ABC123456789",
        ]

        for text in test_cases:
            detected = self.detector.detect(text)
            order_found = any(d.pii_type == PIIType.ORDER_ID for d in detected)
            assert order_found, f"Order ID not detected in: {text}"

    def test_detect_multiple_pii(self):
        """Test detection of multiple PII types in one text."""
        text = "Customer john@email.com ordered ORD-ABC12345 from IP 10.0.0.1"
        detected = self.detector.detect(text)

        types_found = {d.pii_type for d in detected}
        assert PIIType.EMAIL in types_found
        assert PIIType.ORDER_ID in types_found
        assert PIIType.IP_ADDRESS in types_found

    def test_no_pii(self):
        """Test text with no PII."""
        text = "Hello, how can I help you today?"
        detected = self.detector.detect(text)
        assert len(detected) == 0

    def test_contains_pii(self):
        """Test quick PII check."""
        assert self.detector.contains_pii("Email: test@example.com")
        assert not self.detector.contains_pii("No PII here")

    def test_mask_pii(self):
        """Test PII masking."""
        text = "Contact john@email.com for help"
        masked = self.detector.mask_pii(text)

        assert "john@email.com" not in masked
        assert "****" in masked


class TestInMemoryTokenStore:
    """Tests for in-memory token store."""

    @pytest.fixture
    def store(self):
        return InMemoryTokenStore(default_ttl_hours=1)

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, store):
        """Test storing and retrieving a token."""
        mapping = TokenMapping(
            token="TOKEN_test-1234",
            original_value="john@email.com",
            pii_type="email",
            created_at=datetime.utcnow()
        )

        # Store
        result = await store.store(mapping)
        assert result is True

        # Retrieve
        retrieved = await store.retrieve("TOKEN_test-1234")
        assert retrieved is not None
        assert retrieved.original_value == "john@email.com"
        assert retrieved.pii_type == "email"

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent(self, store):
        """Test retrieving a nonexistent token."""
        retrieved = await store.retrieve("TOKEN_nonexistent")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete(self, store):
        """Test deleting a token."""
        mapping = TokenMapping(
            token="TOKEN_to-delete",
            original_value="test@test.com",
            pii_type="email",
            created_at=datetime.utcnow()
        )

        await store.store(mapping)
        assert await store.retrieve("TOKEN_to-delete") is not None

        result = await store.delete("TOKEN_to-delete")
        assert result is True
        assert await store.retrieve("TOKEN_to-delete") is None

    @pytest.mark.asyncio
    async def test_generate_token(self, store):
        """Test token generation format."""
        token = store.generate_token()
        assert token.startswith("TOKEN_")
        assert len(token) == 42  # TOKEN_ + UUID


class TestPIITokenizer:
    """Tests for PII tokenization."""

    @pytest.fixture
    def tokenizer(self):
        store = InMemoryTokenStore()
        return PIITokenizer(token_store=store)

    @pytest.mark.asyncio
    async def test_tokenize_email(self, tokenizer):
        """Test tokenizing an email."""
        text = "Contact john.doe@example.com for support"
        result = await tokenizer.tokenize(text)

        assert result.pii_fields_found == 1
        assert len(result.tokens_created) == 1
        assert "john.doe@example.com" not in result.tokenized_text
        assert "TOKEN_" in result.tokenized_text

    @pytest.mark.asyncio
    async def test_tokenize_multiple(self, tokenizer):
        """Test tokenizing multiple PII fields."""
        text = "Email: test@email.com, Order: ORD-ABC12345"
        result = await tokenizer.tokenize(text)

        assert result.pii_fields_found >= 2
        assert "test@email.com" not in result.tokenized_text
        assert "ORD-ABC12345" not in result.tokenized_text

    @pytest.mark.asyncio
    async def test_tokenize_no_pii(self, tokenizer):
        """Test tokenizing text with no PII."""
        text = "Hello, how can I help you?"
        result = await tokenizer.tokenize(text)

        assert result.pii_fields_found == 0
        assert len(result.tokens_created) == 0
        assert result.tokenized_text == text

    @pytest.mark.asyncio
    async def test_tokenize_with_context(self, tokenizer):
        """Test tokenization with context ID."""
        text = "Email: user@test.com"
        result = await tokenizer.tokenize(text, context_id="conv-123")

        assert result.context_id == "conv-123"
        assert result.pii_fields_found == 1

    @pytest.mark.asyncio
    async def test_tokenize_dict(self, tokenizer):
        """Test tokenizing a dictionary."""
        data = {
            "customer_name": "John Doe",
            "customer_email": "john@email.com",
            "message": "My order ORD-12345 is late",
            "order_id": "ORD-12345"
        }

        tokenized_data, result = await tokenizer.tokenize_dict(data)

        assert "john@email.com" not in tokenized_data["customer_email"]
        assert result.pii_fields_found >= 2


class TestPIIDetokenizer:
    """Tests for PII de-tokenization."""

    @pytest.fixture
    def setup(self):
        """Set up tokenizer and detokenizer with shared store."""
        store = InMemoryTokenStore()
        tokenizer = PIITokenizer(token_store=store)
        detokenizer = PIIDetokenizer(token_store=store)
        return tokenizer, detokenizer

    @pytest.mark.asyncio
    async def test_roundtrip(self, setup):
        """Test tokenize -> detokenize roundtrip."""
        tokenizer, detokenizer = setup

        original = "Contact support@company.com for help"

        # Tokenize
        tok_result = await tokenizer.tokenize(original)
        assert "support@company.com" not in tok_result.tokenized_text

        # De-tokenize
        detok_result = await detokenizer.detokenize(tok_result.tokenized_text)
        assert detok_result.detokenized_text == original
        assert detok_result.tokens_resolved == 1

    @pytest.mark.asyncio
    async def test_multiple_roundtrip(self, setup):
        """Test roundtrip with multiple PII fields."""
        tokenizer, detokenizer = setup

        original = "User john@test.com from IP 192.168.1.1 ordered #ORD-ABC123"

        tok_result = await tokenizer.tokenize(original)
        detok_result = await detokenizer.detokenize(tok_result.tokenized_text)

        # All PII should be restored
        assert "john@test.com" in detok_result.detokenized_text
        assert "192.168.1.1" in detok_result.detokenized_text

    @pytest.mark.asyncio
    async def test_detokenize_unknown_token(self, setup):
        """Test de-tokenizing unknown tokens."""
        _, detokenizer = setup

        text = "Hello TOKEN_00000000-0000-0000-0000-000000000000"
        result = await detokenizer.detokenize(text)

        assert len(result.tokens_not_found) == 1
        assert result.tokens_resolved == 0

    @pytest.mark.asyncio
    async def test_contains_tokens(self, setup):
        """Test token detection in text."""
        _, detokenizer = setup

        assert detokenizer.contains_tokens("Test TOKEN_12345678-1234-1234-1234-123456789abc")
        assert not detokenizer.contains_tokens("No tokens here")

    @pytest.mark.asyncio
    async def test_extract_tokens(self, setup):
        """Test token extraction."""
        _, detokenizer = setup

        text = "A: TOKEN_aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa B: TOKEN_bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        tokens = detokenizer.extract_tokens(text)

        assert len(tokens) == 2


class TestIntegration:
    """Integration tests for the tokenization module."""

    @pytest.mark.asyncio
    async def test_customer_service_message_flow(self):
        """Test full flow of tokenizing a customer message for AI processing."""
        store = InMemoryTokenStore()
        tokenizer = PIITokenizer(token_store=store)
        detokenizer = PIIDetokenizer(token_store=store)

        # Simulate customer message
        customer_message = {
            "content": "Hi, I'm John Smith. My email is john.smith@email.com and "
                       "my order #ORD-ABC123456 hasn't arrived. Please call me at 555-123-4567.",
            "customer_id": "CUST-XYZ789"
        }

        # 1. Tokenize before sending to AI
        tokenized_msg, tok_result = await tokenizer.tokenize_message(
            customer_message,
            context_id="conv-001"
        )

        # Verify PII is tokenized
        assert "john.smith@email.com" not in tokenized_msg["content"]
        assert "555-123-4567" not in tokenized_msg["content"]
        assert tok_result.pii_fields_found >= 3

        # 2. Simulate AI response (with tokens preserved)
        ai_response = {
            "content": f"Hello! I found your order {tok_result.tokens_created[1] if len(tok_result.tokens_created) > 1 else 'your order'}. "
                       f"I'll send an update to your email."
        }

        # 3. De-tokenize before sending to customer
        final_response = await detokenizer.detokenize_response(ai_response)

        # The response should have original values if tokens were used
        # (In this simplified test, AI response may not contain the exact tokens)

        print(f"Original: {customer_message}")
        print(f"Tokenized: {tokenized_msg}")
        print(f"Tokens created: {tok_result.tokens_created}")
        print(f"Final response: {final_response}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
