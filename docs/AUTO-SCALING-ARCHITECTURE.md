# Auto-Scaling Architecture for Enterprise Retail Volume

**Created:** 2026-01-27
**Status:** REQUIREMENT (Phase 5 mandatory)
**Target:** 10,000 daily customer users

---

## Executive Summary

This document defines the auto-scaling architecture required to support enterprise retail volume (10,000 daily users) for the multi-agent customer service platform. The system must demonstrate:

1. **Horizontal scaling** of agent container instances
2. **Load balancing** across multiple instances
3. **Connection pooling** to external resources (Azure OpenAI, Cosmos DB)
4. **Automatic resource reclamation** during low-usage periods
5. **Cost efficiency** through scale-to-zero capabilities

---

## Load Analysis

### Traffic Pattern Assumptions

| Metric | Value | Calculation |
|--------|-------|-------------|
| Daily Users | 10,000 | Business requirement |
| Conversations/User | 2.5 | Average retail engagement |
| Messages/Conversation | 4 | Typical interaction length |
| **Daily Messages** | **100,000** | 10,000 × 2.5 × 4 |
| Peak Hour Factor | 3x | Standard retail pattern |
| **Peak Hour Messages** | **12,500** | 100,000 ÷ 24 × 3 |
| **Peak Requests/Second** | **3.5** | 12,500 ÷ 3,600 |

### Current System Performance (Baseline)

| Metric | Current Value | Notes |
|--------|--------------|-------|
| Single Instance Throughput | 0.22 RPS | Measured in load test |
| Response Time (P95) | 14.9s | At 3 concurrent users |
| Azure OpenAI Calls/Request | 4 | Critic, Intent, Escalation, Response |
| Tokens/Request | ~1,000 | Estimated average |

### Required Capacity

| Metric | Requirement | Calculation |
|--------|-------------|-------------|
| Peak RPS | 3.5 | From traffic analysis |
| Instances Needed | **16** | 3.5 ÷ 0.22 (with headroom) |
| Azure OpenAI TPM | **210,000** | 3.5 × 1,000 × 60 |
| Concurrent Users | **50** | 3.5 × 14.9s response time |

---

## Auto-Scaling Architecture Options

### Option 1: Azure Container Apps (RECOMMENDED)

**Why Container Apps?**
- Native Kubernetes-based auto-scaling (KEDA)
- Scale to zero capability
- Built-in load balancing
- Cost-effective for variable workloads

```
┌─────────────────────────────────────────────────────────────────┐
│                    Azure Container Apps Environment              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Ingress (HTTPS)                       │   │
│  │              agntcy-cs.azurecontainerapps.io            │   │
│  └────────────────────────┬────────────────────────────────┘   │
│                           │                                     │
│  ┌────────────────────────▼────────────────────────────────┐   │
│  │              API Gateway Container App                   │   │
│  │         (Scale: 0-10 replicas, HTTP trigger)            │   │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐          │   │
│  │  │ R1   │ │ R2   │ │ R3   │ │ ...  │ │ R10  │          │   │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘          │   │
│  └────────────────────────┬────────────────────────────────┘   │
│                           │                                     │
│  ┌────────────────────────▼────────────────────────────────┐   │
│  │              SLIM Gateway Container App                  │   │
│  │         (Scale: 1-5 replicas, CPU trigger)              │   │
│  └────────────────────────┬────────────────────────────────┘   │
│                           │                                     │
│  ┌────────────────────────▼────────────────────────────────┐   │
│  │                   Agent Container Apps                   │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │   │
│  │  │ Intent      │ │ Response    │ │ Critic      │       │   │
│  │  │ (0-5)       │ │ (0-8)       │ │ (0-5)       │       │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘       │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │   │
│  │  │ Escalation  │ │ Knowledge   │ │ Analytics   │       │   │
│  │  │ (0-3)       │ │ (0-3)       │ │ (0-2)       │       │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │      Azure OpenAI Service     │
              │  (Connection Pool: 100 max)   │
              │  TPM: 200,000 (scalable)      │
              └───────────────────────────────┘
```

**Terraform Configuration:**

```hcl
# Container Apps Environment
resource "azurerm_container_app_environment" "main" {
  name                = "${local.name_prefix}-cae"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  # Cost optimization: Consumption plan with auto-scale
  infrastructure_subnet_id = azurerm_subnet.containers.id
}

# API Gateway Container App with HTTP scaling
resource "azurerm_container_app" "api_gateway" {
  name                         = "${local.name_prefix}-api-gateway"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = data.azurerm_resource_group.main.name
  revision_mode                = "Single"

  template {
    container {
      name   = "api-gateway"
      image  = "${azurerm_container_registry.main.login_server}/api-gateway:v1.1.2-openai"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "AZURE_OPENAI_ENDPOINT"
        value = var.azure_openai_endpoint
      }
      # ... other env vars
    }

    # Auto-scaling configuration
    min_replicas = 0  # Scale to zero during off-hours
    max_replicas = 10 # Peak capacity

    # HTTP-based scaling trigger
    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = 10  # Scale up when >10 concurrent requests
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8080
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}

# Response Generator with higher scale (most resource-intensive)
resource "azurerm_container_app" "response_generator" {
  name                         = "${local.name_prefix}-response-gen"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = data.azurerm_resource_group.main.name
  revision_mode                = "Single"

  template {
    container {
      name   = "response-generator"
      image  = "${azurerm_container_registry.main.login_server}/response-generator:v1.1.0-openai"
      cpu    = 1.0
      memory = "2Gi"
    }

    min_replicas = 0
    max_replicas = 8  # Higher scale for response generation

    # CPU-based scaling trigger
    custom_scale_rule {
      name             = "cpu-scaling"
      custom_rule_type = "cpu"
      metadata = {
        type  = "Utilization"
        value = "70"  # Scale up at 70% CPU
      }
    }
  }
}
```

**Cost Estimate:**

| Component | Min | Max | Monthly Cost |
|-----------|-----|-----|--------------|
| API Gateway | 0 | 10 | $0-150 |
| SLIM Gateway | 1 | 5 | $30-150 |
| Intent Classifier | 0 | 5 | $0-75 |
| Response Generator | 0 | 8 | $0-240 |
| Critic/Supervisor | 0 | 5 | $0-75 |
| Escalation | 0 | 3 | $0-45 |
| Knowledge Retrieval | 0 | 3 | $0-45 |
| Analytics | 0 | 2 | $0-30 |
| Azure OpenAI (200K TPM) | - | - | $200-400 |
| **Total** | | | **$230-1,210** |

---

### Option 2: Azure Kubernetes Service (AKS)

**Why AKS?**
- Full Kubernetes control
- Custom HPA (Horizontal Pod Autoscaler) configurations
- KEDA integration for event-driven scaling
- Better for complex orchestration needs

```yaml
# Horizontal Pod Autoscaler for API Gateway
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-gateway-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # 5 min cooldown
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0  # Immediate scale-up
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
```

**Cost Estimate:**

| Component | Monthly Cost |
|-----------|--------------|
| AKS Control Plane | $73 (Standard) |
| Node Pool (Standard_D4s_v3) | $140-560 |
| Azure OpenAI | $200-400 |
| **Total** | **$413-1,033** |

---

### Option 3: Azure Container Instances with VMSS (Current + Enhancement)

**Why Enhance Current?**
- Minimal infrastructure changes
- Lower learning curve
- Suitable for moderate scale

**Implementation:**

```hcl
# Virtual Machine Scale Set for Container Instances
resource "azurerm_orchestrated_virtual_machine_scale_set" "agents" {
  name                = "${local.name_prefix}-vmss-agents"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name

  platform_fault_domain_count = 1

  sku_name = "Standard_D2s_v3"

  instances = 2  # Minimum instances

  os_profile {
    linux_configuration {
      computer_name_prefix = "agent"
      admin_username       = "azureuser"
    }
  }

  # Auto-scale based on CPU
  automatic_instance_repair {
    enabled      = true
    grace_period = "PT30M"
  }
}

# Auto-scale settings
resource "azurerm_monitor_autoscale_setting" "agents" {
  name                = "${local.name_prefix}-autoscale"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  target_resource_id  = azurerm_orchestrated_virtual_machine_scale_set.agents.id

  profile {
    name = "defaultProfile"

    capacity {
      default = 2
      minimum = 1
      maximum = 10
    }

    rule {
      metric_trigger {
        metric_name        = "Percentage CPU"
        metric_resource_id = azurerm_orchestrated_virtual_machine_scale_set.agents.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT5M"
        time_aggregation   = "Average"
        operator           = "GreaterThan"
        threshold          = 70
      }

      scale_action {
        direction = "Increase"
        type      = "ChangeCount"
        value     = "2"
        cooldown  = "PT5M"
      }
    }

    rule {
      metric_trigger {
        metric_name        = "Percentage CPU"
        metric_resource_id = azurerm_orchestrated_virtual_machine_scale_set.agents.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT10M"
        time_aggregation   = "Average"
        operator           = "LessThan"
        threshold          = 30
      }

      scale_action {
        direction = "Decrease"
        type      = "ChangeCount"
        value     = "1"
        cooldown  = "PT10M"
      }
    }
  }

  # Off-hours schedule (scale down at night)
  profile {
    name = "offHours"

    capacity {
      default = 1
      minimum = 1
      maximum = 2
    }

    recurrence {
      timezone = "Eastern Standard Time"
      days     = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
      hours    = [22]  # 10 PM
      minutes  = [0]
    }
  }

  # Business hours schedule (scale up in morning)
  profile {
    name = "businessHours"

    capacity {
      default = 4
      minimum = 2
      maximum = 10
    }

    recurrence {
      timezone = "Eastern Standard Time"
      days     = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
      hours    = [7]  # 7 AM
      minutes  = [0]
    }
  }
}
```

---

## Connection Pooling for External Resources

### Azure OpenAI Connection Pool

```python
# shared/openai_pool.py
"""
Azure OpenAI Connection Pool for High-Volume Workloads

Purpose: Manage multiple concurrent connections to Azure OpenAI to maximize
throughput while respecting rate limits.

Why connection pooling?
- Azure OpenAI has TPM (tokens per minute) limits
- Single connection creates head-of-line blocking
- Multiple connections allow parallel request processing
- Pool management prevents connection exhaustion

See: https://learn.microsoft.com/azure/ai-services/openai/quotas-limits
"""

import asyncio
from typing import Optional
from dataclasses import dataclass
from openai import AsyncAzureOpenAI
import logging

logger = logging.getLogger(__name__)


@dataclass
class PoolConfig:
    """Configuration for Azure OpenAI connection pool."""
    min_connections: int = 5
    max_connections: int = 50
    connection_timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0


class AzureOpenAIPool:
    """
    Connection pool for Azure OpenAI API.

    Manages multiple client instances to maximize throughput
    while respecting rate limits.

    Usage:
        pool = AzureOpenAIPool(endpoint, api_key, config)
        await pool.initialize()

        async with pool.acquire() as client:
            response = await client.chat.completions.create(...)
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        config: Optional[PoolConfig] = None
    ):
        self.endpoint = endpoint
        self.api_key = api_key
        self.config = config or PoolConfig()

        self._pool: asyncio.Queue[AsyncAzureOpenAI] = asyncio.Queue()
        self._active_connections = 0
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self):
        """Initialize the connection pool with minimum connections."""
        if self._initialized:
            return

        for _ in range(self.config.min_connections):
            client = self._create_client()
            await self._pool.put(client)
            self._active_connections += 1

        self._initialized = True
        logger.info(
            f"Azure OpenAI pool initialized with {self._active_connections} connections"
        )

    def _create_client(self) -> AsyncAzureOpenAI:
        """Create a new Azure OpenAI client."""
        return AsyncAzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version="2024-02-15-preview",
            timeout=self.config.connection_timeout,
            max_retries=self.config.max_retries
        )

    async def acquire(self) -> AsyncAzureOpenAI:
        """
        Acquire a client from the pool.

        If pool is empty and under max_connections, creates new client.
        Otherwise, waits for available client.
        """
        try:
            # Try to get existing client (non-blocking)
            return self._pool.get_nowait()
        except asyncio.QueueEmpty:
            pass

        # Check if we can create new connection
        async with self._lock:
            if self._active_connections < self.config.max_connections:
                client = self._create_client()
                self._active_connections += 1
                logger.debug(
                    f"Created new connection, total: {self._active_connections}"
                )
                return client

        # Wait for available client
        return await self._pool.get()

    async def release(self, client: AsyncAzureOpenAI):
        """Return a client to the pool."""
        await self._pool.put(client)

    async def close(self):
        """Close all connections in the pool."""
        while not self._pool.empty():
            client = await self._pool.get()
            await client.close()
            self._active_connections -= 1

        self._initialized = False
        logger.info("Azure OpenAI pool closed")

    @property
    def available(self) -> int:
        """Number of available connections."""
        return self._pool.qsize()

    @property
    def active(self) -> int:
        """Total active connections."""
        return self._active_connections


# Context manager for clean acquisition/release
class PooledClient:
    """Context manager for pooled Azure OpenAI client."""

    def __init__(self, pool: AzureOpenAIPool):
        self.pool = pool
        self.client: Optional[AsyncAzureOpenAI] = None

    async def __aenter__(self) -> AsyncAzureOpenAI:
        self.client = await self.pool.acquire()
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.pool.release(self.client)
```

### Cosmos DB Connection Optimization

```python
# shared/cosmosdb_pool.py
"""
Cosmos DB Connection Configuration for High-Volume Workloads

Purpose: Configure Cosmos DB client for optimal throughput with connection
pooling and automatic failover.

Why these settings?
- max_connection_retry_attempts: Handles transient failures
- preferred_regions: Minimizes latency with region affinity
- connection_mode: Gateway mode for firewall-friendly connections
- max_integrated_cache_staleness: Reduces RU consumption with caching

See: https://learn.microsoft.com/azure/cosmos-db/nosql/best-practice-python
"""

from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey
from dataclasses import dataclass
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class CosmosConfig:
    """Cosmos DB connection configuration."""
    endpoint: str
    key: str
    database_name: str
    preferred_regions: List[str] = None
    max_retry_attempts: int = 9
    enable_endpoint_discovery: bool = True
    connection_mode: str = "Gateway"  # or "Direct"


async def create_cosmos_client(config: CosmosConfig) -> CosmosClient:
    """
    Create optimized Cosmos DB client for high-volume workloads.

    Args:
        config: Cosmos DB configuration

    Returns:
        Configured CosmosClient instance
    """
    client = CosmosClient(
        url=config.endpoint,
        credential=config.key,
        # Connection pooling settings
        connection_retry_policy={
            "max_retry_attempts": config.max_retry_attempts,
            "fixed_retry_interval_in_ms": 1000,
            "max_retry_interval_in_ms": 30000,
        },
        # Region affinity for latency optimization
        preferred_locations=config.preferred_regions or ["East US 2"],
        # Enable automatic endpoint discovery for failover
        enable_endpoint_discovery=config.enable_endpoint_discovery,
    )

    logger.info(f"Cosmos DB client created for {config.endpoint}")
    return client
```

---

## Resource Reclamation Strategy

### Scale-to-Zero Configuration

```hcl
# Container Apps scale-to-zero rules
resource "azurerm_container_app" "agent" {
  # ...

  template {
    # Scale to zero when no traffic
    min_replicas = 0
    max_replicas = 10

    # HTTP scaling rule with idle timeout
    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = 10
    }
  }

  # Idle timeout for resource reclamation
  # Container is terminated after 300s of no requests
  lifecycle {
    idle_timeout_in_seconds = 300
  }
}
```

### Scheduled Scaling Profiles

```hcl
# Azure Monitor Autoscale with time-based profiles
resource "azurerm_monitor_autoscale_setting" "agents" {
  # ... (base configuration)

  # Business hours: High capacity
  profile {
    name = "business-hours"

    capacity {
      default = 4
      minimum = 2
      maximum = 16
    }

    recurrence {
      timezone = "Eastern Standard Time"
      days     = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
      hours    = [8]
      minutes  = [0]
    }
  }

  # Off-peak: Minimal capacity
  profile {
    name = "off-peak"

    capacity {
      default = 1
      minimum = 0  # Scale to zero allowed
      maximum = 4
    }

    recurrence {
      timezone = "Eastern Standard Time"
      days     = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
      hours    = [20]  # 8 PM
      minutes  = [0]
    }
  }

  # Weekend: Reduced capacity
  profile {
    name = "weekend"

    capacity {
      default = 1
      minimum = 0
      maximum = 4
    }

    recurrence {
      timezone = "Eastern Standard Time"
      days     = ["Saturday", "Sunday"]
      hours    = [0]
      minutes  = [0]
    }
  }
}
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Migrate from Container Instances to Container Apps
- [ ] Configure HTTP-based auto-scaling rules
- [ ] Implement connection pooling for Azure OpenAI
- [ ] Set up monitoring dashboards for scaling events

### Phase 2: Optimization (Week 3-4)
- [ ] Implement scale-to-zero for non-critical agents
- [ ] Add scheduled scaling profiles
- [ ] Configure Cosmos DB connection optimization
- [ ] Load test with 10,000 simulated daily users

### Phase 3: Validation (Week 5)
- [ ] Run 24-hour endurance test
- [ ] Validate cost projections
- [ ] Document operational procedures
- [ ] Create runbooks for scaling interventions

---

## Recommendation

**Recommended Option: Azure Container Apps**

Rationale:
1. **Native auto-scaling** with KEDA triggers (HTTP, CPU, custom metrics)
2. **Scale-to-zero** capability for cost optimization during off-hours
3. **Built-in load balancing** with no additional configuration
4. **Simpler management** than AKS while providing necessary scaling
5. **Cost-effective** for variable workloads (pay-per-use billing)

**Estimated Monthly Cost:**

| Scenario | Instances | Azure OpenAI | Total |
|----------|-----------|--------------|-------|
| Off-peak | 1-2 | $100 | ~$130 |
| Normal | 4-6 | $250 | ~$350 |
| Peak | 10-16 | $400 | ~$600 |
| **Average** | | | **~$350-450** |

This is within the revised budget of $310-360/month for base infrastructure, with additional Azure OpenAI costs scaling with usage.

---

## Monitoring & Alerting

### Key Metrics to Monitor

| Metric | Threshold | Action |
|--------|-----------|--------|
| Request Queue Length | >50 | Scale up |
| CPU Utilization | >70% | Scale up |
| Response Time P95 | >30s | Investigate |
| Error Rate | >1% | Alert |
| Active Instances | >80% max | Increase max |
| Azure OpenAI 429s | >10/min | Increase TPM |

### Alert Configuration

```hcl
resource "azurerm_monitor_metric_alert" "high_latency" {
  name                = "${local.name_prefix}-high-latency-alert"
  resource_group_name = data.azurerm_resource_group.main.name
  scopes              = [azurerm_container_app.api_gateway.id]

  criteria {
    metric_namespace = "Microsoft.App/containerApps"
    metric_name      = "RequestDuration"
    aggregation      = "P95"
    operator         = "GreaterThan"
    threshold        = 30000  # 30 seconds
  }

  action {
    action_group_id = azurerm_monitor_action_group.ops_team.id
  }
}
```

---

## References

- [Azure Container Apps Scaling](https://learn.microsoft.com/azure/container-apps/scale-app)
- [KEDA Scalers](https://keda.sh/docs/scalers/)
- [Azure OpenAI Quotas](https://learn.microsoft.com/azure/ai-services/openai/quotas-limits)
- [Cosmos DB Best Practices](https://learn.microsoft.com/azure/cosmos-db/nosql/best-practice-python)

---

**Document Version:** 1.0
**Author:** AGNTCY Development Team
**Review Required:** Architecture Team
