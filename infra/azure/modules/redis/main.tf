variable "name_prefix"         { type = string }
variable "location"            { type = string }
variable "resource_group_name" { type = string }
variable "capacity" {
  type    = number
  default = 1
}
variable "tags" { type = map(string) }

resource "azurerm_redis_cache" "main" {
  name                = "${var.name_prefix}-redis"
  location            = var.location
  resource_group_name = var.resource_group_name
  capacity            = var.capacity
  family              = "C"
  sku_name            = "Standard"
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"

  redis_configuration {
    maxmemory_policy = "allkeys-lru"
  }

  tags = var.tags
}

output "hostname"    { value = azurerm_redis_cache.main.hostname }
output "primary_key" {
  value     = azurerm_redis_cache.main.primary_access_key
  sensitive = true
}
output "ssl_port"    { value = azurerm_redis_cache.main.ssl_port }
