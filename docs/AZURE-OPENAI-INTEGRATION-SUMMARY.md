# Azure OpenAI Integration Summary

**Date:** 2026-01-26
**Phase:** 4 - Azure Production Setup
**Status:** Implementation Complete ✅

## Overview

This document summarizes the Azure OpenAI integration implemented across all agents in the AGNTCY Multi-Agent Customer Service Platform.

## Components Implemented

### 1. Shared Azure OpenAI Client (`shared/azure_openai.py`)

A unified client module for all agents to interact with Azure OpenAI services:

**Features:**
- Automatic authentication (API key or managed identity)
- Support for multiple models:
  - `gpt-4o-mini` - Intent classification, escalation detection, content validation
  - `gpt-4o` - Response generation
  - `text-embedding-3-large` - Knowledge retrieval (RAG)
- Token usage tracking per request
- Cost estimation based on Azure OpenAI pricing
- JSON response parsing with fallback extraction
- Singleton pattern for shared usage

**Key Methods:**
```python
await client.classify_intent(message, system_prompt, temperature)
await client.validate_content(content, validation_prompt, temperature)
await client.detect_escalation(conversation, system_prompt, temperature)
await client.generate_response(context, system_prompt, temperature, max_tokens)
await client.generate_embeddings(texts)
```

### 2. Cost Monitor (`shared/cost_monitor.py`)

Centralized cost tracking for Azure OpenAI usage:

**Features:**
- Per-agent token usage tracking
- Real-time cost estimation
- Budget alerts at 80% and 100% thresholds
- Aggregated reports by agent and model
- Export to JSON for analysis

**Usage:**
```python
from shared import get_cost_monitor, record_openai_usage

# Record usage
record_openai_usage("intent-classifier", "gpt-4o-mini", prompt_tokens=100, completion_tokens=50)

# Get summary
summary = get_cost_monitor().get_summary()
```

### 3. Agent Updates

All 5 agents updated to use Azure OpenAI with fallback to mock/template responses:

| Agent | Model | Use Case |
|-------|-------|----------|
| Intent Classification | gpt-4o-mini | Classify customer intent into 17 categories |
| Critic/Supervisor | gpt-4o-mini | Validate input (prompt injection) and output (PII) |
| Response Generation | gpt-4o | Generate natural customer responses |
| Escalation | gpt-4o-mini | Detect when to escalate to humans |
| Knowledge Retrieval | text-embedding-3-large | Semantic search over knowledge base |

**Key Pattern:**
- Each agent checks `USE_AZURE_OPENAI` environment variable
- Falls back to mock/template responses if OpenAI unavailable
- Logs token usage and costs on cleanup

### 4. Production Prompts

Five production-ready prompts from Phase 3.5 optimization integrated:

1. **Intent Classification** (98% accuracy) - 17 intents with decision rules
2. **Critic Input Validation** (0% FP, 100% TP) - Detects prompt injection, jailbreak, PII extraction
3. **Critic Output Validation** - Blocks profanity, PII leakage, system info
4. **Escalation Detection** (100% precision/recall) - Mandatory triggers + indicators
5. **Response Generation** (88.4% quality) - Brand voice with register matching

## Configuration

### Environment Variables

```bash
# Required
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/

# Authentication (choose one)
AZURE_OPENAI_API_KEY=your-api-key  # For API key auth
AZURE_CLIENT_ID=your-managed-identity-client-id  # For managed identity

# Optional
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_GPT4O_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
AZURE_OPENAI_MONTHLY_BUDGET=60.00
USE_AZURE_OPENAI=true  # Set to false to disable OpenAI
```

### Terraform Configuration

Azure OpenAI resources are configured in `terraform/phase4_prod/openai.tf`:

```hcl
resource "azurerm_cognitive_deployment" "gpt4o_mini" {
  name                 = "gpt-4o-mini"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = "gpt-4o-mini"
    version = "2024-07-18"
  }
  sku {
    name     = "GlobalStandard"
    capacity = 30  # 30K TPM
  }
}
```

## Cost Estimates

Based on Phase 3.5 evaluation and production patterns:

| Model | Est. Monthly Tokens | Est. Monthly Cost |
|-------|---------------------|-------------------|
| gpt-4o-mini | ~10M tokens | ~$6-9 |
| gpt-4o | ~2M tokens | ~$25-35 |
| text-embedding-3-large | ~5M tokens | ~$0.65 |
| **Total** | ~17M tokens | **~$32-45** |

*Actual costs depend on conversation volume. Budget alert set at $48/month.*

## Testing

### Unit Tests

```bash
# Run Azure OpenAI integration tests (requires credentials)
pytest tests/integration/test_azure_openai.py -v
```

### Manual Testing

```python
# Quick connectivity test
from shared import get_openai_client
import asyncio

async def test():
    client = get_openai_client()
    await client.initialize()
    result = await client.classify_intent(
        "Where is my order?",
        "Classify as ORDER_STATUS or OTHER. Output: {\"intent\": \"...\"}",
        temperature=0.0
    )
    print(result)
    await client.close()

asyncio.run(test())
```

## File Changes

### New Files
- `shared/azure_openai.py` - Azure OpenAI client module
- `shared/cost_monitor.py` - Cost monitoring module
- `tests/integration/test_azure_openai.py` - Integration tests

### Modified Files
- `shared/__init__.py` - Export new modules
- `agents/intent_classification/agent.py` - Azure OpenAI integration
- `agents/critic_supervisor/agent.py` - Azure OpenAI integration
- `agents/response_generation/agent.py` - Azure OpenAI integration
- `agents/escalation/agent.py` - Azure OpenAI integration
- `agents/knowledge_retrieval/agent.py` - Embeddings integration
- `requirements.txt` - Added openai, azure-identity packages

## Deployment Status

**Completed 2026-01-27:**
- ✅ All 6 agent images rebuilt with Azure OpenAI integration (`v1.1.0-openai` tag)
- ✅ Images pushed to ACR (`acragntcycsprodrc6vcp.azurecr.io`)
- ✅ Container groups redeployed with updated environment variables
- ✅ Azure OpenAI connectivity validated in production

**Container Deployment:**
| Agent | Image Tag | IP Address | Status |
|-------|-----------|------------|--------|
| Intent Classifier | v1.1.0-openai | 10.0.1.9 | ✅ Running |
| Critic/Supervisor | v1.1.0-openai | 10.0.1.8 | ✅ Running |
| Response Generator | v1.1.0-openai | 10.0.1.10 | ✅ Running |
| Escalation | v1.1.0-openai | 10.0.1.12 | ✅ Running |
| Knowledge Retrieval | v1.1.0-openai | 10.0.1.6 | ✅ Running |
| Analytics | v1.1.0-openai | 10.0.1.11 | ✅ Running |

**Validation Results:**
- Intent Classification: Successfully classifying intents via GPT-4o-mini
- Critic/Supervisor: Defense-in-depth working (Azure filter + GPT validation)
- Escalation: Detecting escalation triggers with 100% accuracy
- All agents logging token usage and costs

## Remaining Phase 4 Tasks

1. **Enable Application Insights** - Monitor token usage in production
2. **Load Testing** - Validate costs at 100 concurrent users
3. **Set Budget Alerts** - Configure Azure Cost Management alerts
4. **Real API Integrations** - Shopify, Zendesk, Mailchimp
5. **Multi-language Support** - French (fr-CA) and Spanish (es)

## Related Documentation

- `docs/PHASE-4-DEPLOYMENT-KNOWLEDGE-BASE.md` - Deployment guide
- `evaluation/prompts/` - Production prompt files
- `evaluation/results/PHASE-3.5-COMPLETION-SUMMARY.md` - Prompt optimization results
