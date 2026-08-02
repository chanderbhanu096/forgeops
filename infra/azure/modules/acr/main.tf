variable "name_prefix"         { type = string }
variable "location"            { type = string }
variable "resource_group_name" { type = string }
variable "tags"                { type = map(string) }

# ACR name must be globally unique, alphanumeric only, 5-50 chars
locals {
  acr_name = replace("${var.name_prefix}acr", "-", "")
}

resource "azurerm_container_registry" "main" {
  name                = local.acr_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Standard"
  admin_enabled       = false   # use managed identity, not admin credentials

  retention_policy {
    days    = 30
    enabled = true
  }

  tags = var.tags
}

output "login_server" { value = azurerm_container_registry.main.login_server }
output "registry_id"  { value = azurerm_container_registry.main.id }
