# Phase 4: Multi-Agent Customer Service Platform - Azure Production
# Region: East US 2 (compute), West US (Azure OpenAI - existing)
# Budget: $310-360/month
# Purpose: Educational example - cost-optimized multi-agent AI system using AGNTCY SDK
# Created: 2026-01-26

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.85"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state storage (configure after initial deployment)
  # backend "azurerm" {
  #   resource_group_name  = "agntcy-prod-rg"
  #   storage_account_name = "stagntcytfstate"
  #   container_name       = "tfstate"
  #   key                  = "phase4.tfstate"
  # }
}

provider "azurerm" {
  features {
    # -------------------------------------------------------------------------
    # Key Vault Settings - Non-Obvious Choices Explained
    # -------------------------------------------------------------------------
    # purge_soft_delete_on_destroy = false
    #   - Key Vault soft-delete keeps deleted vaults recoverable for 90 days
    #   - Setting to false prevents permanent deletion during terraform destroy
    #   - Reason: Prevents accidental loss of secrets during dev/test cycles
    #   - Production: Keep false to maintain audit trail and recovery option
    #
    # recover_soft_deleted_key_vaults = true
    #   - Automatically recover a soft-deleted vault with same name
    #   - Prevents "vault name already exists" errors on re-deploy
    #   - Reason: Simplifies dev/test lifecycle (destroy → apply)
    # -------------------------------------------------------------------------
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
    # -------------------------------------------------------------------------
    # Resource Group Settings
    # -------------------------------------------------------------------------
    # prevent_deletion_if_contains_resources = false
    #   - Allows terraform destroy to delete RG even if it contains resources
    #   - Default (true) would require manual cleanup of all resources first
    #   - Reason: Educational project - simplifies full teardown
    #   - Production: Set to true to prevent accidental data loss
    # -------------------------------------------------------------------------
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }

  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id
}

# Random suffix for globally unique names
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# Use existing resource group
data "azurerm_resource_group" "main" {
  name = var.resource_group_name
}

# Reference existing Azure OpenAI in West US
data "azurerm_cognitive_account" "openai" {
  name                = var.azure_openai_name
  resource_group_name = var.azure_openai_resource_group
}

# ============================================================================
# LOCAL VALUES
# ============================================================================

locals {
  # Naming convention: {resource-type}-{project}-{env}-{region}
  name_prefix = "agntcy-cs-prod"
  location    = "eastus2"

  # Common tags for cost allocation
  common_tags = {
    Project       = "AGNTCY-CustomerService"
    Environment   = "Production"
    Phase         = "Phase4"
    ManagedBy     = "Terraform"
    CostCenter    = "Engineering"
    Owner         = var.owner_email
    Purpose       = "Educational-Example"
    AgentCount    = "6"
    Budget        = "310-360"
    CreatedDate   = "2026-01-26"
    GitRepository = "AGNTCY-muti-agent-deployment-customer-service"
  }

  # Agent configurations
  # ============================================================================
  # Container Right-Sizing (Post-Phase 5 Cost Optimization)
  # ============================================================================
  # These values have been optimized based on production load testing results.
  # See: docs/POST-PHASE5-COST-OPTIMIZATION-PLAN.md (Initiative 2)
  # See: tests/load/LOAD-TEST-REPORT-2026-01-27.md for profiling data
  #
  # Optimization Notes:
  # - Analytics: Reduced to 0.25 vCPU / 0.5 GB (batch processing, not real-time)
  # - Response Generator: Kept at 0.5 vCPU / 1.5 GB (handles larger context windows)
  # - All others: 0.5 vCPU / 1.0 GB (standard configuration)
  #
  # To revert to original values, change var.enable_container_right_sizing to false
  # ============================================================================
  agents = {
    intent-classifier = {
      cpu    = var.enable_container_right_sizing ? 0.5 : 0.5
      memory = var.enable_container_right_sizing ? 1.0 : 1.0
      port   = 8080
    }
    knowledge-retrieval = {
      cpu    = var.enable_container_right_sizing ? 0.5 : 0.5
      memory = var.enable_container_right_sizing ? 1.0 : 1.0
      port   = 8080
    }
    response-generator = {
      # Response generator needs more memory for larger context windows
      cpu    = var.enable_container_right_sizing ? 0.5 : 0.5
      memory = var.enable_container_right_sizing ? 1.5 : 1.5
      port   = 8080
    }
    escalation = {
      cpu    = var.enable_container_right_sizing ? 0.5 : 0.5
      memory = var.enable_container_right_sizing ? 1.0 : 1.0
      port   = 8080
    }
    analytics = {
      # Analytics is batch processing - reduced for cost optimization
      # Savings: ~$4/month with 0.25 vCPU / 0.5 GB
      cpu    = var.enable_container_right_sizing ? 0.25 : 0.5
      memory = var.enable_container_right_sizing ? 0.5 : 1.0
      port   = 8080
    }
    critic-supervisor = {
      cpu    = var.enable_container_right_sizing ? 0.5 : 0.5
      memory = var.enable_container_right_sizing ? 1.0 : 1.0
      port   = 8080
    }
  }
}
