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

  # SLIM Gateway backend (main entry point for agents)
  backend_address_pool {
    name         = "slim-backend-pool"
    ip_addresses = ["10.0.1.4"] # SLIM gateway private IP
  }

  # Direct agent access (optional, for debugging/monitoring)
  backend_address_pool {
    name         = "agents-backend-pool"
    ip_addresses = [
      "10.0.1.6",  # Knowledge Retrieval
      "10.0.1.7",  # Critic/Supervisor
      "10.0.1.8",  # Response Generator
      "10.0.1.9",  # Analytics
      "10.0.1.10", # Intent Classifier
      "10.0.1.11"  # Escalation
    ]
  }

  # ============================================================================
  # BACKEND HTTP SETTINGS
  # ============================================================================

  # HTTPS backend settings for SLIM (TLS termination at SLIM)
  # Note: For production, you'd add a trusted_root_certificate block
  # For this educational project, we allow untrusted backend certs
  backend_http_settings {
    name                                = "slim-https-settings"
    cookie_based_affinity               = "Disabled"
    port                                = 8443
    protocol                            = "Https"
    request_timeout                     = 60
    pick_host_name_from_backend_address = true
  }

  # HTTP backend settings for direct agent access
  backend_http_settings {
    name                  = "agents-http-settings"
    cookie_based_affinity = "Disabled"
    port                  = 8080
    protocol              = "Http"
    request_timeout       = 30
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

  # Main HTTPS routing rule - routes to SLIM gateway
  request_routing_rule {
    name                       = "https-to-slim"
    priority                   = 200
    rule_type                  = "Basic"
    http_listener_name         = "https-listener"
    backend_address_pool_name  = "slim-backend-pool"
    backend_http_settings_name = "slim-https-settings"
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

  probe {
    name                = "slim-health-probe"
    protocol            = "Https"
    path                = "/health"
    host                = "slim.internal"
    interval            = 30
    timeout             = 30
    unhealthy_threshold = 3

    match {
      status_code = ["200-399"]
    }
  }

  probe {
    name                = "agents-health-probe"
    protocol            = "Http"
    path                = "/health"
    interval            = 30
    timeout             = 30
    unhealthy_threshold = 3
    pick_host_name_from_backend_http_settings = true

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
