"""
Unit tests for Azure OpenAI Client.

Tests the Azure OpenAI integration:
- Configuration handling
- Client initialization
- Chat completions (intent, validation, escalation, response)
- Embedding generation
- Token usage tracking
- Singleton pattern

Target: 85%+ coverage for shared/azure_openai.py
"""

import json
import os
import pytest
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from shared.azure_openai import (
    TokenUsage,
    AzureOpenAIConfig,
    AzureOpenAIClient,
    get_openai_client,
    shutdown_openai_client,
)


# ============================================================================
# TokenUsage Tests
# ============================================================================


class TestTokenUsage:
    """Tests for TokenUsage dataclass."""

    def test_default_values(self):
        """Verify default TokenUsage values."""
        usage = TokenUsage()

        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0
        assert usage.estimated_cost == 0.0
        assert usage.model == ""
        assert isinstance(usage.timestamp, datetime)

    def test_custom_values(self):
        """Verify TokenUsage with custom values."""
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost=0.001,
            model="gpt-4o-mini",
        )

        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150
        assert usage.estimated_cost == 0.001
        assert usage.model == "gpt-4o-mini"


# ============================================================================
# AzureOpenAIConfig Tests
# ============================================================================


class TestAzureOpenAIConfig:
    """Tests for AzureOpenAIConfig dataclass."""

    def test_default_values(self):
        """Verify default config values."""
        config = AzureOpenAIConfig(endpoint="https://test.openai.azure.com/")

        assert config.endpoint == "https://test.openai.azure.com/"
        assert config.api_key is None
        assert config.api_version == "2024-02-15-preview"
        assert config.gpt4o_mini_deployment == "gpt-4o-mini"
        assert config.gpt4o_deployment == "gpt-4o"
        assert config.embedding_deployment == "text-embedding-3-large"

    def test_custom_values(self):
        """Verify config with custom values."""
        config = AzureOpenAIConfig(
            endpoint="https://custom.openai.azure.com/",
            api_key="test-key",
            api_version="2024-01-01",
            gpt4o_mini_deployment="custom-mini",
            gpt4o_deployment="custom-gpt4o",
            embedding_deployment="custom-embedding",
        )

        assert config.endpoint == "https://custom.openai.azure.com/"
        assert config.api_key == "test-key"
        assert config.api_version == "2024-01-01"
        assert config.gpt4o_mini_deployment == "custom-mini"

    def test_costs_per_million_defaults(self):
        """Verify default cost rates."""
        config = AzureOpenAIConfig(endpoint="https://test.openai.azure.com/")

        assert "gpt-4o-mini" in config.costs_per_million
        assert "gpt-4o" in config.costs_per_million
        assert "text-embedding-3-large" in config.costs_per_million

        assert config.costs_per_million["gpt-4o-mini"]["input"] == 0.15
        assert config.costs_per_million["gpt-4o-mini"]["output"] == 0.60
        assert config.costs_per_million["gpt-4o"]["input"] == 2.50
        assert config.costs_per_million["gpt-4o"]["output"] == 10.00

    def test_from_environment_success(self):
        """Verify config from environment variables."""
        with patch.dict(os.environ, {
            "AZURE_OPENAI_ENDPOINT": "https://env-test.openai.azure.com/",
            "AZURE_OPENAI_API_KEY": "env-api-key",
            "AZURE_OPENAI_API_VERSION": "2024-03-01",
            "AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT": "env-mini",
            "AZURE_OPENAI_GPT4O_DEPLOYMENT": "env-gpt4o",
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "env-embedding",
        }, clear=False):
            config = AzureOpenAIConfig.from_environment()

            assert config.endpoint == "https://env-test.openai.azure.com/"
            assert config.api_key == "env-api-key"
            assert config.api_version == "2024-03-01"
            assert config.gpt4o_mini_deployment == "env-mini"
            assert config.gpt4o_deployment == "env-gpt4o"
            assert config.embedding_deployment == "env-embedding"

    def test_from_environment_missing_endpoint(self):
        """Verify error when endpoint is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="AZURE_OPENAI_ENDPOINT"):
                AzureOpenAIConfig.from_environment()

    def test_from_environment_defaults(self):
        """Verify defaults when only endpoint is set."""
        with patch.dict(os.environ, {
            "AZURE_OPENAI_ENDPOINT": "https://minimal.openai.azure.com/",
        }, clear=True):
            config = AzureOpenAIConfig.from_environment()

            assert config.endpoint == "https://minimal.openai.azure.com/"
            assert config.api_key is None
            assert config.api_version == "2024-02-15-preview"
            assert config.gpt4o_mini_deployment == "gpt-4o-mini"


# ============================================================================
# AzureOpenAIClient Initialization Tests
# ============================================================================


class TestAzureOpenAIClientInit:
    """Tests for AzureOpenAIClient initialization."""

    def test_init_with_config(self):
        """Verify initialization with provided config."""
        config = AzureOpenAIConfig(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        )
        client = AzureOpenAIClient(config=config)

        assert client.config == config
        assert client._client is None
        assert client._token_usage == []
        assert client._initialized is False

    def test_init_without_config(self):
        """Verify initialization loads config from environment."""
        with patch.dict(os.environ, {
            "AZURE_OPENAI_ENDPOINT": "https://env.openai.azure.com/",
        }, clear=True):
            client = AzureOpenAIClient()

            assert client.config.endpoint == "https://env.openai.azure.com/"

    @pytest.mark.asyncio
    async def test_initialize_with_api_key(self):
        """Verify initialization with API key authentication."""
        config = AzureOpenAIConfig(
            endpoint="https://test.openai.azure.com/",
            api_key="test-api-key",
        )
        client = AzureOpenAIClient(config=config)

        # AsyncAzureOpenAI is imported inside initialize(), so we patch openai module
        mock_openai_class = MagicMock()
        mock_instance = MagicMock()
        mock_openai_class.return_value = mock_instance

        with patch.dict("sys.modules", {"openai": MagicMock(AsyncAzureOpenAI=mock_openai_class)}):
            result = await client.initialize()

            assert result is True
            assert client._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self):
        """Verify initialize returns True if already initialized."""
        config = AzureOpenAIConfig(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        )
        client = AzureOpenAIClient(config=config)
        client._initialized = True

        result = await client.initialize()

        assert result is True

    @pytest.mark.asyncio
    async def test_initialize_import_error(self):
        """Verify handling of missing OpenAI package."""
        config = AzureOpenAIConfig(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        )
        client = AzureOpenAIClient(config=config)

        with patch.dict("sys.modules", {"openai": None}):
            # Simulate ImportError by making the import fail
            with patch("builtins.__import__", side_effect=ImportError("No module named 'openai'")):
                result = await client.initialize()

                assert result is False
                assert client._initialized is False

    @pytest.mark.asyncio
    async def test_initialize_exception(self):
        """Verify handling of initialization exceptions."""
        config = AzureOpenAIConfig(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        )
        client = AzureOpenAIClient(config=config)

        mock_openai_class = MagicMock(side_effect=Exception("Connection failed"))
        with patch.dict("sys.modules", {"openai": MagicMock(AsyncAzureOpenAI=mock_openai_class)}):
            result = await client.initialize()

            assert result is False


# ============================================================================
# Token Usage Tracking Tests
# ============================================================================


class TestTokenUsageTracking:
    """Tests for token usage tracking."""

    def test_track_usage(self):
        """Verify token usage is tracked correctly."""
        config = AzureOpenAIConfig(endpoint="https://test.openai.azure.com/")
        client = AzureOpenAIClient(config=config)

        usage = client._track_usage(
            model="gpt-4o-mini",
            prompt_tokens=1000,
            completion_tokens=500,
        )

        assert usage.prompt_tokens == 1000
        assert usage.completion_tokens == 500
        assert usage.total_tokens == 1500
        assert usage.model == "gpt-4o-mini"
        # Cost: (1000/1M * 0.15) + (500/1M * 0.60) = 0.00015 + 0.0003 = 0.00045
        assert usage.estimated_cost == pytest.approx(0.00045, abs=0.0001)

    def test_track_usage_accumulates(self):
        """Verify multiple usages accumulate."""
        config = AzureOpenAIConfig(endpoint="https://test.openai.azure.com/")
        client = AzureOpenAIClient(config=config)

        client._track_usage("gpt-4o-mini", 1000, 500)
        client._track_usage("gpt-4o", 2000, 1000)

        assert len(client._token_usage) == 2

    def test_track_usage_unknown_model(self):
        """Verify unknown model defaults to zero cost."""
        config = AzureOpenAIConfig(endpoint="https://test.openai.azure.com/")
        client = AzureOpenAIClient(config=config)

        usage = client._track_usage("unknown-model", 1000, 500)

        assert usage.estimated_cost == 0.0

    def test_get_total_usage_empty(self):
        """Verify empty usage returns zeros."""
        config = AzureOpenAIConfig(endpoint="https://test.openai.azure.com/")
        client = AzureOpenAIClient(config=config)

        usage = client.get_total_usage()

        assert usage["total_requests"] == 0
        assert usage["total_tokens"] == 0
        assert usage["total_cost"] == 0.0
        assert usage["by_model"] == {}

    def test_get_total_usage_with_data(self):
        """Verify usage aggregation."""
        config = AzureOpenAIConfig(endpoint="https://test.openai.azure.com/")
        client = AzureOpenAIClient(config=config)

        client._track_usage("gpt-4o-mini", 1000, 500)
        client._track_usage("gpt-4o-mini", 2000, 1000)
        client._track_usage("gpt-4o", 3000, 1500)

        usage = client.get_total_usage()

        assert usage["total_requests"] == 3
        assert usage["total_tokens"] == 9000  # 1500 + 3000 + 4500
        assert "gpt-4o-mini" in usage["by_model"]
        assert "gpt-4o" in usage["by_model"]
        assert usage["by_model"]["gpt-4o-mini"]["requests"] == 2

    def test_reset_usage_tracking(self):
        """Verify usage reset clears data."""
        config = AzureOpenAIConfig(endpoint="https://test.openai.azure.com/")
        client = AzureOpenAIClient(config=config)

        client._track_usage("gpt-4o-mini", 1000, 500)
        assert len(client._token_usage) == 1

        client.reset_usage_tracking()

        assert len(client._token_usage) == 0


# ============================================================================
# Chat Completion Tests
# ============================================================================


class TestChatCompletion:
    """Tests for chat completion methods."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        config = AzureOpenAIConfig(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        )
        return AzureOpenAIClient(config=config)

    @pytest.fixture
    def mock_response(self):
        """Create a mock OpenAI response."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = '{"intent": "order_status", "confidence": 0.95}'
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        return response

    @pytest.mark.asyncio
    async def test_chat_completion_json_mode(self, client, mock_response):
        """Verify chat completion with JSON mode."""
        client._initialized = True
        client._client = MagicMock()
        client._client.chat = MagicMock()
        client._client.chat.completions = MagicMock()
        client._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await client._chat_completion(
            deployment="gpt-4o-mini",
            system_prompt="Classify intent",
            user_message="Where is my order?",
            json_mode=True,
        )

        assert result["intent"] == "order_status"
        assert result["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_chat_completion_text_mode(self, client):
        """Verify chat completion with text mode."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Your order is on its way!"
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 20

        client._initialized = True
        client._client = MagicMock()
        client._client.chat = MagicMock()
        client._client.chat.completions = MagicMock()
        client._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await client._chat_completion(
            deployment="gpt-4o",
            system_prompt="Generate response",
            user_message="Where is my order?",
            json_mode=False,
        )

        assert result["response"] == "Your order is on its way!"

    @pytest.mark.asyncio
    async def test_chat_completion_initializes_if_needed(self, client, mock_response):
        """Verify chat completion initializes client if needed."""
        client._initialized = False

        with patch.object(client, "initialize", new_callable=AsyncMock) as mock_init:
            mock_init.return_value = True
            client._client = MagicMock()
            client._client.chat = MagicMock()
            client._client.chat.completions = MagicMock()
            client._client.chat.completions.create = AsyncMock(return_value=mock_response)

            await client._chat_completion(
                deployment="gpt-4o-mini",
                system_prompt="Test",
                user_message="Test",
            )

            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_completion_raises_if_not_initialized(self, client):
        """Verify error when client not initialized."""
        client._initialized = True  # Set True but leave _client as None
        client._client = None

        with pytest.raises(RuntimeError, match="not initialized"):
            await client._chat_completion(
                deployment="gpt-4o-mini",
                system_prompt="Test",
                user_message="Test",
            )

    @pytest.mark.asyncio
    async def test_chat_completion_invalid_json(self, client):
        """Verify handling of invalid JSON response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Not valid JSON: {intent: order}"
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 20

        client._initialized = True
        client._client = MagicMock()
        client._client.chat = MagicMock()
        client._client.chat.completions = MagicMock()
        client._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await client._chat_completion(
            deployment="gpt-4o-mini",
            system_prompt="Test",
            user_message="Test",
            json_mode=True,
        )

        # Should fall back to _extract_json
        assert "error" in result or "intent" in result


# ============================================================================
# Intent Classification Tests
# ============================================================================


class TestIntentClassification:
    """Tests for classify_intent method."""

    @pytest.mark.asyncio
    async def test_classify_intent(self):
        """Verify intent classification."""
        config = AzureOpenAIConfig(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        )
        client = AzureOpenAIClient(config=config)

        with patch.object(client, "_chat_completion", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = {"intent": "return_request", "confidence": 0.92}

            result = await client.classify_intent(
                message="I want to return my order",
                system_prompt="Classify the intent",
            )

            assert result["intent"] == "return_request"
            assert result["confidence"] == 0.92
            mock_chat.assert_called_once()
            call_kwargs = mock_chat.call_args[1]
            assert call_kwargs["deployment"] == "gpt-4o-mini"
            assert call_kwargs["json_mode"] is True


# ============================================================================
# Content Validation Tests
# ============================================================================


class TestContentValidation:
    """Tests for validate_content method."""

    @pytest.mark.asyncio
    async def test_validate_content(self):
        """Verify content validation."""
        config = AzureOpenAIConfig(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        )
        client = AzureOpenAIClient(config=config)

        with patch.object(client, "_chat_completion", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = {
                "action": "allow",
                "reason": "Content is appropriate",
                "confidence": 0.99,
            }

            result = await client.validate_content(
                content="Normal customer message",
                validation_prompt="Validate content",
            )

            assert result["action"] == "allow"
            assert result["confidence"] == 0.99


# ============================================================================
# Escalation Detection Tests
# ============================================================================


class TestEscalationDetection:
    """Tests for detect_escalation method."""

    @pytest.mark.asyncio
    async def test_detect_escalation(self):
        """Verify escalation detection."""
        config = AzureOpenAIConfig(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        )
        client = AzureOpenAIClient(config=config)

        with patch.object(client, "_chat_completion", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = {
                "escalate": True,
                "confidence": 0.85,
                "reason": "Customer is frustrated",
            }

            result = await client.detect_escalation(
                conversation="Customer: This is the third time I've called!",
                system_prompt="Detect escalation",
            )

            assert result["escalate"] is True
            assert result["reason"] == "Customer is frustrated"


# ============================================================================
# Response Generation Tests
# ============================================================================


class TestResponseGeneration:
    """Tests for generate_response method."""

    @pytest.mark.asyncio
    async def test_generate_response(self):
        """Verify response generation."""
        config = AzureOpenAIConfig(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        )
        client = AzureOpenAIClient(config=config)

        with patch.object(client, "_chat_completion", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = {"response": "Your order will arrive tomorrow."}

            result = await client.generate_response(
                context="Customer asked about order status",
                system_prompt="Generate helpful response",
            )

            assert result == "Your order will arrive tomorrow."
            call_kwargs = mock_chat.call_args[1]
            assert call_kwargs["deployment"] == "gpt-4o"
            assert call_kwargs["json_mode"] is False


# ============================================================================
# Embedding Generation Tests
# ============================================================================


class TestEmbeddingGeneration:
    """Tests for generate_embeddings method."""

    @pytest.mark.asyncio
    async def test_generate_embeddings(self):
        """Verify embedding generation."""
        config = AzureOpenAIConfig(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        )
        client = AzureOpenAIClient(config=config)

        mock_embedding = [0.1, 0.2, 0.3] * 512  # 1536 dimensions
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        mock_response.usage.prompt_tokens = 50

        client._initialized = True
        client._client = MagicMock()
        client._client.embeddings = MagicMock()
        client._client.embeddings.create = AsyncMock(return_value=mock_response)

        result = await client.generate_embeddings(["Test text"])

        assert len(result) == 1
        assert len(result[0]) == 1536

    @pytest.mark.asyncio
    async def test_generate_embeddings_initializes_if_needed(self):
        """Verify embeddings initializes client if needed."""
        config = AzureOpenAIConfig(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        )
        client = AzureOpenAIClient(config=config)

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_response.usage.prompt_tokens = 10

        with patch.object(client, "initialize", new_callable=AsyncMock) as mock_init:
            mock_init.return_value = True
            client._client = MagicMock()
            client._client.embeddings = MagicMock()
            client._client.embeddings.create = AsyncMock(return_value=mock_response)

            await client.generate_embeddings(["Test"])

            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_embeddings_raises_if_not_initialized(self):
        """Verify error when client not initialized."""
        config = AzureOpenAIConfig(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        )
        client = AzureOpenAIClient(config=config)
        client._initialized = True
        client._client = None

        with pytest.raises(RuntimeError, match="not initialized"):
            await client.generate_embeddings(["Test"])


# ============================================================================
# JSON Extraction Tests
# ============================================================================


class TestJSONExtraction:
    """Tests for _extract_json method."""

    def test_extract_valid_json(self):
        """Verify extraction of valid JSON."""
        config = AzureOpenAIConfig(endpoint="https://test.openai.azure.com/")
        client = AzureOpenAIClient(config=config)

        result = client._extract_json('Some text {"key": "value"} more text')

        assert result == {"key": "value"}

    def test_extract_no_json(self):
        """Verify fallback for no JSON."""
        config = AzureOpenAIConfig(endpoint="https://test.openai.azure.com/")
        client = AzureOpenAIClient(config=config)

        result = client._extract_json("No JSON here at all")

        assert "error" in result
        assert "raw" in result

    def test_extract_invalid_json(self):
        """Verify fallback for malformed JSON."""
        config = AzureOpenAIConfig(endpoint="https://test.openai.azure.com/")
        client = AzureOpenAIClient(config=config)

        result = client._extract_json('{key: "no quotes on key"}')

        assert "error" in result


# ============================================================================
# Client Close Tests
# ============================================================================


class TestClientClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close_client(self):
        """Verify client is closed properly."""
        config = AzureOpenAIConfig(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        )
        client = AzureOpenAIClient(config=config)
        client._initialized = True

        mock_http_client = MagicMock()
        mock_http_client.close = AsyncMock()
        client._client = mock_http_client

        # Store reference before close nullifies it
        stored_mock = client._client

        await client.close()

        stored_mock.close.assert_called_once()
        assert client._client is None
        assert client._initialized is False

    @pytest.mark.asyncio
    async def test_close_no_client(self):
        """Verify close is safe when no client."""
        config = AzureOpenAIConfig(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        )
        client = AzureOpenAIClient(config=config)

        # Should not raise
        await client.close()


# ============================================================================
# Singleton Tests
# ============================================================================


class TestSingletonFunctions:
    """Tests for singleton functions."""

    def test_get_openai_client_creates_instance(self):
        """Verify get_openai_client creates instance."""
        import shared.azure_openai as module

        # Reset singleton
        module._client_instance = None

        with patch.dict(os.environ, {
            "AZURE_OPENAI_ENDPOINT": "https://singleton.openai.azure.com/",
        }, clear=True):
            client = get_openai_client()

            assert isinstance(client, AzureOpenAIClient)
            assert module._client_instance is client

    def test_get_openai_client_returns_same_instance(self):
        """Verify singleton returns same instance."""
        import shared.azure_openai as module

        # Reset singleton
        module._client_instance = None

        with patch.dict(os.environ, {
            "AZURE_OPENAI_ENDPOINT": "https://singleton.openai.azure.com/",
        }, clear=True):
            client1 = get_openai_client()
            client2 = get_openai_client()

            assert client1 is client2

    @pytest.mark.asyncio
    async def test_shutdown_openai_client(self):
        """Verify shutdown closes and clears singleton."""
        import shared.azure_openai as module

        # Setup a mock client
        mock_client = AzureOpenAIClient(
            AzureOpenAIConfig(endpoint="https://test.openai.azure.com/")
        )
        mock_client._client = MagicMock()
        mock_client._client.close = AsyncMock()
        mock_client._initialized = True
        module._client_instance = mock_client

        await shutdown_openai_client()

        assert module._client_instance is None

    @pytest.mark.asyncio
    async def test_shutdown_no_instance(self):
        """Verify shutdown is safe when no instance."""
        import shared.azure_openai as module

        module._client_instance = None

        # Should not raise
        await shutdown_openai_client()
