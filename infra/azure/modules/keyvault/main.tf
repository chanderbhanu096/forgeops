variable "name_prefix"         { type = string }
variable "location"            { type = string }
variable "resource_group_name" { type = string }
variable "tenant_id"           { type = string }
variable "object_id"           { type = string }
variable "secrets" {
  type      = map(string)
  sensitive = true
}
variable "tags"                { type = map(string) }

# Key Vault name must be globally unique, 3-24 chars
locals {
  kv_name = "${var.name_prefix}-kv"
}

resource "azurerm_key_vault" "main" {
  name                        = local.kv_name
  location                    = var.location
  resource_group_name         = var.resource_group_name
  tenant_id                   = var.tenant_id
  sku_name                    = "standard"
  purge_protection_enabled    = true
  soft_delete_retention_days  = 7
  enable_rbac_authorization   = true   # use RBAC, not access policies

  network_acls {
    bypass         = "AzureServices"
    default_action = "Allow"   # restrict to VNet in production
  }

  tags = var.tags
}

# Initial access policy for the deploying principal (to write secrets)
resource "azurerm_role_assignment" "deployer_kv_admin" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = var.object_id
}

resource "azurerm_key_vault_secret" "secrets" {
  for_each     = var.secrets
  name         = each.key
  value        = each.value
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_role_assignment.deployer_kv_admin]

  lifecycle { ignore_changes = [value] }
}

output "vault_id"   { value = azurerm_key_vault.main.id }
output "vault_uri"  { value = azurerm_key_vault.main.vault_uri }
output "secret_ids" {
  value = { for k, v in azurerm_key_vault_secret.secrets : k => v.id }
}
