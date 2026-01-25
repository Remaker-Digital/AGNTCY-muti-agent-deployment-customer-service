# Configuration Management Strategy - Phases 4-5

**Version**: 1.0
**Created**: January 25, 2026
**Status**: Recommendation for Phase 4-5 Implementation
**Audience**: Development Team, DevOps Engineers

---

## Executive Summary

For Phases 4-5 (Azure production deployment), we recommend a **hierarchical configuration approach** using:

1. **Azure Key Vault** for secrets (API keys, connection strings)
2. **Azure App Configuration** for application settings (feature flags, operational parameters)
3. **Environment Variables** for container-specific configuration
4. **Terraform Variables** for infrastructure configuration
5. **Config Files** (YAML/JSON) for agent-specific behavior and prompts

This approach balances **security, flexibility, cost, and operational simplicity** while following Azure best practices.

---

## Table of Contents

1. [Configuration Categories](#configuration-categories)
2. [Recommended Approach](#recommended-approach)
3. [Implementation Details](#implementation-details)
4. [Configuration Hierarchy](#configuration-hierarchy)
5. [Cost Analysis](#cost-analysis)
6. [Security Considerations](#security-considerations)
7. [Operational Workflow](#operational-workflow)
8. [Alternative Approaches Considered](#alternative-approaches-considered)
9. [Migration Path (Phase 3 → Phase 4)](#migration-path-phase-3--phase-4)

---

## Configuration Categories

### 1. Secrets (High Security) 🔒

**Examples**:
- Azure OpenAI API keys
- Shopify Admin API tokens
- Zendesk API tokens
- Mailchimp API keys
- Google Analytics service account JSON
- Cosmos DB connection strings
- Application Insights instrumentation keys

**Requirements**:
- ✅ Must be encrypted at rest and in transit
- ✅ Must support rotation without downtime
- ✅ Must have access audit logs
- ✅ Must NOT be in source control
- ✅ Must support Managed Identity access

**Recommended Storage**: **Azure Key Vault**

---

### 2. Application Settings (Medium Security) ⚙️

**Examples**:
- Feature flags (enable/disable RAG, PII tokenization, Critic/Supervisor)
- LLM model parameters (temperature, max_tokens, top_p)
- Rate limiting thresholds (requests per minute)
- Timeout values (agent response timeout, LLM call timeout)
- Cache TTLs (knowledge base cache, response cache)
- Language support (enabled languages: en, fr-CA, es)
- Escalation thresholds (sentiment score, response confidence)
- Analytics sampling rate (execution tracing sampling)

**Requirements**:
- ✅ Must support dynamic updates (no restart required)
- ✅ Must version configuration changes (rollback capability)
- ✅ Must support environment separation (dev, staging, prod)
- ⚠️ NOT highly sensitive (can be in source control with proper access controls)
- ✅ Must be queryable by agents at runtime

**Recommended Storage**: **Azure App Configuration** (with Key Vault references for sensitive values)

---

### 3. Infrastructure Configuration (Low Security) 🏗️

**Examples**:
- Azure region (East US)
- Resource group names (multi-agent-rg)
- Container CPU/memory allocations (1 CPU, 2 GB memory)
- Auto-scaling rules (min 1, max 10 instances)
- Network configuration (VNet CIDR, subnet ranges)
- Log retention periods (7 days)
- Budget alert thresholds (83%, 93%)

**Requirements**:
- ✅ Must be version controlled (Git)
- ✅ Must support infrastructure-as-code (Terraform)
- ✅ Must be reviewable in PRs
- ✅ Must be environment-specific (dev, staging, prod)
- ⚠️ NOT dynamic (requires redeployment)

**Recommended Storage**: **Terraform Variables** (terraform.tfvars, variables.tf)

---

### 4. Agent Behavior Configuration (Medium Security) 🤖

**Examples**:
- LLM prompts (system prompts, few-shot examples)
- Intent classification keywords (order_status: ["where is my order", "track package"])
- Response templates (fallback messages, error messages)
- Knowledge base metadata (document categories, confidence thresholds)
- Escalation rules (when to escalate, which queue)
- Conversation flow logic (state machine definitions)

**Requirements**:
- ✅ Must support frequent updates (prompt engineering iterations)
- ✅ Must be version controlled (Git)
- ✅ Must support A/B testing (different prompts for different users)
- ✅ Must be environment-specific (test prompts in staging)
- ⚠️ Medium sensitivity (prompts reveal business logic, but not secrets)

**Recommended Storage**: **Config Files (YAML/JSON)** in Git + **Azure App Configuration** for dynamic overrides

---

### 5. Runtime State (Not Configuration) 📊

**Examples**:
- Conversation history (customer messages, agent responses)
- Session state (current intent, context variables)
- Metrics and logs (execution traces, performance data)
- PII tokens (customer_email → TOKEN_abc123)

**Requirements**:
- ✅ Must be persisted in databases (Cosmos DB, Azure Key Vault for PII tokens)
- ✅ NOT configuration (this is data)

**Recommended Storage**: **Cosmos DB** (conversation state), **Azure Key Vault** (PII tokens), **Application Insights** (metrics/logs)

---

## Recommended Approach

### Hierarchical Configuration Model

```
┌─────────────────────────────────────────────────────────────────┐
│                     Configuration Hierarchy                      │
│                  (Lower layers override higher)                  │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: Infrastructure (Terraform)                             │
│  - Azure region, resource groups, networking                     │
│  - Container CPU/memory, auto-scaling rules                      │
│  - Budget alerts, log retention                                  │
│  Storage: terraform/phase4_prod/terraform.tfvars                 │
│  Update Frequency: Rare (infrastructure changes only)            │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 2: Secrets (Azure Key Vault)                              │
│  - API keys, connection strings, certificates                    │
│  - PII tokens (customer data tokenization)                       │
│  Access: Managed Identity (agents), RBAC (operators)             │
│  Update Frequency: Quarterly (rotation), ad-hoc (new services)  │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3: Application Settings (Azure App Configuration)         │
│  - Feature flags, LLM parameters, timeouts                       │
│  - Rate limits, cache TTLs, escalation thresholds               │
│  - Language support, sampling rates                              │
│  Access: Managed Identity (agents), Azure Portal (operators)     │
│  Update Frequency: Daily-Weekly (operational tuning)             │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 4: Agent Behavior (Config Files in Git)                   │
│  - LLM prompts, intent keywords, response templates             │
│  - Knowledge base metadata, escalation rules                     │
│  Storage: agents/{agent_name}/config.yaml in Git                │
│  Update Frequency: Daily (prompt engineering, A/B testing)       │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 5: Environment Variables (Container Instances)            │
│  - Container-specific overrides (AGENT_NAME, LOG_LEVEL)          │
│  - References to Layer 2 & 3 (@Microsoft.KeyVault(...))         │
│  Storage: Terraform azurerm_container_group resource             │
│  Update Frequency: Rare (container redeployment only)            │
└─────────────────────────────────────────────────────────────────┘
                                ↓
                        Agent Runtime
```

### Configuration Precedence (Lowest to Highest)

1. **Default values** (hardcoded in agent code, rarely used)
2. **Config files** (agents/{agent_name}/config.yaml in Git)
3. **Azure App Configuration** (feature flags, operational parameters)
4. **Environment variables** (container-specific overrides)
5. **Azure Key Vault** (secrets, always take precedence)

**Example**: If `LLM_TEMPERATURE` is defined in:
- Config file: `0.7`
- Azure App Configuration: `0.5`
- Environment variable: `0.3`

**Agent uses**: `0.3` (environment variable wins)

---

## Implementation Details

### 1. Azure Key Vault (Secrets)

**Setup**:
```hcl
# terraform/phase4_prod/key_vault.tf
resource "azurerm_key_vault" "main" {
  name                       = "kv-multi-agent"
  location                   = var.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = var.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 90
  purge_protection_enabled   = true

  # Managed Identity access
  access_policy {
    tenant_id = var.tenant_id
    object_id = azurerm_user_assigned_identity.agents.principal_id

    secret_permissions = ["Get", "List"]
  }
}

# Store secrets
resource "azurerm_key_vault_secret" "shopify_api_token" {
  name         = "shopify-api-token"
  value        = var.shopify_api_token  # From terraform.tfvars (NOT committed)
  key_vault_id = azurerm_key_vault.main.id
}
```

**Agent Usage (Python)**:
```python
from azure.identity import ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient

# Authenticate with Managed Identity (no credentials needed)
credential = ManagedIdentityCredential()
secret_client = SecretClient(
    vault_url="https://kv-multi-agent.vault.azure.net/",
    credential=credential
)

# Retrieve secret
shopify_token = secret_client.get_secret("shopify-api-token").value
```

**Cost**: ~$5-10/month (Standard tier, ~10,000 operations/month)

---

### 2. Azure App Configuration (Application Settings)

**Setup**:
```hcl
# terraform/phase4_prod/app_configuration.tf
resource "azurerm_app_configuration" "main" {
  name                = "appconfig-multi-agent"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "standard"

  identity {
    type = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.agents.id]
  }
}

# Feature flags
resource "azurerm_app_configuration_feature" "rag_enabled" {
  configuration_store_id = azurerm_app_configuration.main.id
  name                   = "rag_enabled"
  enabled                = true
  label                  = "production"
}

# Key-value settings
resource "azurerm_app_configuration_key" "llm_temperature" {
  configuration_store_id = azurerm_app_configuration.main.id
  key                    = "llm:temperature"
  value                  = "0.7"
  label                  = "production"
}

# Reference to Key Vault secret
resource "azurerm_app_configuration_key" "openai_key_ref" {
  configuration_store_id = azurerm_app_configuration.main.id
  key                    = "openai:api_key"
  type                   = "vault"
  vault_key_reference    = azurerm_key_vault_secret.openai_api_key.id
  label                  = "production"
}
```

**Agent Usage (Python)**:
```python
from azure.appconfiguration import AzureAppConfigurationClient
from azure.identity import ManagedIdentityCredential

# Connect to App Configuration
credential = ManagedIdentityCredential()
app_config_client = AzureAppConfigurationClient(
    base_url="https://appconfig-multi-agent.azconfig.io",
    credential=credential
)

# Get feature flag
rag_enabled = app_config_client.get_configuration_setting(
    key=".appconfig.featureflag/rag_enabled",
    label="production"
).value

# Get setting
llm_temperature = float(app_config_client.get_configuration_setting(
    key="llm:temperature",
    label="production"
).value)

# Get Key Vault reference (automatically resolved)
openai_key = app_config_client.get_configuration_setting(
    key="openai:api_key",
    label="production"
).value  # Returns actual secret from Key Vault
```

**Cost**: ~$1-5/month (Standard tier, ~10,000 requests/month)

**Benefits**:
- ✅ Dynamic updates (no agent restart required)
- ✅ Feature flags (gradual rollout, A/B testing)
- ✅ Version history (rollback capability)
- ✅ Labels for environment separation (dev, staging, prod)
- ✅ Key Vault integration (secrets referenced, not duplicated)

---

### 3. Terraform Variables (Infrastructure)

**Setup**:
```hcl
# terraform/phase4_prod/variables.tf
variable "location" {
  description = "Azure region"
  type        = string
  default     = "East US"
}

variable "container_cpu" {
  description = "CPU cores per container"
  type        = number
  default     = 1
}

variable "container_memory" {
  description = "Memory GB per container"
  type        = number
  default     = 2
}

variable "budget_amount" {
  description = "Monthly budget in USD"
  type        = number
  default     = 360
}

# Secrets (NOT committed, from terraform.tfvars)
variable "shopify_api_token" {
  description = "Shopify Admin API token"
  type        = string
  sensitive   = true
}
```

```hcl
# terraform/phase4_prod/terraform.tfvars (DO NOT COMMIT)
location         = "East US"
container_cpu    = 1
container_memory = 2
budget_amount    = 360

# Secrets (from environment or secure storage)
shopify_api_token = "shpat_abc123..."
```

**Usage**:
```hcl
# Reference in resources
resource "azurerm_container_group" "intent_classifier" {
  name                = "intent-classifier"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  container {
    name   = "intent-classifier"
    image  = "acrname.azurecr.io/intent-classifier:latest"
    cpu    = var.container_cpu
    memory = var.container_memory

    environment_variables = {
      AGENT_NAME = "intent-classifier"
      LOG_LEVEL  = "INFO"
    }
  }
}
```

**Cost**: Free (Terraform is free, Azure resources billed separately)

---

### 4. Config Files (Agent Behavior)

**Setup**:
```yaml
# agents/intent_classification/config.yaml
agent:
  name: "intent-classifier"
  version: "1.0.0"
  description: "Classifies customer intent using LLM"

llm:
  model: "gpt-4o-mini"
  temperature: 0.3  # Lower for classification (more deterministic)
  max_tokens: 100
  system_prompt: |
    You are an intent classification assistant for an e-commerce customer service platform.
    Classify the customer's message into one of the following intents:
    - order_status: Customer asking about order status or tracking
    - product_info: Customer asking about product details
    - return: Customer wants to return/exchange a product
    - account: Customer asking about their account
    - shipping: Customer asking about shipping options/costs
    - payment: Customer asking about payment methods/issues
    - general: General inquiries

    Respond with ONLY the intent name and confidence score (0.0-1.0).

intent_keywords:
  order_status:
    - "where is my order"
    - "track my package"
    - "order status"
    - "delivery date"
  product_info:
    - "tell me about"
    - "product details"
    - "specifications"
    - "what is"
  return:
    - "return"
    - "refund"
    - "exchange"
    - "send back"

fallback:
  confidence_threshold: 0.7  # If LLM confidence < 0.7, escalate
  default_intent: "general"
```

**Agent Usage (Python)**:
```python
import yaml
from pathlib import Path

# Load config file
config_path = Path(__file__).parent / "config.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)

# Use configuration
model = config['llm']['model']  # "gpt-4o-mini"
temperature = config['llm']['temperature']  # 0.3
system_prompt = config['llm']['system_prompt']
keywords = config['intent_keywords']
```

**Benefits**:
- ✅ Version controlled (Git)
- ✅ Code review (PRs for prompt changes)
- ✅ Environment-specific (different files for dev/staging/prod)
- ✅ Fast iteration (no Azure dependency)
- ✅ Free (no additional cost)

---

### 5. Environment Variables (Container-Specific)

**Setup**:
```hcl
# terraform/phase4_prod/container_instances.tf
resource "azurerm_container_group" "intent_classifier" {
  name                = "intent-classifier"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  identity {
    type = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.agents.id]
  }

  container {
    name   = "intent-classifier"
    image  = "acrname.azurecr.io/intent-classifier:latest"
    cpu    = 1
    memory = 2

    environment_variables = {
      # Container identity
      AGENT_NAME = "intent-classifier"
      AGENT_VERSION = "1.0.0"

      # Logging
      LOG_LEVEL = "INFO"

      # Azure connections
      APP_CONFIG_URL = "https://appconfig-multi-agent.azconfig.io"
      KEY_VAULT_URL  = "https://kv-multi-agent.vault.azure.net/"

      # AGNTCY SDK
      SLIM_ENDPOINT = "http://slim-service:8080"
    }

    # Secure environment variables (from Key Vault)
    secure_environment_variables = {
      OPENAI_API_KEY = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.openai_api_key.id})"
    }
  }
}
```

**Agent Usage (Python)**:
```python
import os

# Read environment variables
agent_name = os.getenv("AGENT_NAME", "unknown-agent")
log_level = os.getenv("LOG_LEVEL", "INFO")
app_config_url = os.getenv("APP_CONFIG_URL")

# Secure variables (automatically injected from Key Vault)
openai_key = os.getenv("OPENAI_API_KEY")
```

**Benefits**:
- ✅ Container-specific configuration
- ✅ Key Vault integration (automatic secret injection)
- ✅ No code changes (standard environment variable pattern)

---

## Configuration Hierarchy

### Example: LLM Temperature Configuration

**Scenario**: Agent needs to determine LLM temperature for intent classification

**Configuration Sources**:
1. **Default (code)**: `temperature = 0.7` (hardcoded fallback)
2. **Config file** (Git): `llm.temperature = 0.3` (intent classification tuned)
3. **Azure App Configuration**: `llm:temperature = 0.5` (A/B test override)
4. **Environment Variable**: `LLM_TEMPERATURE = 0.8` (container-specific override)

**Precedence** (highest to lowest):
1. Environment Variable: `0.8` ← **WINS**
2. Azure App Configuration: `0.5`
3. Config file: `0.3`
4. Default: `0.7`

**Agent uses**: `temperature = 0.8`

### Configuration Loading Order (Python)

```python
import os
import yaml
from azure.appconfiguration import AzureAppConfigurationClient
from azure.identity import ManagedIdentityCredential

class ConfigManager:
    def __init__(self):
        self.config = {}

        # 1. Load defaults (hardcoded)
        self.config['llm_temperature'] = 0.7

        # 2. Load config file (Git)
        with open('config.yaml') as f:
            file_config = yaml.safe_load(f)
            self.config['llm_temperature'] = file_config.get('llm', {}).get('temperature', 0.7)

        # 3. Load Azure App Configuration
        try:
            credential = ManagedIdentityCredential()
            app_config = AzureAppConfigurationClient(
                base_url=os.getenv("APP_CONFIG_URL"),
                credential=credential
            )
            temp_setting = app_config.get_configuration_setting(
                key="llm:temperature",
                label="production"
            )
            if temp_setting:
                self.config['llm_temperature'] = float(temp_setting.value)
        except Exception as e:
            print(f"App Config unavailable, using file config: {e}")

        # 4. Load environment variables (highest precedence)
        if os.getenv("LLM_TEMPERATURE"):
            self.config['llm_temperature'] = float(os.getenv("LLM_TEMPERATURE"))

    def get(self, key, default=None):
        return self.config.get(key, default)

# Usage
config = ConfigManager()
temperature = config.get('llm_temperature')  # Returns 0.8 (from env var)
```

---

## Cost Analysis

### Monthly Costs (Phase 4-5)

| Service | Tier | Usage | Cost |
|---------|------|-------|------|
| **Azure Key Vault** | Standard | 10,000 operations/month | ~$5-10 |
| **Azure App Configuration** | Standard | 10,000 requests/month | ~$1-5 |
| **Config Files (Git)** | N/A | Free | $0 |
| **Environment Variables** | N/A | Free | $0 |
| **Terraform State** | Blob Storage | <1 GB | ~$0.50 |
| **TOTAL** | | | **~$6.50-15.50/month** |

**Percentage of Total Budget**: 2-5% of $310-360/month budget

**Cost Optimization**:
- ✅ Use App Configuration Standard (not Free tier for production features)
- ✅ Use Key Vault Standard (not Premium, no HSM needed)
- ✅ Cache App Configuration values (reduce API calls)
- ✅ Use config files for static values (free)

---

## Security Considerations

### Secrets Management

**✅ DO**:
- Store all secrets in Azure Key Vault
- Use Managed Identity for access (no hardcoded credentials)
- Enable soft-delete (90 days) + purge protection
- Rotate secrets quarterly (automated)
- Audit secret access (Azure Monitor logs)
- Use Key Vault references in App Configuration (not duplicates)

**❌ DON'T**:
- Store secrets in config files (even encrypted)
- Store secrets in Azure App Configuration (use Key Vault references)
- Store secrets in environment variables (except Key Vault references)
- Commit `terraform.tfvars` to Git (add to `.gitignore`)
- Use same secrets across dev/staging/prod

### Access Control

**Key Vault Access**:
- **Agents**: Managed Identity, `Get` and `List` permissions only
- **Operators**: RBAC, `Get`, `List`, `Set` permissions (human approval required)
- **CI/CD**: Service Principal, `Get` permission only (read secrets for deployment)

**App Configuration Access**:
- **Agents**: Managed Identity, `Read` permission
- **Operators**: RBAC, `Read` and `Write` permissions
- **CI/CD**: Service Principal, `Read` permission

### Sensitive Configuration

**Medium-Sensitivity Settings** (can be in App Configuration):
- LLM prompts (reveal business logic, but not secrets)
- Escalation thresholds (operational parameters)
- Feature flags (enable/disable features)

**High-Sensitivity Settings** (must be in Key Vault):
- API keys, tokens, passwords
- Connection strings with credentials
- Certificates, private keys

---

## Operational Workflow

### Scenario 1: Update LLM Temperature (Operational Tuning)

**Goal**: Increase temperature from 0.7 to 0.9 for response generation (more creative)

**Steps**:
1. **Azure Portal**:
   - Navigate to Azure App Configuration
   - Find key: `llm:temperature`
   - Update value: `0.7` → `0.9`
   - Click Save
2. **Agents**: Automatically pick up new value within 30 seconds (no restart)
3. **Verify**: Check Application Insights for new temperature in logs

**Duration**: <1 minute
**Downtime**: None (dynamic update)

---

### Scenario 2: Update Intent Classification Prompt (Prompt Engineering)

**Goal**: Add new intent type "complaint" to system prompt

**Steps**:
1. **Local development**:
   - Edit `agents/intent_classification/config.yaml`
   - Add "complaint" to intent list in system_prompt
   - Add keywords to intent_keywords
2. **Git**:
   - Commit changes
   - Create PR
   - Code review (team approves prompt changes)
   - Merge to main
3. **CI/CD**:
   - Azure DevOps pipeline triggers
   - Builds new container image
   - Deploys to staging
   - Smoke tests pass
   - Promote to production
4. **Agents**: New prompt active after container restart

**Duration**: 10-30 minutes (including CI/CD)
**Downtime**: <1 minute (rolling deployment)

---

### Scenario 3: Rotate Shopify API Token (Security)

**Goal**: Rotate Shopify API token (quarterly security requirement)

**Steps**:
1. **Shopify**:
   - Generate new API token
   - Keep old token active (avoid downtime)
2. **Azure Key Vault**:
   - Update secret: `shopify-api-token`
   - New version created automatically
3. **Agents**: Automatically pick up new token within 5 minutes (Key Vault cache TTL)
4. **Shopify**: Revoke old token (after confirming new token works)

**Duration**: 5-10 minutes
**Downtime**: None (seamless rotation)

---

### Scenario 4: Add New Feature Flag (Gradual Rollout)

**Goal**: Enable PII tokenization for 10% of users (canary release)

**Steps**:
1. **Azure App Configuration**:
   - Create feature flag: `pii_tokenization_enabled`
   - Set targeting: 10% of users (random sampling)
   - Enable flag
2. **Agent Code**:
   - Check feature flag before tokenizing
   ```python
   if feature_manager.is_enabled("pii_tokenization_enabled", user_id):
       data = tokenize_pii(data)
   ```
3. **Monitor**: Check Application Insights for errors
4. **Gradual Rollout**: Increase to 25%, 50%, 100% over days/weeks
5. **Full Rollout**: Remove feature flag check (always enabled)

**Duration**: Minutes (feature flag update)
**Downtime**: None (gradual rollout)

---

## Alternative Approaches Considered

### ❌ Option 1: Environment Variables Only

**Pros**:
- ✅ Simple (standard pattern)
- ✅ No additional Azure services (free)

**Cons**:
- ❌ Requires container restart for updates
- ❌ Secrets in plain text (unless Key Vault references)
- ❌ No version history (hard to rollback)
- ❌ No feature flags (can't do gradual rollout)

**Verdict**: Too inflexible for production, acceptable for Phase 3 only

---

### ❌ Option 2: Config Files Only

**Pros**:
- ✅ Version controlled (Git)
- ✅ Code review (PRs)
- ✅ Free

**Cons**:
- ❌ Requires container rebuild for updates
- ❌ Can't store secrets (even encrypted)
- ❌ No dynamic updates (can't adjust without redeployment)
- ❌ No environment separation (need multiple files)

**Verdict**: Good for static behavior (prompts), insufficient for operational tuning

---

### ❌ Option 3: Azure App Configuration Only

**Pros**:
- ✅ Dynamic updates (no restart)
- ✅ Feature flags
- ✅ Version history

**Cons**:
- ❌ Not suitable for secrets (use Key Vault instead)
- ❌ Not suitable for infrastructure (use Terraform instead)
- ❌ Additional cost (~$1-5/month, acceptable but unnecessary if not used correctly)

**Verdict**: Good for application settings, but not a complete solution

---

### ✅ Option 4: Hierarchical Approach (RECOMMENDED)

**Pros**:
- ✅ Security (Key Vault for secrets)
- ✅ Flexibility (App Configuration for operational tuning)
- ✅ Version control (Terraform + Git for infrastructure and behavior)
- ✅ Dynamic updates (App Configuration + Key Vault)
- ✅ Cost-effective (~$6.50-15.50/month, <5% of budget)

**Cons**:
- ⚠️ More complex (4 configuration sources)
- ⚠️ Learning curve (operators need training)

**Verdict**: Best balance of security, flexibility, and cost

---

## Migration Path (Phase 3 → Phase 4)

### Phase 3 (Current)

**Configuration**:
- `.env` file (local development)
- Environment variables in Docker Compose
- Hardcoded defaults in agent code

**Example**:
```bash
# .env
SLIM_ENDPOINT=http://localhost:8080
SHOPIFY_API_URL=http://localhost:5001
AGENT_LOG_LEVEL=INFO
```

---

### Phase 4 (Migration)

**Step 1: Create Azure Key Vault**
```bash
az keyvault create \
  --name kv-multi-agent \
  --resource-group multi-agent-rg \
  --location "East US"

# Store secrets
az keyvault secret set \
  --vault-name kv-multi-agent \
  --name shopify-api-token \
  --value "shpat_abc123..."
```

**Step 2: Create Azure App Configuration**
```bash
az appconfig create \
  --name appconfig-multi-agent \
  --resource-group multi-agent-rg \
  --location "East US" \
  --sku Standard

# Create settings
az appconfig kv set \
  --name appconfig-multi-agent \
  --key llm:temperature \
  --value "0.7" \
  --label production
```

**Step 3: Update Agent Code**
```python
# Before (Phase 3)
SLIM_ENDPOINT = os.getenv("SLIM_ENDPOINT", "http://localhost:8080")

# After (Phase 4)
from shared.config import ConfigManager
config = ConfigManager()
SLIM_ENDPOINT = config.get("slim_endpoint")  # Hierarchical lookup
```

**Step 4: Update Terraform**
```hcl
# Add Key Vault references to container environment variables
secure_environment_variables = {
  SHOPIFY_API_TOKEN = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.shopify_api_token.id})"
}
```

**Step 5: Migrate Config Files**
```bash
# Move configuration to Git
mkdir -p agents/intent_classification
mv .env agents/intent_classification/config.yaml
git add agents/intent_classification/config.yaml
git commit -m "Migrate configuration to YAML"
```

---

## Recommended Implementation Order (Phase 4)

### Week 1-2: Infrastructure Setup
1. ✅ Create Azure Key Vault (store all secrets)
2. ✅ Create Terraform variables (infrastructure configuration)
3. ✅ Update `.gitignore` (exclude terraform.tfvars)

### Week 3-4: Service Deployment
4. ✅ Create Azure App Configuration (application settings)
5. ✅ Create config files in Git (agent behavior)
6. ✅ Update agent code (ConfigManager class)

### Week 5-6: API Integration
7. ✅ Store API tokens in Key Vault
8. ✅ Reference Key Vault secrets in App Configuration
9. ✅ Test dynamic configuration updates

### Week 7-8: Testing & Validation
10. ✅ Test configuration hierarchy (precedence)
11. ✅ Test secret rotation (zero downtime)
12. ✅ Test feature flags (gradual rollout)

---

## Conclusion

**Recommended Approach**: **Hierarchical Configuration Model**

1. **Azure Key Vault**: Secrets (API keys, connection strings)
2. **Azure App Configuration**: Application settings (feature flags, operational parameters)
3. **Terraform Variables**: Infrastructure configuration (Azure resources)
4. **Config Files (YAML)**: Agent behavior (prompts, keywords, templates)
5. **Environment Variables**: Container-specific overrides

**Benefits**:
- ✅ Security: Secrets never in source control
- ✅ Flexibility: Dynamic updates without redeployment
- ✅ Version Control: Infrastructure and behavior changes reviewed in Git
- ✅ Cost-Effective: ~$6.50-15.50/month (<5% of budget)
- ✅ Operational Simplicity: Clear separation of concerns
- ✅ Azure Best Practices: Managed Identity, RBAC, audit logging

**Next Steps**:
1. Review this strategy with team
2. Begin implementation in Week 1-2 of Phase 4
3. Create ConfigManager utility class (shared/config.py)
4. Document operational procedures (updating settings, rotating secrets)

---

**Document Status**: Recommendation
**Created**: January 25, 2026
**Author**: Development Team
**Review Required**: Before Phase 4 implementation
