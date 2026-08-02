# ForgeOps — root Terraform configuration
#
# What this creates:
#   VPC (2 AZ, public + private subnets)
#   ECR repositories (api, web, mcp-github, mcp-data, mcp-knowledge)
#   RDS PostgreSQL 16 (Multi-AZ optional, pgvector extension enabled)
#   ElastiCache Redis 7 (single-node, upgradeable to cluster)
#   ECS Cluster (Fargate)
#   Application Load Balancer (HTTPS, ACM cert)
#   ECS Services: api, web, mcp-github, mcp-data, mcp-knowledge
#   SSM Parameter Store for secrets
#   CloudWatch log groups
#   IAM roles for task execution and task
#   Security groups with least-privilege rules

terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }

  # Uncomment for remote state (recommended for team use)
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket"
  #   key            = "forgeops/terraform.tfstate"
  #   region         = "eu-west-1"
  #   dynamodb_table = "terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "forgeops"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ── Data sources ──────────────────────────────────────────────────────────────

data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" { state = "available" }

locals {
  account_id = data.aws_caller_identity.current.account_id
  azs        = slice(data.aws_availability_zones.available.names, 0, 2)
  name_prefix = "${var.project}-${var.environment}"
}

# ── VPC ───────────────────────────────────────────────────────────────────────

module "vpc" {
  source = "./modules/vpc"

  name_prefix = local.name_prefix
  cidr        = var.vpc_cidr
  azs         = local.azs
}

# ── ECR repositories ──────────────────────────────────────────────────────────

module "ecr" {
  source = "./modules/ecr"

  name_prefix  = local.name_prefix
  repositories = ["api", "web", "mcp-github", "mcp-data", "mcp-knowledge"]
}

# ── RDS PostgreSQL ────────────────────────────────────────────────────────────

module "rds" {
  source = "./modules/rds"

  name_prefix        = local.name_prefix
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  allowed_sg_ids     = [module.ecs_api.task_sg_id]
  db_name            = "forgeops"
  instance_class     = var.rds_instance_class
  multi_az           = var.environment == "production"
  db_password_ssm    = aws_ssm_parameter.db_password.name
}

# ── ElastiCache Redis ─────────────────────────────────────────────────────────

module "elasticache" {
  source = "./modules/elasticache"

  name_prefix    = local.name_prefix
  vpc_id         = module.vpc.vpc_id
  subnet_ids     = module.vpc.private_subnet_ids
  allowed_sg_ids = [module.ecs_api.task_sg_id]
  node_type      = var.redis_node_type
}

# ── Application Load Balancer ─────────────────────────────────────────────────

module "alb" {
  source = "./modules/alb"

  name_prefix       = local.name_prefix
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  certificate_arn   = var.acm_certificate_arn
  domain            = var.domain
}

# ── ECS Cluster ───────────────────────────────────────────────────────────────

resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name       = aws_ecs_cluster.main.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = "FARGATE"
  }
}

# ── IAM roles ─────────────────────────────────────────────────────────────────

resource "aws_iam_role" "ecs_task_execution" {
  name = "${local.name_prefix}-ecs-task-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "task_execution_managed" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ssm_read" {
  name = "ssm-read"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["ssm:GetParameters", "ssm:GetParameter"]
      Resource = "arn:aws:ssm:${var.aws_region}:${local.account_id}:parameter/${local.name_prefix}/*"
    }]
  })
}

resource "aws_iam_role" "ecs_task" {
  name = "${local.name_prefix}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "task_cloudwatch" {
  name = "cloudwatch-logs"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "arn:aws:logs:${var.aws_region}:${local.account_id}:log-group:/forgeops/*:*"
    }]
  })
}

# ── SSM Parameters (secrets) ──────────────────────────────────────────────────

resource "aws_ssm_parameter" "db_password" {
  name  = "/${local.name_prefix}/db-password"
  type  = "SecureString"
  value = var.db_password

  lifecycle { ignore_changes = [value] }
}

resource "aws_ssm_parameter" "openai_api_key" {
  name  = "/${local.name_prefix}/openai-api-key"
  type  = "SecureString"
  value = var.openai_api_key

  lifecycle { ignore_changes = [value] }
}

resource "aws_ssm_parameter" "mcp_secret" {
  name  = "/${local.name_prefix}/mcp-secret"
  type  = "SecureString"
  value = var.mcp_secret

  lifecycle { ignore_changes = [value] }
}

resource "aws_ssm_parameter" "github_token" {
  name  = "/${local.name_prefix}/github-token"
  type  = "SecureString"
  value = var.github_token

  lifecycle { ignore_changes = [value] }
}

# ── CloudWatch log groups ─────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "api" {
  name              = "/forgeops/${var.environment}/api"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "web" {
  name              = "/forgeops/${var.environment}/web"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "mcp" {
  for_each          = toset(["mcp-github", "mcp-data", "mcp-knowledge"])
  name              = "/forgeops/${var.environment}/${each.key}"
  retention_in_days = 14
}

# ── ECS Services ──────────────────────────────────────────────────────────────

module "ecs_api" {
  source = "./modules/ecs-service"

  name_prefix        = local.name_prefix
  service_name       = "api"
  cluster_arn        = aws_ecs_cluster.main.arn
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  image_uri          = "${module.ecr.repository_urls["api"]}:${var.image_tag}"
  cpu                = 1024
  memory             = 2048
  desired_count      = var.api_desired_count
  task_role_arn      = aws_iam_role.ecs_task.arn
  execution_role_arn = aws_iam_role.ecs_task_execution.arn
  log_group_name     = aws_cloudwatch_log_group.api.name
  aws_region         = var.aws_region

  target_group_arn   = module.alb.api_target_group_arn
  container_port     = 8000

  environment_vars = [
    { name = "ENVIRONMENT",              value = var.environment },
    { name = "LOG_LEVEL",                value = "INFO" },
    { name = "REDIS_URL",                value = "redis://${module.elasticache.primary_endpoint}:6379" },
  ]

  secrets = [
    { name = "DATABASE_URL",   valueFrom = "${aws_ssm_parameter.db_password.arn}" },
    { name = "OPENAI_API_KEY", valueFrom = "${aws_ssm_parameter.openai_api_key.arn}" },
    { name = "MCP_SECRET",     valueFrom = "${aws_ssm_parameter.mcp_secret.arn}" },
    { name = "GITHUB_TOKEN",   valueFrom = "${aws_ssm_parameter.github_token.arn}" },
  ]

  # Internal-only — API is not directly internet-facing
  alb_sg_id = module.alb.security_group_id
}

module "ecs_web" {
  source = "./modules/ecs-service"

  name_prefix        = local.name_prefix
  service_name       = "web"
  cluster_arn        = aws_ecs_cluster.main.arn
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  image_uri          = "${module.ecr.repository_urls["web"]}:${var.image_tag}"
  cpu                = 512
  memory             = 1024
  desired_count      = var.web_desired_count
  task_role_arn      = aws_iam_role.ecs_task.arn
  execution_role_arn = aws_iam_role.ecs_task_execution.arn
  log_group_name     = aws_cloudwatch_log_group.web.name
  aws_region         = var.aws_region

  target_group_arn = module.alb.web_target_group_arn
  container_port   = 3000

  environment_vars = [
    { name = "NEXT_PUBLIC_API_URL", value = "https://${var.domain}" },
    { name = "NEXT_PUBLIC_WS_URL",  value = "wss://${var.domain}" },
    { name = "NODE_ENV",            value = "production" },
  ]
  secrets     = []
  alb_sg_id   = module.alb.security_group_id
}
