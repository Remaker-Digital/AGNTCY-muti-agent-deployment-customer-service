# Phase 4: Variables
# All sensitive values should be passed via environment variables or terraform.tfvars

# ============================================================================
# REQUIRED VARIABLES
# ============================================================================

variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "tenant_id" {
  description = "Azure tenant ID"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the existing resource group"
  type        = string
  default     = "agntcy-prod-rg"
}

variable "owner_email" {
  description = "Email address for resource owner (used in tags and alerts)"
  type        = string
}

# ============================================================================
# AZURE OPENAI (EXISTING IN WEST US)
# ============================================================================

variable "azure_openai_name" {
  description = "Name of existing Azure OpenAI resource"
  type        = string
  default     = "myOAIResource3aa68d"
}

variable "azure_openai_resource_group" {
  description = "Resource group containing Azure OpenAI"
  type        = string
  default     = "myAOAIResourceGroup3aa68d"
}

variable "azure_openai_endpoint" {
  description = "Azure OpenAI endpoint URL"
  type        = string
  sensitive   = true
}

variable "azure_openai_api_key" {
  description = "Azure OpenAI API key (will be stored in Key Vault)"
  type        = string
  sensitive   = true
}

variable "gpt4o_mini_deployment" {
  description = "GPT-4o-mini deployment name for intent/critic"
  type        = string
  default     = "gpt-4o-mini"
}

variable "gpt4o_deployment" {
  description = "GPT-4o deployment name for response generation"
  type        = string
  default     = "gpt-4o"
}

variable "embedding_deployment" {
  description = "Embedding model deployment name for RAG"
  type        = string
  default     = "text-embedding-3-large"
}

# ============================================================================
# EXTERNAL SERVICE CREDENTIALS
# ============================================================================

variable "shopify_api_key" {
  description = "Shopify Partner API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "shopify_api_secret" {
  description = "Shopify Partner API secret"
  type        = string
  sensitive   = true
  default     = ""
}

variable "shopify_store_url" {
  description = "Shopify development store URL"
  type        = string
  default     = ""
}

variable "zendesk_subdomain" {
  description = "Zendesk subdomain (e.g., 'mycompany' for mycompany.zendesk.com)"
  type        = string
  default     = ""
}

variable "zendesk_api_token" {
  description = "Zendesk API token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "zendesk_email" {
  description = "Zendesk admin email for API authentication"
  type        = string
  default     = ""
}

variable "mailchimp_api_key" {
  description = "Mailchimp API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "google_analytics_property_id" {
  description = "Google Analytics 4 property ID"
  type        = string
  default     = ""
}

variable "google_analytics_credentials_json" {
  description = "Google Analytics service account JSON (base64 encoded)"
  type        = string
  sensitive   = true
  default     = ""
}

# ============================================================================
# NETWORKING
# ============================================================================

variable "vnet_address_space" {
  description = "Virtual network address space"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

variable "subnet_containers" {
  description = "Subnet CIDR for container instances"
  type        = string
  default     = "10.0.1.0/24"
}

variable "subnet_private_endpoints" {
  description = "Subnet CIDR for private endpoints"
  type        = string
  default     = "10.0.2.0/24"
}

# ============================================================================
# CONTAINER CONFIGURATION
# ============================================================================

variable "container_registry_sku" {
  description = "Azure Container Registry SKU"
  type        = string
  default     = "Basic"

  validation {
    condition     = contains(["Basic", "Standard"], var.container_registry_sku)
    error_message = "Container registry SKU must be Basic or Standard (not Premium - cost optimization)."
  }
}

variable "container_cpu_default" {
  description = "Default CPU cores for containers"
  type        = number
  default     = 0.5
}

variable "container_memory_default" {
  description = "Default memory in GB for containers"
  type        = number
  default     = 1.0
}

# ============================================================================
# COSMOS DB
# ============================================================================

variable "cosmos_db_enable_serverless" {
  description = "Enable serverless mode for Cosmos DB (recommended for cost)"
  type        = bool
  default     = true
}

variable "cosmos_db_backup_retention_hours" {
  description = "Cosmos DB continuous backup retention in hours"
  type        = number
  default     = 720 # 30 days
}

# ============================================================================
# OBSERVABILITY
# ============================================================================

variable "log_retention_days" {
  description = "Log Analytics workspace retention in days"
  type        = number
  default     = 30 # Minimum for PerGB2018 SKU

  validation {
    condition     = var.log_retention_days >= 30 && var.log_retention_days <= 730
    error_message = "Log retention must be between 30 and 730 days for PerGB2018 SKU."
  }
}

variable "application_insights_sampling_percentage" {
  description = "Application Insights sampling percentage (50% for cost optimization)"
  type        = number
  default     = 50

  validation {
    condition     = var.application_insights_sampling_percentage >= 1 && var.application_insights_sampling_percentage <= 100
    error_message = "Sampling percentage must be between 1 and 100."
  }
}

# ============================================================================
# BUDGET ALERTS
# ============================================================================

variable "budget_amount" {
  description = "Monthly budget amount in USD"
  type        = number
  default     = 360
}

variable "budget_alert_threshold_warning" {
  description = "Budget alert threshold percentage for warning (83% = $299)"
  type        = number
  default     = 83
}

variable "budget_alert_threshold_critical" {
  description = "Budget alert threshold percentage for critical (93% = $335)"
  type        = number
  default     = 93
}

# ============================================================================
# FEATURE FLAGS
# ============================================================================

variable "enable_private_endpoints" {
  description = "Enable private endpoints for Cosmos DB and Key Vault"
  type        = bool
  default     = true
}

variable "enable_nats_jetstream" {
  description = "Enable NATS JetStream for event bus"
  type        = bool
  default     = true
}

variable "enable_multi_language" {
  description = "Enable multi-language response generation (en, fr-ca, es)"
  type        = bool
  default     = false # Phase 4 starts with English only, add languages later
}

variable "deploy_containers" {
  description = "Deploy container instances (set to false until images are built)"
  type        = bool
  default     = false # Set to true after images are pushed to ACR
}

# ============================================================================
# APPLICATION GATEWAY
# ============================================================================

variable "enable_application_gateway" {
  description = "Enable Application Gateway for public HTTPS access"
  type        = bool
  default     = false # Set to true when ready for public access
}

variable "ssl_certificate_password" {
  description = "Password for the SSL certificate PFX file"
  type        = string
  sensitive   = true
  default     = ""
}
