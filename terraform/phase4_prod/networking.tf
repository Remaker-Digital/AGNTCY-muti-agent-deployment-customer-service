# Phase 4: Networking Configuration
# VNet, Subnets, NSGs, Private Endpoints

# ============================================================================
# VIRTUAL NETWORK
# ============================================================================

resource "azurerm_virtual_network" "main" {
  name                = "${local.name_prefix}-vnet"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  address_space       = var.vnet_address_space

  tags = local.common_tags

  # Cost: $0 (VNet is free)
}

# ============================================================================
# SUBNETS
# ============================================================================

# Subnet for Container Instances
resource "azurerm_subnet" "containers" {
  name                 = "${local.name_prefix}-subnet-containers"
  resource_group_name  = data.azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.subnet_containers]

  # Service endpoints for Key Vault and Cosmos DB access
  service_endpoints = ["Microsoft.KeyVault", "Microsoft.AzureCosmosDB"]

  # Delegation required for Container Instances
  delegation {
    name = "aci-delegation"
    service_delegation {
      name    = "Microsoft.ContainerInstance/containerGroups"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

# Subnet for Private Endpoints (Cosmos DB, Key Vault)
resource "azurerm_subnet" "private_endpoints" {
  name                 = "${local.name_prefix}-subnet-pe"
  resource_group_name  = data.azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.subnet_private_endpoints]

  # Required for private endpoints
  private_endpoint_network_policies_enabled = false
}

# ============================================================================
# NETWORK SECURITY GROUPS
# ============================================================================

resource "azurerm_network_security_group" "containers" {
  name                = "${local.name_prefix}-nsg-containers"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name

  # Allow HTTPS inbound from internet (for Application Gateway in Phase 5)
  security_rule {
    name                       = "allow-https-inbound"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = var.subnet_containers
  }

  # Allow Application Gateway subnet to reach API Gateway (port 8080)
  # Required for AppGW backend health probes and traffic routing
  security_rule {
    name                       = "allow-appgw-to-api-gateway"
    priority                   = 103
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "8080"
    source_address_prefix      = var.subnet_appgateway
    destination_address_prefix = var.subnet_containers
  }

  # Allow Application Gateway subnet to reach SLIM (port 8443)
  # Required for AppGW backend health probes and traffic routing
  security_rule {
    name                       = "allow-appgw-to-slim"
    priority                   = 105
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "8443"
    source_address_prefix      = var.subnet_appgateway
    destination_address_prefix = var.subnet_containers
  }

  # Allow inter-container communication (SLIM protocol)
  security_rule {
    name                       = "allow-slim-internal"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "8443"
    source_address_prefix      = var.subnet_containers
    destination_address_prefix = var.subnet_containers
  }

  # Allow container ports
  security_rule {
    name                       = "allow-container-ports"
    priority                   = 120
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "8080"
    source_address_prefix      = var.subnet_containers
    destination_address_prefix = var.subnet_containers
  }

  # Deny all other inbound
  security_rule {
    name                       = "deny-all-inbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  tags = local.common_tags
}

resource "azurerm_subnet_network_security_group_association" "containers" {
  subnet_id                 = azurerm_subnet.containers.id
  network_security_group_id = azurerm_network_security_group.containers.id
}

# ============================================================================
# PRIVATE DNS ZONES (for Private Endpoints)
# ============================================================================

resource "azurerm_private_dns_zone" "cosmos" {
  count               = var.enable_private_endpoints ? 1 : 0
  name                = "privatelink.documents.azure.com"
  resource_group_name = data.azurerm_resource_group.main.name

  tags = local.common_tags
}

resource "azurerm_private_dns_zone" "keyvault" {
  count               = var.enable_private_endpoints ? 1 : 0
  name                = "privatelink.vaultcore.azure.net"
  resource_group_name = data.azurerm_resource_group.main.name

  tags = local.common_tags
}

# Link DNS zones to VNet
resource "azurerm_private_dns_zone_virtual_network_link" "cosmos" {
  count                 = var.enable_private_endpoints ? 1 : 0
  name                  = "${local.name_prefix}-cosmos-dns-link"
  resource_group_name   = data.azurerm_resource_group.main.name
  private_dns_zone_name = azurerm_private_dns_zone.cosmos[0].name
  virtual_network_id    = azurerm_virtual_network.main.id

  tags = local.common_tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "keyvault" {
  count                 = var.enable_private_endpoints ? 1 : 0
  name                  = "${local.name_prefix}-kv-dns-link"
  resource_group_name   = data.azurerm_resource_group.main.name
  private_dns_zone_name = azurerm_private_dns_zone.keyvault[0].name
  virtual_network_id    = azurerm_virtual_network.main.id

  tags = local.common_tags
}
