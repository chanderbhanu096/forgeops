variable "name_prefix"        { type = string }
variable "service_name"       { type = string }
variable "cluster_arn"        { type = string }
variable "vpc_id"             { type = string }
variable "subnet_ids"         { type = list(string) }
variable "image_uri"          { type = string }
variable "cpu" {
  type    = number
  default = 512
}
variable "memory" {
  type    = number
  default = 1024
}
variable "desired_count" {
  type    = number
  default = 1
}
variable "task_role_arn"      { type = string }
variable "execution_role_arn" { type = string }
variable "log_group_name"     { type = string }
variable "aws_region"         { type = string }
variable "container_port"     { type = number }
variable "target_group_arn"   { type = string }
variable "alb_sg_id"          { type = string }
variable "environment_vars" {
  type    = list(object({ name = string, value = string }))
  default = []
}
variable "secrets" {
  type    = list(object({ name = string, valueFrom = string }))
  default = []
}

locals {
  full_name = "${var.name_prefix}-${var.service_name}"
}

resource "aws_security_group" "task" {
  name   = "${local.full_name}-task-sg"
  vpc_id = var.vpc_id

  ingress {
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [var.alb_sg_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_ecs_task_definition" "main" {
  family                   = local.full_name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  task_role_arn            = var.task_role_arn
  execution_role_arn       = var.execution_role_arn

  container_definitions = jsonencode([{
    name      = var.service_name
    image     = var.image_uri
    essential = true

    portMappings = [{
      containerPort = var.container_port
      protocol      = "tcp"
    }]

    environment = var.environment_vars
    secrets     = var.secrets

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = var.log_group_name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = var.service_name
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:${var.container_port}/health')\" || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])

  lifecycle { create_before_destroy = true }
}

resource "aws_ecs_service" "main" {
  name                               = local.full_name
  cluster                            = var.cluster_arn
  task_definition                    = aws_ecs_task_definition.main.arn
  desired_count                      = var.desired_count
  launch_type                        = "FARGATE"
  platform_version                   = "LATEST"
  health_check_grace_period_seconds  = 60

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [aws_security_group.task.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = var.service_name
    container_port   = var.container_port
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  deployment_controller { type = "ECS" }

  lifecycle { ignore_changes = [desired_count] }
}

output "task_sg_id"       { value = aws_security_group.task.id }
output "service_name"     { value = aws_ecs_service.main.name }
output "task_definition"  { value = aws_ecs_task_definition.main.arn }
