# Phase 4/5: Application Gateway for Public HTTPS Access
# Provides secure ingress to the multi-agent platform
# Cost: ~$20-30/month for Standard_v2 with minimal capacity

# ============================================================================
# APPLICATION GATEWAY SUBNET
# ============================================================================

# Application Gateway requires its own dedicated subnet (no delegations allowed)
resource "azurerm_subnet" "appgateway" {
  name                 = "${local.name_prefix}-subnet-appgw"
  resource_group_name  = data.azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.3.0/24"]

  # No delegations or service endpoints - required for App Gateway
}

# ============================================================================
# PUBLIC IP ADDRESS
# ============================================================================

resource "azurerm_public_ip" "appgateway" {
  count               = var.enable_application_gateway ? 1 : 0
  name                = "${local.name_prefix}-pip-appgw"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard" # Required for Application Gateway v2

  # Optional: Custom domain label for agntcy-cs-prod-xxxx.eastus2.cloudapp.azure.com
  domain_name_label   = "${local.name_prefix}-${random_string.suffix.result}"

  tags = local.common_tags
}

# ============================================================================
# APPLICATION GATEWAY
# ============================================================================

resource "azurerm_application_gateway" "main" {
  count               = var.enable_application_gateway ? 1 : 0
  name                = "${local.name_prefix}-appgw"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name

  # SKU: Standard_v2 is minimum for zone redundancy and autoscaling
  # Use V2 for WAF and better performance
  sku {
    name     = "Standard_v2"
    tier     = "Standard_v2"
  }

  # Autoscaling: 0-2 instances for cost optimization
  # 0 minimum = scale to zero when idle (lowest cost)
  autoscale_configuration {
    min_capacity = 0
    max_capacity = 2
  }

  # Gateway IP configuration - references the App Gateway subnet
  gateway_ip_configuration {
    name      = "gateway-ip-config"
    subnet_id = azurerm_subnet.appgateway.id
  }

  # Frontend port for HTTPS
  frontend_port {
    name = "https-port"
    port = 443
  }

  # Frontend port for HTTP (redirect to HTTPS)
  frontend_port {
    name = "http-port"
    port = 80
  }

  # Frontend IP configuration - public IP
  frontend_ip_configuration {
    name                 = "public-frontend"
    public_ip_address_id = azurerm_public_ip.appgateway[0].id
  }

  # ============================================================================
  # BACKEND POOLS
  # ============================================================================
  # Purpose: Define backend targets for Application Gateway routing
  #
  # Why dynamic IPs? Azure Container Instances get private IPs assigned at creation.
  # Using Terraform references ensures the Application Gateway always points to
  # the correct container IPs, even after redeployments.
  #
  # See: https://learn.microsoft.com/azure/application-gateway/application-gateway-components
  # Source of Record: terraform/phase4_prod/containers.tf (container group definitions)
  # ============================================================================

  # API Gateway backend (HTTP REST API for load testing and external access)
  # Why separate API Gateway? SLIM uses gRPC (HTTP/2 + protobufs) which Application
  # Gateway doesn't fully support for health probes. This FastAPI service provides
  # HTTP/1.1 REST endpoints that AppGW can properly health-check.
  # Cost Impact: ~$12-18/month (0.5 vCPU + 1GB RAM)
  # See: api_gateway/main.py for endpoint definitions
  backend_address_pool {
    name         = "api-gateway-backend-pool"
    ip_addresses = var.deploy_containers ? [azurerm_container_group.api_gateway[0].ip_address] : ["10.0.1.7"]
  }

  # SLIM Gateway backend (internal gRPC - kept for reference but not used by AppGW)
  # Why not used? SLIM uses gRPC which AppGW can't health-probe properly.
  # Agent-to-agent communication uses SLIM directly, bypassing AppGW.
  backend_address_pool {
    name         = "slim-backend-pool"
    ip_addresses = var.deploy_containers ? [azurerm_container_group.slim_gateway[0].ip_address] : ["10.0.1.4"]
  }

  # Direct agent access (optional, for debugging/monitoring)
  # Use with path-based routing rules for direct agent health checks
  backend_address_pool {
    name         = "agents-backend-pool"
    ip_addresses = var.deploy_containers ? [
      azurerm_container_group.knowledge_retrieval[0].ip_address,
      azurerm_container_group.critic_supervisor[0].ip_address,
      azurerm_container_group.response_generator[0].ip_address,
      azurerm_container_group.analytics[0].ip_address,
      azurerm_container_group.intent_classifier[0].ip_address,
      azurerm_container_group.escalation[0].ip_address
    ] : ["10.0.1.6", "10.0.1.7", "10.0.1.8", "10.0.1.9", "10.0.1.10", "10.0.1.11"]
  }

  # ============================================================================
  # BACKEND HTTP SETTINGS
  # ============================================================================
  # Purpose: Define how Application Gateway communicates with backend pools
  #
  # Why pick_host_name_from_backend_address = true?
  # When health probes use pick_host_name_from_backend_http_settings, the backend
  # settings must also use pick_host_name_from_backend_address for compatibility.
  # This tells AppGW to use the backend's IP address as the Host header.
  #
  # See: https://learn.microsoft.com/azure/application-gateway/configuration-http-settings
  # ============================================================================

  # HTTP backend settings for API Gateway (main traffic)
  # The API Gateway FastAPI service listens on port 8080
  backend_http_settings {
    name                                = "api-gateway-http-settings"
    cookie_based_affinity               = "Disabled"
    port                                = 8080
    protocol                            = "Http"
    request_timeout                     = 60
    pick_host_name_from_backend_address = true
    probe_name                          = "api-gateway-health-probe"
  }

  # HTTPS backend settings for SLIM (internal gRPC - NOT USED by Application Gateway)
  # Kept for reference; SLIM uses gRPC which AppGW can't health-probe properly
  backend_http_settings {
    name                                = "slim-https-settings"
    cookie_based_affinity               = "Disabled"
    port                                = 8443
    protocol                            = "Https"
    request_timeout                     = 60
    pick_host_name_from_backend_address = true
  }

  # HTTP backend settings for direct agent access (debugging/monitoring)
  backend_http_settings {
    name                                = "agents-http-settings"
    cookie_based_affinity               = "Disabled"
    port                                = 8080
    protocol                            = "Http"
    request_timeout                     = 30
    pick_host_name_from_backend_address = true
  }

  # ============================================================================
  # SSL CERTIFICATE (Self-signed for now - replace with real cert in production)
  # ============================================================================

  # Note: For production, use Azure Key Vault integration or Let's Encrypt
  # This creates a self-signed certificate for initial testing
  ssl_certificate {
    name     = "self-signed-cert"
    data     = filebase64("${path.module}/certs/appgw-cert.pfx")
    password = var.ssl_certificate_password
  }

  # ============================================================================
  # HTTP LISTENERS
  # ============================================================================

  # HTTPS listener for main traffic
  http_listener {
    name                           = "https-listener"
    frontend_ip_configuration_name = "public-frontend"
    frontend_port_name             = "https-port"
    protocol                       = "Https"
    ssl_certificate_name           = "self-signed-cert"
  }

  # HTTP listener (redirects to HTTPS)
  http_listener {
    name                           = "http-listener"
    frontend_ip_configuration_name = "public-frontend"
    frontend_port_name             = "http-port"
    protocol                       = "Http"
  }

  # ============================================================================
  # ROUTING RULES
  # ============================================================================

  # HTTP to HTTPS redirect rule
  request_routing_rule {
    name                       = "http-to-https-redirect"
    priority                   = 100
    rule_type                  = "Basic"
    http_listener_name         = "http-listener"
    redirect_configuration_name = "http-to-https"
  }

  # Main HTTPS routing rule - routes to API Gateway
  request_routing_rule {
    name                       = "https-to-api-gateway"
    priority                   = 200
    rule_type                  = "Basic"
    http_listener_name         = "https-listener"
    backend_address_pool_name  = "api-gateway-backend-pool"
    backend_http_settings_name = "api-gateway-http-settings"
  }

  # ============================================================================
  # REDIRECT CONFIGURATION
  # ============================================================================

  redirect_configuration {
    name                 = "http-to-https"
    redirect_type        = "Permanent"
    target_listener_name = "https-listener"
    include_path         = true
    include_query_string = true
  }

  # ============================================================================
  # HEALTH PROBES
  # ============================================================================
  # Purpose: Monitor backend health to enable automatic failover
  #
  # Why pick_host_name_from_backend_http_settings?
  # - Allows Application Gateway to use the backend's IP from the pool
  # - Avoids hardcoding IPs that may change on container redeployment
  # - Standard pattern for dynamic backend pools
  #
  # See: https://learn.microsoft.com/azure/application-gateway/application-gateway-probe-overview
  # ============================================================================

  # API Gateway health probe (main traffic)
  # The API Gateway exposes GET /health endpoint returning 200 OK with JSON body
  # See: api_gateway/main.py:health_check()
  probe {
    name                                      = "api-gateway-health-probe"
    protocol                                  = "Http"
    path                                      = "/health"
    pick_host_name_from_backend_http_settings = true
    interval                                  = 30
    timeout                                   = 30
    unhealthy_threshold                       = 3

    match {
      status_code = ["200-399"]
    }
  }

  # SLIM health probe (internal gRPC - NOT USED by Application Gateway)
  # Why kept? For reference and potential future use if SLIM adds HTTP health endpoint
  # Currently SLIM uses gRPC which AppGW can't health-probe via HTTP
  probe {
    name                                      = "slim-health-probe"
    protocol                                  = "Https"
    path                                      = "/health"
    pick_host_name_from_backend_http_settings = true
    interval                                  = 30
    timeout                                   = 30
    unhealthy_threshold                       = 3

    match {
      status_code = ["200-399"]
    }
  }

  # Agents health probe (for direct access testing)
  # Individual agents expose /health endpoints for container health checks
  probe {
    name                                      = "agents-health-probe"
    protocol                                  = "Http"
    path                                      = "/health"
    pick_host_name_from_backend_http_settings = true
    interval                                  = 30
    timeout                                   = 30
    unhealthy_threshold                       = 3

    match {
      status_code = ["200-399"]
    }
  }

  # SSL Policy - Use modern TLS 1.2+ (required by Azure as of 2025)
  ssl_policy {
    policy_type = "Predefined"
    policy_name = "AppGwSslPolicy20220101S"  # TLS 1.2 minimum, modern cipher suites
  }

  tags = local.common_tags

  # Lifecycle: Prevent accidental deletion
  lifecycle {
    prevent_destroy = false # Set to true in production
  }
}

# ============================================================================
# NSG RULES FOR APPLICATION GATEWAY
# ============================================================================

resource "azurerm_network_security_group" "appgateway" {
  count               = var.enable_application_gateway ? 1 : 0
  name                = "${local.name_prefix}-nsg-appgw"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name

  # Allow HTTPS inbound from internet
  security_rule {
    name                       = "allow-https-inbound"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "Internet"
    destination_address_prefix = "*"
  }

  # Allow HTTP inbound (for redirect to HTTPS)
  security_rule {
    name                       = "allow-http-inbound"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "Internet"
    destination_address_prefix = "*"
  }

  # Required: Allow Azure Gateway Manager (health probes)
  security_rule {
    name                       = "allow-gateway-manager"
    priority                   = 120
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "65200-65535"
    source_address_prefix      = "GatewayManager"
    destination_address_prefix = "*"
  }

  # Required: Allow Azure Load Balancer probes
  security_rule {
    name                       = "allow-azure-lb"
    priority                   = 130
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "AzureLoadBalancer"
    destination_address_prefix = "*"
  }

  tags = local.common_tags
}

resource "azurerm_subnet_network_security_group_association" "appgateway" {
  count                     = var.enable_application_gateway ? 1 : 0
  subnet_id                 = azurerm_subnet.appgateway.id
  network_security_group_id = azurerm_network_security_group.appgateway[0].id
}

# ============================================================================
# DIAGNOSTIC SETTINGS
# ============================================================================

resource "azurerm_monitor_diagnostic_setting" "appgateway" {
  count                      = var.enable_application_gateway ? 1 : 0
  name                       = "${local.name_prefix}-appgw-diag"
  target_resource_id         = azurerm_application_gateway.main[0].id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  # Access logs - essential for debugging
  enabled_log {
    category = "ApplicationGatewayAccessLog"
  }

  # Performance logs
  enabled_log {
    category = "ApplicationGatewayPerformanceLog"
  }

  # Firewall logs (if WAF enabled in future)
  enabled_log {
    category = "ApplicationGatewayFirewallLog"
  }

  # Metrics
  metric {
    category = "AllMetrics"
    enabled  = true
  }
}
