variable "name_prefix"         { type = string }
variable "location"            { type = string }
variable "resource_group_name" { type = string }
variable "subnet_id"           { type = string }
variable "db_password" {
  type      = string
  sensitive = true
}
variable "sku_name" {
  type    = string
  default = "B_Standard_B2ms"
}
variable "tags"                { type = map(string) }

resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "${var.name_prefix}-postgres"
  resource_group_name    = var.resource_group_name
  location               = var.location
  version                = "16"
  delegated_subnet_id    = var.subnet_id
  administrator_login    = "forgeops"
  administrator_password = var.db_password
  sku_name               = var.sku_name
  storage_mb             = 32768
  backup_retention_days  = 7
  geo_redundant_backup_enabled = false

  high_availability {
    mode = "Disabled"   # set to SameZone for production
  }

  tags = var.tags

  lifecycle { prevent_destroy = true }
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = "forgeops"
  server_id = azurerm_postgresql_flexible_server.main.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

# Enable pgvector extension
resource "azurerm_postgresql_flexible_server_configuration" "azure_extensions" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "VECTOR,UUID-OSSP,PG_TRGM"
}

resource "azurerm_postgresql_flexible_server_configuration" "shared_preload" {
  name      = "shared_preload_libraries"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "pg_stat_statements"
}

output "fqdn"     { value = azurerm_postgresql_flexible_server.main.fqdn }
output "server_id" { value = azurerm_postgresql_flexible_server.main.id }
