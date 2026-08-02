variable "name_prefix"     { type = string }
variable "vpc_id"          { type = string }
variable "subnet_ids"      { type = list(string) }
variable "allowed_sg_ids"  { type = list(string) }
variable "db_name"         { type = string }
variable "instance_class" {
  type    = string
  default = "db.t4g.medium"
}
variable "multi_az" {
  type    = bool
  default = false
}
variable "db_password_ssm" { type = string }

resource "aws_db_subnet_group" "main" {
  name       = "${var.name_prefix}-db-subnet"
  subnet_ids = var.subnet_ids
}

resource "aws_security_group" "rds" {
  name   = "${var.name_prefix}-rds-sg"
  vpc_id = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = var.allowed_sg_ids
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

data "aws_ssm_parameter" "db_password" {
  name            = var.db_password_ssm
  with_decryption = true
}

resource "aws_db_parameter_group" "postgres16" {
  name   = "${var.name_prefix}-pg16"
  family = "postgres16"

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }
}

resource "aws_db_instance" "main" {
  identifier              = "${var.name_prefix}-postgres"
  engine                  = "postgres"
  engine_version          = "16"
  instance_class          = var.instance_class
  allocated_storage       = 50
  max_allocated_storage   = 200
  storage_type            = "gp3"
  storage_encrypted       = true
  db_name                 = var.db_name
  username                = "forgeops"
  password                = data.aws_ssm_parameter.db_password.value
  db_subnet_group_name    = aws_db_subnet_group.main.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  parameter_group_name    = aws_db_parameter_group.postgres16.name
  multi_az                = var.multi_az
  backup_retention_period = 7
  skip_final_snapshot     = false
  final_snapshot_identifier = "${var.name_prefix}-final-snapshot"
  deletion_protection     = true
  apply_immediately       = false

  lifecycle { prevent_destroy = true }
}

output "endpoint" { value = aws_db_instance.main.endpoint }
output "sg_id"    { value = aws_security_group.rds.id }
