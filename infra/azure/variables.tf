variable "location" {
  type    = string
  default = "westeurope"
}

variable "environment" {
  type    = string
  default = "staging"
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production"
  }
}

variable "project" {
  type    = string
  default = "forgeops"
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "domain" {
  type        = string
  description = "Custom domain for the app (e.g. forgeops.example.com)"
  default     = ""
}

# Secrets — inject via CI/CD, never commit defaults
variable "db_password" {
  type      = string
  sensitive = true
}

variable "openai_api_key" {
  type      = string
  sensitive = true
}

variable "mcp_secret" {
  type      = string
  sensitive = true
}

variable "github_token" {
  type      = string
  sensitive = true
  default   = ""
}

# Sizing
variable "postgres_sku" {
  type    = string
  default = "B_Standard_B2ms"
}

variable "redis_capacity" {
  type    = number
  default = 1   # 1 GB
}

variable "api_min_replicas" {
  type    = number
  default = 1
}

variable "api_max_replicas" {
  type    = number
  default = 5
}
