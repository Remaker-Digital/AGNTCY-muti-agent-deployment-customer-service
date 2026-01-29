# ============================================================================
# Model Router Unit Tests - Phase 6
# ============================================================================
# Purpose: Unit tests for model router abstraction layer
#
# Test Coverage:
# - Data models and enums
# - Mock provider functionality
# - Router initialization and configuration
# - Fallback logic
# - Cost tracking
#
# Run:
#     pytest tests/unit/test_model_router.py -v
# ============================================================================

import pytest
import pytest_asyncio
import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.model_router.models import (
    LLMProvider,
    ModelCapability,
    ProviderConfig,
    ModelConfig,
    LLMRequest,
    LLMResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ProviderStatus,
    FallbackStrategy,
)
from shared.model_router.providers.mock import MockProvider
from shared.model_router.router import ModelRouter
from shared.model_router.cost_tracker import ModelCostTracker, ProviderCostRecord


# ============================================================================
# Test Data Models
# ============================================================================


class TestLLMProvider:
    """Tests for LLMProvider enum."""

    def test_provider_values(self):
        """Test provider enum values."""
        assert LLMProvider.AZURE_OPENAI.value == "azure_openai"
        assert LLMProvider.ANTHROPIC.value == "anthropic"
        assert LLMProvider.LOCAL.value == "local"

    def test_all_providers_exist(self):
        """Test all expected providers exist."""
        providers = [p for p in LLMProvider]
        assert len(providers) == 3


class TestModelCapability:
    """Tests for ModelCapability enum."""

    def test_capability_values(self):
        """Test capability enum values."""
        assert ModelCapability.CHAT.value == "chat"
        assert ModelCapability.EMBEDDING.value == "embedding"
        assert ModelCapability.CLASSIFICATION.value == "classification"
        assert ModelCapability.CODE.value == "code"


class TestFallbackStrategy:
    """Tests for FallbackStrategy enum."""

    def test_strategy_values(self):
        """Test strategy enum values."""
        assert FallbackStrategy.SEQUENTIAL.value == "sequential"
        assert FallbackStrategy.ROUND_ROBIN.value == "round_robin"
        assert FallbackStrategy.FAILOVER_ONLY.value == "failover_only"
        assert FallbackStrategy.NONE.value == "none"


class TestProviderConfig:
    """Tests for ProviderConfig dataclass."""

    def test_default_config(self):
        """Test ProviderConfig default values."""
        config = ProviderConfig(
            provider=LLMProvider.AZURE_OPENAI,
            endpoint="https://test.openai.azure.com",
        )

        assert config.provider == LLMProvider.AZURE_OPENAI
        assert config.endpoint == "https://test.openai.azure.com"
        assert config.api_key is None
        assert config.priority == 1
        assert config.enabled is True
        assert config.timeout == 30.0
        assert config.max_retries == 3

    def test_config_with_all_values(self):
        """Test ProviderConfig with all values set."""
        config = ProviderConfig(
            provider=LLMProvider.ANTHROPIC,
            endpoint="https://api.anthropic.com",
            api_key="test-key",
            priority=2,
            enabled=False,
            timeout=60.0,
            max_retries=5,
            rate_limit_rpm=100,
        )

        assert config.provider == LLMProvider.ANTHROPIC
        assert config.api_key == "test-key"
        assert config.priority == 2
        assert config.enabled is False
        assert config.timeout == 60.0
        assert config.max_retries == 5
        assert config.rate_limit_rpm == 100


class TestModelConfig:
    """Tests for ModelConfig dataclass."""

    def test_default_model_config(self):
        """Test ModelConfig default values."""
        config = ModelConfig(
            name="gpt-4o-mini",
            provider=LLMProvider.AZURE_OPENAI,
            capability=ModelCapability.CHAT,
        )

        assert config.name == "gpt-4o-mini"
        assert config.max_tokens == 4096
        assert config.supports_json_mode is True

    def test_classification_default_temperature(self):
        """Test classification models have temperature 0."""
        config = ModelConfig(
            name="classifier",
            provider=LLMProvider.AZURE_OPENAI,
            capability=ModelCapability.CLASSIFICATION,
        )

        assert config.default_temperature == 0.0

    def test_chat_default_temperature(self):
        """Test chat models have temperature 0.7."""
        config = ModelConfig(
            name="chatbot",
            provider=LLMProvider.AZURE_OPENAI,
            capability=ModelCapability.CHAT,
        )

        assert config.default_temperature == 0.7


class TestLLMRequest:
    """Tests for LLMRequest dataclass."""

    def test_simple_request(self):
        """Test creating a simple LLM request."""
        request = LLMRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4o-mini",
        )

        assert len(request.messages) == 1
        assert request.model == "gpt-4o-mini"
        assert request.max_tokens == 500
        assert request.temperature == 0.0
        assert request.json_mode is False

    def test_request_with_json_mode(self):
        """Test request with JSON mode enabled."""
        request = LLMRequest(
            messages=[
                {"role": "system", "content": "Return JSON"},
                {"role": "user", "content": "Classify this"},
            ],
            model="gpt-4o-mini",
            json_mode=True,
            task_type="intent_classification",
        )

        assert request.json_mode is True
        assert request.task_type == "intent_classification"


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_response_creation(self):
        """Test creating an LLM response."""
        response = LLMResponse(
            content="Hello! How can I help?",
            model="gpt-4o-mini",
            provider=LLMProvider.AZURE_OPENAI,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            estimated_cost=0.00001,
        )

        assert response.content == "Hello! How can I help?"
        assert response.provider == LLMProvider.AZURE_OPENAI
        assert response.total_tokens == 15
        assert response.fallback_used is False


class TestProviderStatus:
    """Tests for ProviderStatus dataclass."""

    def test_status_to_dict(self):
        """Test status serialization."""
        status = ProviderStatus(
            provider=LLMProvider.AZURE_OPENAI,
            is_healthy=True,
            is_enabled=True,
            total_requests=100,
            success_rate=0.95,
        )

        data = status.to_dict()
        assert data["provider"] == "azure_openai"
        assert data["is_healthy"] is True
        assert data["total_requests"] == 100


# ============================================================================
# Test Mock Provider
# ============================================================================


class TestMockProvider:
    """Tests for MockProvider implementation."""

    @pytest.fixture
    def mock_config(self):
        """Create mock provider config."""
        return ProviderConfig(
            provider=LLMProvider.LOCAL,
            endpoint="mock://localhost",
            extra_config={
                "latency_ms": 10,
                "error_rate": 0.0,
            },
        )

    @pytest_asyncio.fixture
    async def mock_provider(self, mock_config):
        """Create initialized mock provider."""
        provider = MockProvider(mock_config)
        await provider.initialize()
        yield provider
        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_initialize(self, mock_config):
        """Test mock provider initialization."""
        provider = MockProvider(mock_config)
        result = await provider.initialize()

        assert result is True
        assert provider._initialized is True

    @pytest.mark.asyncio
    async def test_chat_completion_default(self, mock_provider):
        """Test default chat completion response."""
        request = LLMRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="mock-gpt-4o-mini",
        )

        response = await mock_provider.chat_completion(request)

        assert response.provider == LLMProvider.LOCAL
        assert response.content is not None
        assert response.total_tokens > 0

    @pytest.mark.asyncio
    async def test_chat_completion_intent_classification(self, mock_provider):
        """Test intent classification response."""
        request = LLMRequest(
            messages=[
                {"role": "system", "content": "Classify the intent"},
                {"role": "user", "content": "Where is my order?"},
            ],
            model="mock-gpt-4o-mini",
            json_mode=True,
            task_type="intent_classification",
        )

        response = await mock_provider.chat_completion(request)

        # Parse JSON response
        data = json.loads(response.content)
        assert "intent" in data
        assert "confidence" in data

    @pytest.mark.asyncio
    async def test_chat_completion_content_validation(self, mock_provider):
        """Test content validation response."""
        request = LLMRequest(
            messages=[
                {"role": "system", "content": "Validate this content"},
                {"role": "user", "content": "Test content"},
            ],
            model="mock-gpt-4o-mini",
            json_mode=True,
            task_type="content_validation",
        )

        response = await mock_provider.chat_completion(request)

        data = json.loads(response.content)
        assert "action" in data
        assert data["action"] in ["PASS", "BLOCK", "ESCALATE"]

    @pytest.mark.asyncio
    async def test_generate_embeddings(self, mock_provider):
        """Test embedding generation."""
        request = EmbeddingRequest(
            texts=["Hello world", "Test text"],
            model="mock-embedding",
        )

        response = await mock_provider.generate_embeddings(request)

        assert response.provider == LLMProvider.LOCAL
        assert len(response.embeddings) == 2
        assert response.dimensions == 1536

    @pytest.mark.asyncio
    async def test_deterministic_embeddings(self, mock_provider):
        """Test that embeddings are deterministic for same text."""
        request = EmbeddingRequest(texts=["Hello world"], model="mock-embedding")

        response1 = await mock_provider.generate_embeddings(request)
        response2 = await mock_provider.generate_embeddings(request)

        # Same text should produce same embedding
        assert response1.embeddings[0] == response2.embeddings[0]

    @pytest.mark.asyncio
    async def test_health_check(self, mock_provider):
        """Test health check."""
        is_healthy = await mock_provider.health_check()
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_get_available_models(self, mock_provider):
        """Test getting available models."""
        models = await mock_provider.get_available_models()

        assert len(models) >= 2
        model_names = [m.name for m in models]
        assert "mock-gpt-4o-mini" in model_names

    @pytest.mark.asyncio
    async def test_custom_response(self, mock_provider):
        """Test setting custom response."""
        custom_response = {"intent": "custom_intent", "confidence": 0.99}
        mock_provider.set_response("intent_classification", custom_response)

        request = LLMRequest(
            messages=[{"role": "user", "content": "test"}],
            model="mock-gpt-4o-mini",
            json_mode=True,
            task_type="intent_classification",
        )

        response = await mock_provider.chat_completion(request)
        data = json.loads(response.content)

        assert data["intent"] == "custom_intent"
        assert data["confidence"] == 0.99

    @pytest.mark.asyncio
    async def test_error_injection(self, mock_config):
        """Test error injection."""
        mock_config.extra_config["error_rate"] = 1.0  # Always fail
        provider = MockProvider(mock_config)
        await provider.initialize()

        request = LLMRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="mock-gpt-4o-mini",
        )

        with pytest.raises(RuntimeError, match="simulated error"):
            await provider.chat_completion(request)

    @pytest.mark.asyncio
    async def test_shutdown(self, mock_config):
        """Test provider shutdown."""
        provider = MockProvider(mock_config)
        await provider.initialize()
        await provider.shutdown()
        assert provider._initialized is False


# ============================================================================
# Test Model Router
# ============================================================================


class TestModelRouter:
    """Tests for ModelRouter."""

    @pytest.fixture
    def mock_config(self):
        """Create mock provider config."""
        return ProviderConfig(
            provider=LLMProvider.LOCAL,
            endpoint="mock://localhost",
            priority=1,
            extra_config={"latency_ms": 0},
        )

    @pytest_asyncio.fixture
    async def router_with_mock(self, mock_config):
        """Create router with mock provider."""
        router = ModelRouter(
            fallback_strategy=FallbackStrategy.SEQUENTIAL,
            max_fallback_attempts=3,
        )
        router.add_provider(mock_config)
        await router.initialize()
        yield router
        await router.shutdown()

    def test_router_creation(self):
        """Test router creation."""
        router = ModelRouter(
            fallback_strategy=FallbackStrategy.ROUND_ROBIN,
            max_fallback_attempts=5,
        )

        assert router.fallback_strategy == FallbackStrategy.ROUND_ROBIN
        assert router.max_fallback_attempts == 5

    def test_add_provider(self, mock_config):
        """Test adding provider config."""
        router = ModelRouter()
        router.add_provider(mock_config)

        assert LLMProvider.LOCAL in router._provider_configs

    def test_add_provider_after_init_fails(self, mock_config):
        """Test that adding provider after init raises error."""
        router = ModelRouter()
        router._initialized = True

        with pytest.raises(RuntimeError, match="Cannot add providers after initialization"):
            router.add_provider(mock_config)

    @pytest.mark.asyncio
    async def test_initialize(self, mock_config):
        """Test router initialization."""
        router = ModelRouter()
        router.add_provider(mock_config)
        result = await router.initialize()

        assert result is True
        assert router._initialized is True
        assert LLMProvider.LOCAL in router._providers

    @pytest.mark.asyncio
    async def test_chat_completion(self, router_with_mock):
        """Test chat completion through router."""
        request = LLMRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="mock-gpt-4o-mini",
        )

        response = await router_with_mock.chat_completion(request)

        assert response.provider == LLMProvider.LOCAL
        assert response.content is not None

    @pytest.mark.asyncio
    async def test_chat_completion_not_initialized(self):
        """Test chat completion fails when not initialized."""
        router = ModelRouter()

        request = LLMRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="mock-gpt-4o-mini",
        )

        with pytest.raises(RuntimeError, match="not initialized"):
            await router.chat_completion(request)

    @pytest.mark.asyncio
    async def test_generate_embeddings(self, router_with_mock):
        """Test embedding generation through router."""
        request = EmbeddingRequest(
            texts=["Hello world"],
            model="mock-embedding",
        )

        response = await router_with_mock.generate_embeddings(request)

        assert response.provider == LLMProvider.LOCAL
        assert len(response.embeddings) == 1

    @pytest.mark.asyncio
    async def test_get_available_models(self, router_with_mock):
        """Test getting available models from router."""
        models = await router_with_mock.get_available_models()

        assert len(models) >= 2

    @pytest.mark.asyncio
    async def test_get_available_models_by_capability(self, router_with_mock):
        """Test filtering models by capability."""
        embedding_models = await router_with_mock.get_available_models(
            capability=ModelCapability.EMBEDDING
        )

        for model in embedding_models:
            assert model.capability == ModelCapability.EMBEDDING

    @pytest.mark.asyncio
    async def test_health_check(self, router_with_mock):
        """Test health check for all providers."""
        status = await router_with_mock.health_check()

        assert "local" in status
        assert status["local"].is_healthy is True

    def test_get_provider_status(self, mock_config):
        """Test getting provider status."""
        router = ModelRouter()
        router.add_provider(mock_config)

        status = router.get_provider_status()

        assert "initialized" in status
        assert "fallback_strategy" in status
        assert "providers" in status

    @pytest.mark.asyncio
    async def test_cost_callback(self, router_with_mock):
        """Test cost tracking callback."""
        costs_recorded = []

        async def cost_callback(**kwargs):
            costs_recorded.append(kwargs)

        router_with_mock.set_cost_callback(cost_callback)

        request = LLMRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="mock-gpt-4o-mini",
            agent_name="test_agent",
        )

        await router_with_mock.chat_completion(request)

        assert len(costs_recorded) == 1
        assert costs_recorded[0]["agent_name"] == "test_agent"
        assert costs_recorded[0]["model"] == "mock-gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_shutdown(self, router_with_mock):
        """Test router shutdown."""
        await router_with_mock.shutdown()

        assert router_with_mock._initialized is False
        assert len(router_with_mock._providers) == 0


class TestModelRouterFallback:
    """Tests for router fallback behavior."""

    @pytest.mark.asyncio
    async def test_fallback_on_provider_failure(self):
        """Test fallback when primary provider fails."""
        # Create two providers: failing primary, working secondary
        primary_config = ProviderConfig(
            provider=LLMProvider.AZURE_OPENAI,
            endpoint="mock://primary",
            priority=1,
            extra_config={"error_rate": 1.0},  # Always fail
        )

        secondary_config = ProviderConfig(
            provider=LLMProvider.LOCAL,
            endpoint="mock://secondary",
            priority=2,
            extra_config={"error_rate": 0.0, "latency_ms": 0},
        )

        router = ModelRouter(fallback_strategy=FallbackStrategy.SEQUENTIAL)

        # Use mock providers for both
        mock_primary = MockProvider(primary_config)
        mock_secondary = MockProvider(secondary_config)

        await mock_primary.initialize()
        await mock_secondary.initialize()

        router._providers = {
            LLMProvider.AZURE_OPENAI: mock_primary,
            LLMProvider.LOCAL: mock_secondary,
        }
        router._initialized = True

        request = LLMRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="mock-gpt-4o-mini",
        )

        response = await router.chat_completion(request)

        # Should succeed via fallback
        assert response.provider == LLMProvider.LOCAL
        assert response.fallback_used is True


# ============================================================================
# Test Cost Tracker
# ============================================================================


class TestModelCostTracker:
    """Tests for ModelCostTracker."""

    @pytest.fixture
    def tracker(self):
        """Create a cost tracker."""
        return ModelCostTracker()

    @pytest.mark.asyncio
    async def test_record_usage(self, tracker):
        """Test recording usage."""
        await tracker.record_usage(
            agent_name="intent_classifier",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost=0.0001,
            provider=LLMProvider.AZURE_OPENAI,
        )

        summary = tracker.get_provider_summary(LLMProvider.AZURE_OPENAI)
        assert summary["total_requests"] == 1
        assert summary["total_tokens"] == 150
        assert summary["estimated_cost"] == 0.0001

    @pytest.mark.asyncio
    async def test_record_multiple_usage(self, tracker):
        """Test recording multiple usages."""
        for i in range(3):
            await tracker.record_usage(
                agent_name="test_agent",
                model="gpt-4o-mini",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost=0.001,
                provider=LLMProvider.AZURE_OPENAI,
            )

        summary = tracker.get_provider_summary(LLMProvider.AZURE_OPENAI)
        assert summary["total_requests"] == 3
        assert summary["estimated_cost"] == 0.003

    @pytest.mark.asyncio
    async def test_by_model_breakdown(self, tracker):
        """Test tracking by model."""
        await tracker.record_usage(
            agent_name="agent1",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost=0.001,
            provider=LLMProvider.AZURE_OPENAI,
        )

        await tracker.record_usage(
            agent_name="agent2",
            model="gpt-4o",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost=0.01,
            provider=LLMProvider.AZURE_OPENAI,
        )

        summary = tracker.get_provider_summary(LLMProvider.AZURE_OPENAI)
        assert "gpt-4o-mini" in summary["by_model"]
        assert "gpt-4o" in summary["by_model"]

    @pytest.mark.asyncio
    async def test_by_agent_breakdown(self, tracker):
        """Test tracking by agent."""
        await tracker.record_usage(
            agent_name="intent_classifier",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost=0.001,
            provider=LLMProvider.AZURE_OPENAI,
        )

        await tracker.record_usage(
            agent_name="response_generator",
            model="gpt-4o",
            prompt_tokens=200,
            completion_tokens=100,
            estimated_cost=0.01,
            provider=LLMProvider.AZURE_OPENAI,
        )

        summary = tracker.get_provider_summary(LLMProvider.AZURE_OPENAI)
        assert "intent_classifier" in summary["by_agent"]
        assert "response_generator" in summary["by_agent"]

    def test_record_failure(self, tracker):
        """Test recording failures."""
        tracker.record_failure(LLMProvider.AZURE_OPENAI)
        tracker.record_failure(LLMProvider.AZURE_OPENAI)

        summary = tracker.get_provider_summary(LLMProvider.AZURE_OPENAI)
        assert summary["failed_requests"] == 2

    @pytest.mark.asyncio
    async def test_cost_comparison(self, tracker):
        """Test cost comparison across providers."""
        await tracker.record_usage(
            agent_name="agent1",
            model="gpt-4o-mini",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost=0.01,
            provider=LLMProvider.AZURE_OPENAI,
        )

        await tracker.record_usage(
            agent_name="agent1",
            model="claude-3-haiku",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost=0.02,
            provider=LLMProvider.ANTHROPIC,
        )

        comparison = tracker.get_cost_comparison()

        assert comparison.total_cost == 0.03
        assert comparison.total_requests == 2
        # Azure should be cheapest (lower cost per token)
        assert comparison.cheapest_provider == "azure_openai"

    @pytest.mark.asyncio
    async def test_get_summary(self, tracker):
        """Test getting overall summary."""
        await tracker.record_usage(
            agent_name="test",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost=0.001,
            provider=LLMProvider.AZURE_OPENAI,
        )

        summary = tracker.get_summary()

        assert "period_start" in summary
        assert "total_cost" in summary
        assert "by_provider" in summary
        assert "recommendations" in summary

    def test_reset(self, tracker):
        """Test resetting tracker."""
        tracker._provider_costs[LLMProvider.AZURE_OPENAI].total_requests = 10

        tracker.reset()

        summary = tracker.get_provider_summary(LLMProvider.AZURE_OPENAI)
        assert summary["total_requests"] == 0


# ============================================================================
# Test Router Additional Coverage
# ============================================================================


class TestModelRouterAdditionalCoverage:
    """Additional tests for ModelRouter coverage."""

    @pytest.fixture
    def mock_config(self):
        """Create mock provider config."""
        return ProviderConfig(
            provider=LLMProvider.LOCAL,
            endpoint="mock://localhost",
            priority=1,
            extra_config={"latency_ms": 0, "error_rate": 0.0},
        )

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, mock_config):
        """Test initialize returns True when already initialized."""
        router = ModelRouter()
        router.add_provider(mock_config)
        await router.initialize()

        # Call again
        result = await router.initialize()

        assert result is True
        assert router._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_no_providers_uses_mock(self):
        """Test initialize with no providers defaults to mock."""
        router = ModelRouter()
        # Don't add any providers

        result = await router.initialize()

        assert result is True
        assert LLMProvider.LOCAL in router._providers

    @pytest.mark.asyncio
    async def test_initialize_skips_disabled_providers(self):
        """Test initialize skips disabled providers."""
        disabled_config = ProviderConfig(
            provider=LLMProvider.LOCAL,
            endpoint="mock://localhost",
            enabled=False,  # Disabled
        )

        router = ModelRouter()
        router.add_provider(disabled_config)
        result = await router.initialize()

        # Should fail because only provider is disabled
        assert result is False

    @pytest.mark.asyncio
    async def test_initialize_handles_provider_init_failure(self):
        """Test initialize handles provider init failure gracefully."""
        router = ModelRouter()

        # Create a config that will fail to create a provider
        bad_config = ProviderConfig(
            provider=LLMProvider.AZURE_OPENAI,
            endpoint="https://bad.openai.azure.com",
            priority=1,
        )
        router.add_provider(bad_config)

        # Mock the provider creation to return something that fails init
        mock_provider = MagicMock()
        mock_provider.initialize = AsyncMock(return_value=False)

        with patch.object(router, "_create_provider", return_value=mock_provider):
            result = await router.initialize()

        assert result is False

    def test_create_provider_azure_openai(self):
        """Test _create_provider for Azure OpenAI."""
        router = ModelRouter()
        config = ProviderConfig(
            provider=LLMProvider.AZURE_OPENAI,
            endpoint="https://test.openai.azure.com",
        )

        provider = router._create_provider(config)

        from shared.model_router.providers import AzureOpenAIProvider

        assert isinstance(provider, AzureOpenAIProvider)

    def test_create_provider_anthropic(self):
        """Test _create_provider for Anthropic."""
        router = ModelRouter()
        config = ProviderConfig(
            provider=LLMProvider.ANTHROPIC,
            endpoint="https://api.anthropic.com",
        )

        provider = router._create_provider(config)

        from shared.model_router.providers import AnthropicProvider

        assert isinstance(provider, AnthropicProvider)

    def test_create_provider_local_mock(self):
        """Test _create_provider for local/mock."""
        router = ModelRouter()
        config = ProviderConfig(
            provider=LLMProvider.LOCAL,
            endpoint="mock://localhost",
        )

        provider = router._create_provider(config)

        assert isinstance(provider, MockProvider)

    def test_create_provider_handles_exception(self):
        """Test _create_provider handles exceptions."""
        router = ModelRouter()
        config = ProviderConfig(
            provider=LLMProvider.LOCAL,
            endpoint="mock://localhost",
        )

        with patch.object(
            MockProvider, "__init__", side_effect=Exception("Creation failed")
        ):
            provider = router._create_provider(config)

        assert provider is None

    @pytest.mark.asyncio
    async def test_select_provider_round_robin(self, mock_config):
        """Test _select_provider with round robin strategy."""
        router = ModelRouter(fallback_strategy=FallbackStrategy.ROUND_ROBIN)
        router.add_provider(mock_config)
        await router.initialize()

        # Select multiple times
        provider1 = await router._select_provider()
        provider2 = await router._select_provider()

        # With single provider, should return same one
        assert provider1 == provider2

    @pytest.mark.asyncio
    async def test_select_provider_preferred_not_available(self, mock_config):
        """Test _select_provider when preferred provider not available."""
        router = ModelRouter()
        router.add_provider(mock_config)
        await router.initialize()

        # Make the mock provider unavailable
        router._providers[LLMProvider.LOCAL]._circuit_open = True

        # Request Azure (not configured), should try to get alternative
        with pytest.raises(RuntimeError, match="No LLM providers available"):
            await router._select_provider(preferred_provider=LLMProvider.AZURE_OPENAI)

    @pytest.mark.asyncio
    async def test_chat_completion_specific_provider_not_configured(self, mock_config):
        """Test chat_completion fails when requesting unconfigured provider."""
        router = ModelRouter()
        router.add_provider(mock_config)
        await router.initialize()

        request = LLMRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4o-mini",
        )

        with pytest.raises(RuntimeError, match="not configured"):
            await router.chat_completion(request, provider=LLMProvider.AZURE_OPENAI)

    @pytest.mark.asyncio
    async def test_chat_completion_failover_only_reraises_non_rate_limit(self):
        """Test FAILOVER_ONLY strategy re-raises non-rate-limit errors."""
        primary_config = ProviderConfig(
            provider=LLMProvider.LOCAL,
            endpoint="mock://primary",
            priority=1,
        )

        router = ModelRouter(fallback_strategy=FallbackStrategy.FAILOVER_ONLY)
        router.add_provider(primary_config)
        await router.initialize()

        # Make provider throw a non-rate-limit error
        router._providers[LLMProvider.LOCAL].chat_completion = AsyncMock(
            side_effect=RuntimeError("Some other error")
        )

        request = LLMRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4o-mini",
        )

        with pytest.raises(RuntimeError, match="Some other error"):
            await router.chat_completion(request)

    @pytest.mark.asyncio
    async def test_chat_completion_failover_only_fallback_on_rate_limit(self):
        """Test FAILOVER_ONLY strategy falls back on rate limit."""
        primary_config = ProviderConfig(
            provider=LLMProvider.LOCAL,
            endpoint="mock://primary",
            priority=1,
        )
        secondary_config = ProviderConfig(
            provider=LLMProvider.ANTHROPIC,
            endpoint="mock://secondary",
            priority=2,
        )

        router = ModelRouter(fallback_strategy=FallbackStrategy.FAILOVER_ONLY)

        # Create mock providers
        mock_primary = MockProvider(primary_config)
        mock_secondary = MockProvider(secondary_config)
        await mock_primary.initialize()
        await mock_secondary.initialize()

        router._providers = {
            LLMProvider.LOCAL: mock_primary,
            LLMProvider.ANTHROPIC: mock_secondary,
        }
        router._provider_configs = {
            LLMProvider.LOCAL: primary_config,
            LLMProvider.ANTHROPIC: secondary_config,
        }
        router._initialized = True

        # Make primary throw rate limit error
        mock_primary.chat_completion = AsyncMock(
            side_effect=RuntimeError("rate limit exceeded")
        )

        request = LLMRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="mock-gpt-4o-mini",
        )

        # Should fall back to secondary
        response = await router.chat_completion(request)
        assert response.provider == LLMProvider.LOCAL  # MockProvider returns LOCAL

    @pytest.mark.asyncio
    async def test_generate_embeddings_not_initialized(self):
        """Test embeddings fail when not initialized."""
        router = ModelRouter()

        request = EmbeddingRequest(
            texts=["Hello"],
            model="embedding-model",
        )

        with pytest.raises(RuntimeError, match="not initialized"):
            await router.generate_embeddings(request)

    @pytest.mark.asyncio
    async def test_generate_embeddings_specific_provider_not_configured(
        self, mock_config
    ):
        """Test embeddings fail for unconfigured provider."""
        router = ModelRouter()
        router.add_provider(mock_config)
        await router.initialize()

        request = EmbeddingRequest(
            texts=["Hello"],
            model="embedding-model",
        )

        with pytest.raises(RuntimeError, match="not configured"):
            await router.generate_embeddings(request, provider=LLMProvider.AZURE_OPENAI)

    @pytest.mark.asyncio
    async def test_generate_embeddings_handles_not_implemented(self, mock_config):
        """Test embeddings handles NotImplementedError from provider."""
        router = ModelRouter()
        router.add_provider(mock_config)
        await router.initialize()

        # Make generate_embeddings raise NotImplementedError
        router._providers[LLMProvider.LOCAL].generate_embeddings = AsyncMock(
            side_effect=NotImplementedError("Not supported")
        )

        request = EmbeddingRequest(
            texts=["Hello"],
            model="embedding-model",
        )

        # Should fail since we only have one provider that doesn't support it
        with pytest.raises(RuntimeError, match="Embedding generation failed"):
            await router.generate_embeddings(request)

    @pytest.mark.asyncio
    async def test_generate_embeddings_handles_exception(self, mock_config):
        """Test embeddings handles generic exceptions."""
        router = ModelRouter()
        router.add_provider(mock_config)
        await router.initialize()

        # Make generate_embeddings raise an exception
        router._providers[LLMProvider.LOCAL].generate_embeddings = AsyncMock(
            side_effect=RuntimeError("DB Error")
        )

        request = EmbeddingRequest(
            texts=["Hello"],
            model="embedding-model",
        )

        with pytest.raises(RuntimeError, match="Embedding generation failed.*DB Error"):
            await router.generate_embeddings(request)

    @pytest.mark.asyncio
    async def test_generate_embeddings_with_cost_callback(self, mock_config):
        """Test embeddings calls cost callback."""
        router = ModelRouter()
        router.add_provider(mock_config)
        await router.initialize()

        costs_recorded = []

        async def cost_callback(**kwargs):
            costs_recorded.append(kwargs)

        router.set_cost_callback(cost_callback)

        request = EmbeddingRequest(
            texts=["Hello"],
            model="mock-embedding",
            agent_name="test_agent",
        )

        await router.generate_embeddings(request)

        assert len(costs_recorded) == 1
        assert costs_recorded[0]["agent_name"] == "test_agent"

    @pytest.mark.asyncio
    async def test_get_available_models_handles_exception(self, mock_config):
        """Test get_available_models handles provider exceptions."""
        router = ModelRouter()
        router.add_provider(mock_config)
        await router.initialize()

        # Make get_available_models raise an exception
        router._providers[LLMProvider.LOCAL].get_available_models = AsyncMock(
            side_effect=RuntimeError("Error")
        )

        # Should not raise, just return empty
        models = await router.get_available_models()

        assert models == []

    @pytest.mark.asyncio
    async def test_shutdown_handles_provider_exception(self, mock_config):
        """Test shutdown handles provider shutdown exceptions."""
        router = ModelRouter()
        router.add_provider(mock_config)
        await router.initialize()

        # Make shutdown raise an exception
        router._providers[LLMProvider.LOCAL].shutdown = AsyncMock(
            side_effect=RuntimeError("Shutdown error")
        )

        # Should not raise
        await router.shutdown()

        assert router._initialized is False


# ============================================================================
# Test Global Router Functions
# ============================================================================


class TestGlobalRouterFunctions:
    """Tests for global router singleton functions."""

    @pytest.mark.asyncio
    async def test_init_model_router_returns_existing(self):
        """Test init returns existing initialized router."""
        import shared.model_router.router as router_module

        # Create existing router
        existing = ModelRouter()
        existing._initialized = True
        router_module._global_router = existing

        result = await router_module.init_model_router()

        assert result is existing

        # Cleanup
        router_module._global_router = None

    @pytest.mark.asyncio
    async def test_init_model_router_with_providers(self):
        """Test init with explicit provider list."""
        import shared.model_router.router as router_module

        router_module._global_router = None

        config = ProviderConfig(
            provider=LLMProvider.LOCAL,
            endpoint="mock://localhost",
        )

        router = await router_module.init_model_router(providers=[config])

        assert router._initialized is True
        assert LLMProvider.LOCAL in router._providers

        # Cleanup
        await router_module.shutdown_model_router()

    @pytest.mark.asyncio
    async def test_init_model_router_auto_configure(self):
        """Test init with auto-configuration from environment."""
        import shared.model_router.router as router_module

        router_module._global_router = None

        # No env vars set, should use mock
        with patch.dict("os.environ", {}, clear=True):
            router = await router_module.init_model_router()

        assert router._initialized is True
        assert LLMProvider.LOCAL in router._providers

        # Cleanup
        await router_module.shutdown_model_router()

    def test_get_model_router_raises_when_not_initialized(self):
        """Test get_model_router raises when not initialized."""
        import shared.model_router.router as router_module

        router_module._global_router = None

        with pytest.raises(RuntimeError, match="not initialized"):
            router_module.get_model_router()

    def test_get_model_router_returns_router(self):
        """Test get_model_router returns initialized router."""
        import shared.model_router.router as router_module

        existing = ModelRouter()
        router_module._global_router = existing

        result = router_module.get_model_router()

        assert result is existing

        # Cleanup
        router_module._global_router = None

    @pytest.mark.asyncio
    async def test_shutdown_model_router_clears_global(self):
        """Test shutdown clears global router."""
        import shared.model_router.router as router_module

        existing = ModelRouter()
        existing._initialized = True
        router_module._global_router = existing

        await router_module.shutdown_model_router()

        assert router_module._global_router is None


class TestAutoConfigureProviders:
    """Tests for _auto_configure_providers function."""

    def test_auto_configure_azure_openai(self):
        """Test auto-configuration for Azure OpenAI."""
        import shared.model_router.router as router_module

        router = ModelRouter()

        with patch.dict(
            "os.environ",
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_OPENAI_API_KEY": "test-key",
            },
            clear=True,
        ):
            router_module._auto_configure_providers(router)

        assert LLMProvider.AZURE_OPENAI in router._provider_configs
        assert (
            router._provider_configs[LLMProvider.AZURE_OPENAI].endpoint
            == "https://test.openai.azure.com"
        )

    def test_auto_configure_anthropic(self):
        """Test auto-configuration for Anthropic."""
        import shared.model_router.router as router_module

        router = ModelRouter()

        with patch.dict(
            "os.environ",
            {
                "ANTHROPIC_API_KEY": "test-key",
            },
            clear=True,
        ):
            router_module._auto_configure_providers(router)

        assert LLMProvider.ANTHROPIC in router._provider_configs

    def test_auto_configure_mock_explicit(self):
        """Test auto-configuration for mock when USE_MOCK_LLM is true."""
        import shared.model_router.router as router_module

        router = ModelRouter()

        with patch.dict(
            "os.environ",
            {
                "USE_MOCK_LLM": "true",
            },
            clear=True,
        ):
            router_module._auto_configure_providers(router)

        assert LLMProvider.LOCAL in router._provider_configs

    def test_auto_configure_mock_fallback(self):
        """Test auto-configuration for mock when no providers available."""
        import shared.model_router.router as router_module

        router = ModelRouter()

        with patch.dict("os.environ", {}, clear=True):
            router_module._auto_configure_providers(router)

        # Should add mock as fallback
        assert LLMProvider.LOCAL in router._provider_configs

    def test_auto_configure_all_providers(self):
        """Test auto-configuration with all environment variables."""
        import shared.model_router.router as router_module

        router = ModelRouter()

        with patch.dict(
            "os.environ",
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_OPENAI_API_KEY": "azure-key",
                "ANTHROPIC_API_KEY": "anthropic-key",
                "USE_MOCK_LLM": "true",
            },
            clear=True,
        ):
            router_module._auto_configure_providers(router)

        assert LLMProvider.AZURE_OPENAI in router._provider_configs
        assert LLMProvider.ANTHROPIC in router._provider_configs
        assert LLMProvider.LOCAL in router._provider_configs

        # Check priorities
        assert router._provider_configs[LLMProvider.AZURE_OPENAI].priority == 1
        assert router._provider_configs[LLMProvider.ANTHROPIC].priority == 2
        assert router._provider_configs[LLMProvider.LOCAL].priority == 99
