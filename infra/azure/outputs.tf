output "api_fqdn" {
  description = "FQDN of the API Container App"
  value       = azurerm_container_app.api.latest_revision_fqdn
}

output "web_fqdn" {
  description = "FQDN of the Web Container App"
  value       = azurerm_container_app.web.latest_revision_fqdn
}

output "acr_login_server" {
  description = "ACR login server URL"
  value       = module.acr.login_server
}

output "postgres_fqdn" {
  description = "PostgreSQL server FQDN"
  value       = module.postgres.fqdn
  sensitive   = true
}

output "redis_hostname" {
  description = "Redis hostname"
  value       = module.redis.hostname
}

output "key_vault_uri" {
  description = "Key Vault URI"
  value       = module.keyvault.vault_uri
}

output "managed_identity_client_id" {
  description = "Client ID of the managed identity for Container Apps"
  value       = azurerm_user_assigned_identity.app.client_id
}
