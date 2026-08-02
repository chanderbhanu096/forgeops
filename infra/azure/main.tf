# ForgeOps — Azure Container Apps deployment
#
# Resources:
#   Resource Group
#   Virtual Network + subnets
#   Azure Container Registry (ACR)
#   Azure Database for PostgreSQL Flexible Server
#   Azure Cache for Redis
#   Azure Key Vault (secrets)
#   Container Apps Environment (with VNet integration)
#   Container Apps: api, web, mcp-github, mcp-data, mcp-knowledge
#   Log Analytics Workspace

terraform {
  required_version = ">= 1.7"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.110"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.50"
    }
  }

  # Uncomment for remote state
  # backend "azurerm" {
  #   resource_group_name  = "forgeops-tfstate"
  #   storage_account_name = "forgeopsstate"
  #   container_name       = "tfstate"
  #   key                  = "forgeops.tfstate"
  # }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
  }
}

data "azurerm_client_config" "current" {}

locals {
  name_prefix = "${var.project}-${var.environment}"
  rg_name     = "${local.name_prefix}-rg"
  tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# ── Resource Group ────────────────────────────────────────────────────────────

resource "azurerm_resource_group" "main" {
  name     = local.rg_name
  location = var.location
  tags     = local.tags
}

# ── Virtual Network ───────────────────────────────────────────────────────────

resource "azurerm_virtual_network" "main" {
  name                = "${local.name_prefix}-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags
}

resource "azurerm_subnet" "container_apps" {
  name                 = "container-apps"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.0.0/23"]
  # Container Apps needs a /23 minimum for the environment
  delegation {
    name = "Microsoft.App.environments"
    service_delegation {
      name    = "Microsoft.App/environments"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_subnet" "data" {
  name                 = "data"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.4.0/24"]
  service_endpoints    = ["Microsoft.Storage"]
}

# ── Log Analytics ─────────────────────────────────────────────────────────────

resource "azurerm_log_analytics_workspace" "main" {
  name                = "${local.name_prefix}-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

# ── Azure Container Registry ──────────────────────────────────────────────────

module "acr" {
  source = "./modules/acr"

  name_prefix         = local.name_prefix
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags
}

# ── PostgreSQL Flexible Server ────────────────────────────────────────────────

module "postgres" {
  source = "./modules/postgres"

  name_prefix         = local.name_prefix
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = azurerm_subnet.data.id
  db_password         = var.db_password
  sku_name            = var.postgres_sku
  tags                = local.tags
}

# ── Azure Cache for Redis ─────────────────────────────────────────────────────

module "redis" {
  source = "./modules/redis"

  name_prefix         = local.name_prefix
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  capacity            = var.redis_capacity
  tags                = local.tags
}

# ── Key Vault ─────────────────────────────────────────────────────────────────

module "keyvault" {
  source = "./modules/keyvault"

  name_prefix         = local.name_prefix
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  object_id           = data.azurerm_client_config.current.object_id
  tags                = local.tags

  secrets = {
    db-password    = var.db_password
    openai-api-key = var.openai_api_key
    mcp-secret     = var.mcp_secret
    github-token   = var.github_token
  }
}

# ── Container Apps Environment ────────────────────────────────────────────────

resource "azurerm_container_app_environment" "main" {
  name                       = "${local.name_prefix}-env"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  infrastructure_subnet_id   = azurerm_subnet.container_apps.id
  tags                       = local.tags
}

# ── Managed Identity for Container Apps ──────────────────────────────────────

resource "azurerm_user_assigned_identity" "app" {
  name                = "${local.name_prefix}-app-identity"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags
}

# Grant managed identity: ACR pull
resource "azurerm_role_assignment" "acr_pull" {
  scope                = module.acr.registry_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

# Grant managed identity: Key Vault Secrets User
resource "azurerm_role_assignment" "keyvault_secrets" {
  scope                = module.keyvault.vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

# ── API Container App ─────────────────────────────────────────────────────────

resource "azurerm_container_app" "api" {
  name                         = "${local.name_prefix}-api"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  registry {
    server   = module.acr.login_server
    identity = azurerm_user_assigned_identity.app.id
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = var.api_min_replicas
    max_replicas = var.api_max_replicas

    container {
      name   = "api"
      image  = "${module.acr.login_server}/forgeops-api:${var.image_tag}"
      cpu    = 1.0
      memory = "2Gi"

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }
      env {
        name  = "REDIS_URL"
        value = "rediss://:${module.redis.primary_key}@${module.redis.hostname}:6380/0"
      }
      env {
        name  = "DATABASE_URL"
        value = "postgresql+asyncpg://forgeops:${var.db_password}@${module.postgres.fqdn}/forgeops?sslmode=require"
      }
      env {
        name        = "OPENAI_API_KEY"
        secret_name = "openai-api-key"
      }
      env {
        name        = "MCP_SECRET"
        secret_name = "mcp-secret"
      }
      env {
        name        = "GITHUB_TOKEN"
        secret_name = "github-token"
      }

      liveness_probe {
        transport = "HTTP"
        path      = "/health"
        port      = 8000
        initial_delay = 30
        interval_seconds = 30
      }
    }

    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = "50"
    }
  }

  secret {
    name  = "openai-api-key"
    key_vault_secret_id = module.keyvault.secret_ids["openai-api-key"]
    identity = azurerm_user_assigned_identity.app.id
  }
  secret {
    name  = "mcp-secret"
    key_vault_secret_id = module.keyvault.secret_ids["mcp-secret"]
    identity = azurerm_user_assigned_identity.app.id
  }
  secret {
    name  = "github-token"
    key_vault_secret_id = module.keyvault.secret_ids["github-token"]
    identity = azurerm_user_assigned_identity.app.id
  }
}

# ── Web Container App ─────────────────────────────────────────────────────────

resource "azurerm_container_app" "web" {
  name                         = "${local.name_prefix}-web"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  registry {
    server   = module.acr.login_server
    identity = azurerm_user_assigned_identity.app.id
  }

  ingress {
    external_enabled = true
    target_port      = 3000
    transport        = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 1
    max_replicas = 3

    container {
      name   = "web"
      image  = "${module.acr.login_server}/forgeops-web:${var.image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "NEXT_PUBLIC_API_URL"
        value = "https://${azurerm_container_app.api.latest_revision_fqdn}"
      }
      env {
        name  = "NODE_ENV"
        value = "production"
      }
    }
  }
}
