# ForgeOps — Deployment Guide

ForgeOps runs identically on AWS and Azure. The application is cloud-agnostic.
Only the infrastructure layer differs.

---

## Local development

```bash
cp .env.example .env        # fill in OPENAI_API_KEY at minimum
docker compose up -d        # starts postgres, redis, api, web, mcp servers
open http://localhost:3000   # Mission Control UI
open http://localhost:8000/docs  # API docs
```

---

## AWS deployment

### Prerequisites
- Terraform 1.7+
- AWS CLI configured with a deployment role
- An ACM certificate for your domain
- A Route 53 hosted zone

### First deploy

```bash
cd infra/aws

# Create terraform.tfvars (never commit this)
cat > terraform.tfvars <<EOF
aws_region          = "eu-west-1"
environment         = "staging"
domain              = "forgeops.example.com"
acm_certificate_arn = "arn:aws:acm:eu-west-1:123456789:certificate/..."
db_password         = "$(openssl rand -base64 24)"
openai_api_key      = "sk-..."
mcp_secret          = "$(openssl rand -hex 32)"
github_token        = "ghp_..."
EOF

terraform init
terraform plan
terraform apply
```

### Push images and deploy

```bash
# Get registry URL from Terraform output
ECR_URL=$(terraform output -raw ecr_repository_urls | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['api'])" | cut -d: -f1)

# Authenticate
aws ecr get-login-password --region eu-west-1 | \
  docker login --username AWS --password-stdin $ECR_URL

# Build and push
for svc in api web mcp-github mcp-data mcp-knowledge; do
  docker build -t $ECR_URL/forgeops-$svc:latest .
  docker push $ECR_URL/forgeops-$svc:latest
done

# Force ECS redeployment
aws ecs update-service --cluster forgeops-staging-cluster \
  --service forgeops-staging-api --force-new-deployment
```

### CI/CD (GitHub Actions)

Set these **repository secrets**:
```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
OPENAI_API_KEY          (used in test runner)
```

Set these **repository variables**:
```
DEPLOY_TARGET   = aws
AWS_REGION      = eu-west-1
ECS_CLUSTER     = forgeops-staging-cluster
APP_DOMAIN      = forgeops.example.com
DEPLOY_ENVIRONMENT = staging
```

Every push to `main` will test → build → push → deploy automatically.

---

## Azure deployment

### Prerequisites
- Terraform 1.7+
- Azure CLI (`az login`)
- A service principal for CI/CD

### First deploy

```bash
cd infra/azure

cat > terraform.tfvars <<EOF
location       = "westeurope"
environment    = "staging"
domain         = "forgeops.example.com"
db_password    = "$(openssl rand -base64 24)"
openai_api_key = "sk-..."
mcp_secret     = "$(openssl rand -hex 32)"
github_token   = "ghp_..."
EOF

terraform init
terraform plan
terraform apply
```

### Push images and deploy

```bash
ACR=$(terraform output -raw acr_login_server)
az acr login --name $(echo $ACR | cut -d. -f1)

for svc in api web mcp-github mcp-data mcp-knowledge; do
  docker build -t $ACR/forgeops-$svc:latest .
  docker push $ACR/forgeops-$svc:latest
done

# Update container apps
az containerapp update \
  --name forgeops-staging-api \
  --resource-group forgeops-staging-rg \
  --image $ACR/forgeops-api:latest
```

### CI/CD (GitHub Actions)

Set these **repository secrets**:
```
AZURE_CREDENTIALS   (JSON output of: az ad sp create-for-rbac --sdk-auth)
OPENAI_API_KEY
```

Set these **repository variables**:
```
DEPLOY_TARGET        = azure
ACR_NAME             = forgeops<env>acr
ACR_LOGIN_SERVER     = forgeops<env>acr.azurecr.io
DEPLOY_ENVIRONMENT   = staging
```

---

## Environment variables reference

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | Primary LLM |
| `ANTHROPIC_API_KEY` | No | Fallback LLM |
| `DATABASE_URL` | Yes | PostgreSQL async URL |
| `REDIS_URL` | Yes | Redis URL |
| `MCP_SECRET` | Yes | Shared secret for MCP servers |
| `GITHUB_TOKEN` | No | GitHub API token for repo tools |
| `LANGFUSE_PUBLIC_KEY` | No | LLM trace observability |
| `LANGFUSE_SECRET_KEY` | No | LLM trace observability |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | OTEL traces (Grafana Tempo etc.) |
| `LOG_LEVEL` | No | Default: INFO |
| `ENVIRONMENT` | No | development/staging/production |

---

## Architecture: AWS vs Azure

```
                     AWS                          Azure
              ─────────────────            ─────────────────────
 Containers   ECS Fargate                  Container Apps
 Registry     ECR                          Azure Container Registry
 Database     RDS PostgreSQL 16            PostgreSQL Flexible Server 16
 Cache        ElastiCache Redis 7          Azure Cache for Redis
 Secrets      SSM Parameter Store          Azure Key Vault
 Load bal.    Application Load Balancer    Container Apps built-in HTTPS
 Logs         CloudWatch                   Log Analytics / Azure Monitor
 TLS          ACM                          Managed certificate (auto)
 Identity     IAM Roles                    Managed Identity
 IaC state    S3 + DynamoDB (optional)     Azure Blob (optional)
```

Application code is identical for both targets.
Only `infra/aws/` vs `infra/azure/` differs.
