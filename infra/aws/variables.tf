# ── Required ──────────────────────────────────────────────────────────────────

variable "aws_region" {
  type    = string
  default = "eu-west-1"
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
  type        = string
  description = "Docker image tag to deploy (typically a git SHA)"
  default     = "latest"
}

variable "domain" {
  type        = string
  description = "Public domain name for the application (e.g. forgeops.example.com)"
}

variable "acm_certificate_arn" {
  type        = string
  description = "ARN of the ACM certificate for the domain"
}

# ── Secrets (never commit defaults; inject via CI/CD or AWS Secrets Manager) ──

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

# ── Network ───────────────────────────────────────────────────────────────────

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

# ── Compute sizing ────────────────────────────────────────────────────────────

variable "rds_instance_class" {
  type    = string
  default = "db.t4g.medium"
}

variable "redis_node_type" {
  type    = string
  default = "cache.t4g.small"
}

variable "api_desired_count" {
  type    = number
  default = 2
}

variable "web_desired_count" {
  type    = number
  default = 1
}
