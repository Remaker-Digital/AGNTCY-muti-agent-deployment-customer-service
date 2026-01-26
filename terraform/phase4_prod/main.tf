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
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
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
  agents = {
    intent-classifier = {
      cpu    = 0.5
      memory = 1.0
      port   = 8080
    }
    knowledge-retrieval = {
      cpu    = 0.5
      memory = 1.0
      port   = 8080
    }
    response-generator = {
      cpu    = 0.5
      memory = 1.5
      port   = 8080
    }
    escalation = {
      cpu    = 0.5
      memory = 1.0
      port   = 8080
    }
    analytics = {
      cpu    = 0.5
      memory = 1.0
      port   = 8080
    }
    critic-supervisor = {
      cpu    = 0.5
      memory = 1.0
      port   = 8080
    }
  }
}
