# Aurora DBA + SRE CloudWatch Alarm Agent

This is a VS Code-ready Python and Terraform solution for an AWS GovCloud-compatible advisory agent.

The solution handles three alarm domains:

```text
1. Aurora PostgreSQL DBA alarms
2. General infrastructure SRE alarms
3. Application error/log alarms
```

The agent runs as a private ECS/Fargate task with two containers:

```text
agent container      - polls SQS, classifies alarms, calls Claude, coordinates workflow
mcp-server sidecar   - exposes controlled tools for context, runbooks, email, ServiceNow, audit logs
```

All runbooks are stored in and retrieved from a common S3 bucket at runtime.

## Flow

```text
CloudWatch Alarm
 → EventBridge
 → SQS
 → ECS/Fargate Agent
 → classify domain: database | infrastructure | application
 → MCP sidecar context tool
 → MCP sidecar S3 runbook tool
 → Bedrock Claude analysis
 → ServiceNow incident
 → SMTP email
 → S3 audit log
```

## Included runbooks

```text
runbooks/database_runbook.md
runbooks/infrastructure_runbook.md
runbooks/application_runbook.md
```

Upload them to the common S3 bucket:

```bash
export AWS_REGION=us-gov-west-1
export RUNBOOK_BUCKET_NAME=your-common-runbook-bucket
bash scripts/upload_runbooks_to_s3.sh
```

## Runtime configuration

All runtime configuration and credentials are stored in SSM Parameter Store as SecureString.

```bash
export AWS_REGION=us-gov-west-1
export PARAMETER_PREFIX=/aurora-sre-agent

export RUNBOOK_BUCKET_NAME=your-common-runbook-bucket
export ALARM_QUEUE_URL=https://sqs.us-gov-west-1.amazonaws.com/ACCOUNT/QUEUE
export AUDIT_BUCKET_NAME=your-audit-bucket
export DYNAMODB_TABLE_NAME=aurora-sre-agent-idempotency

export SMTP_HOST=smtp.example.mil
export SMTP_SENDER=dba-sre-agent@example.mil
export SMTP_DEFAULT_RECIPIENTS=dba-oncall@example.mil,sre-oncall@example.mil

export SERVICENOW_INSTANCE_URL=https://your-instance.service-now.com
export SERVICENOW_BEARER_TOKEN=...
export SERVICENOW_ASSIGNMENT_GROUP=...
export SERVICENOW_CMDB_CI=...

export BEDROCK_MODEL_ID=anthropic.claude-3-7-sonnet-20250219-v1:0

export ALLOWED_ACCOUNT_IDS_JSON='["123456789012"]'
export ALLOWED_REGIONS_JSON='["us-gov-west-1"]'
export ALLOWED_ALARM_NAME_PATTERNS_JSON='["prod-*","aurora-*","app-*","infra-*"]'

bash scripts/put_secure_params.sh
```

## Terraform

Terraform provisions:

```text
ECS cluster/service/task definition
Agent + MCP sidecar containers
SQS queue and DLQ
EventBridge rule
S3 audit bucket
DynamoDB idempotency table
KMS key
IAM task roles and policies
CloudWatch log groups
```

It assumes you already have:

```text
Existing VPC
Existing private subnets
Existing private network access/VPC endpoints/NAT/proxy as required
Existing common S3 runbook bucket
Container images already pushed to ECR
```

Example:

```bash
cd terraform
terraform init
terraform plan \
  -var 'vpc_id=vpc-xxxx' \
  -var 'private_subnet_ids=["subnet-a","subnet-b"]' \
  -var 'agent_image=ACCOUNT.dkr.ecr.us-gov-west-1.amazonaws.com/agent:latest' \
  -var 'mcp_image=ACCOUNT.dkr.ecr.us-gov-west-1.amazonaws.com/mcp:latest' \
  -var 'runbook_bucket_name=your-common-runbook-bucket'
```

## Safety model

The solution is advisory-only.

It can:

```text
Read AWS context
Read CloudWatch Logs
Read S3 runbooks
Call Bedrock Claude
Create ServiceNow incidents
Send SMTP email
Write S3 audit logs
```

It must not autonomously:

```text
restart/reboot/failover/scale resources
modify database parameters
execute SQL
kill sessions
deploy/rollback applications
change feature flags
modify security groups, routing, IAM, or load balancer rules
```

## Development

```bash
pip install -r requirements.txt
pytest
```

## Notes

The MCP sidecar retrieves S3 runbooks and caches them under `/tmp/runbooks`.
It checks S3 ETag/VersionId every `runbooks/refresh_interval_seconds` seconds.
The S3 audit log records the runbook bucket/key/ETag/VersionId used for each recommendation.
