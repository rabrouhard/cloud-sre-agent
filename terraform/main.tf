provider "aws" { region = var.aws_region }
data "aws_caller_identity" "current" {}

resource "aws_kms_key" "agent" {
  description             = "${var.name_prefix} encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

resource "aws_sqs_queue" "dlq" {
  name                      = "${var.name_prefix}-dlq"
  kms_master_key_id         = aws_kms_key.agent.arn
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "alarm_queue" {
  name                       = "${var.name_prefix}-alarm-queue"
  kms_master_key_id          = aws_kms_key.agent.arn
  visibility_timeout_seconds = 900
  message_retention_seconds  = 1209600
  redrive_policy = jsonencode({ deadLetterTargetArn = aws_sqs_queue.dlq.arn, maxReceiveCount = 5 })
}

resource "aws_s3_bucket" "audit" { bucket = "${var.name_prefix}-audit-${data.aws_caller_identity.current.account_id}" }

resource "aws_s3_bucket_server_side_encryption_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id
  rule { apply_server_side_encryption_by_default { kms_master_key_id = aws_kms_key.agent.arn, sse_algorithm = "aws:kms" } }
}

resource "aws_s3_bucket_public_access_block" "audit" {
  bucket = aws_s3_bucket.audit.id
  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "idempotency" {
  name         = "${var.name_prefix}-idempotency"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"
  attribute { name = "pk" type = "S" }
  attribute { name = "sk" type = "S" }
  ttl { attribute_name = "expires_at" enabled = true }
  server_side_encryption { enabled = true kms_key_arn = aws_kms_key.agent.arn }
}

resource "aws_cloudwatch_event_rule" "cloudwatch_alarms" {
  name        = "${var.name_prefix}-cloudwatch-alarms"
  description = "CloudWatch alarm events for DBA/SRE agent"
  event_pattern = jsonencode({ source = ["aws.cloudwatch"], detail-type = ["CloudWatch Alarm State Change"], detail = { state = { value = ["ALARM", "OK"] } } })
}

resource "aws_cloudwatch_event_target" "sqs" {
  rule      = aws_cloudwatch_event_rule.cloudwatch_alarms.name
  target_id = "alarmQueue"
  arn       = aws_sqs_queue.alarm_queue.arn
}

data "aws_iam_policy_document" "sqs_eventbridge" {
  statement {
    actions = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.alarm_queue.arn]
    principals { type = "Service" identifiers = ["events.amazonaws.com"] }
    condition { test = "ArnEquals" variable = "aws:SourceArn" values = [aws_cloudwatch_event_rule.cloudwatch_alarms.arn] }
  }
}

resource "aws_sqs_queue_policy" "alarm_queue" {
  queue_url = aws_sqs_queue.alarm_queue.id
  policy    = data.aws_iam_policy_document.sqs_eventbridge.json
}

resource "aws_ecs_cluster" "this" { name = var.name_prefix }

resource "aws_security_group" "ecs_task" {
  name = "${var.name_prefix}-ecs-task"
  description = "No ingress; egress only through existing VPC controls"
  vpc_id = var.vpc_id
  egress { from_port = 0 to_port = 0 protocol = "-1" cidr_blocks = ["0.0.0.0/0"] }
}

resource "aws_cloudwatch_log_group" "agent" { name = "/ecs/${var.name_prefix}/agent" retention_in_days = 30 kms_key_id = aws_kms_key.agent.arn }
resource "aws_cloudwatch_log_group" "mcp" { name = "/ecs/${var.name_prefix}/mcp" retention_in_days = 30 kms_key_id = aws_kms_key.agent.arn }

resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.name_prefix}-execution-role"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy_attachment" "execution" {
  role = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws-us-gov:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task_role" {
  name = "${var.name_prefix}-task-role"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}

data "aws_iam_policy_document" "task" {
  statement { sid = "QueueAccess" actions = ["sqs:ReceiveMessage","sqs:DeleteMessage","sqs:ChangeMessageVisibility","sqs:GetQueueAttributes"] resources = [aws_sqs_queue.alarm_queue.arn] }
  statement { sid = "ReadSsmSecureConfig" actions = ["ssm:GetParameter"] resources = ["arn:aws-us-gov:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.parameter_prefix}/*"] }
  statement { sid = "DecryptConfigAndData" actions = ["kms:Decrypt","kms:GenerateDataKey"] resources = compact([aws_kms_key.agent.arn, var.runbook_kms_key_arn]) }
  statement {
    sid = "ReadRunbooksFromS3"
    actions = ["s3:GetObject","s3:GetObjectVersion","s3:HeadObject"]
    resources = [
      "arn:aws-us-gov:s3:::${var.runbook_bucket_name}/${var.runbook_database_key}",
      "arn:aws-us-gov:s3:::${var.runbook_bucket_name}/${var.runbook_infrastructure_key}",
      "arn:aws-us-gov:s3:::${var.runbook_bucket_name}/${var.runbook_application_key}"
    ]
  }
  statement { sid = "WriteAuditLogs" actions = ["s3:PutObject"] resources = ["${aws_s3_bucket.audit.arn}/*"] }
  statement { sid = "IdempotencyTable" actions = ["dynamodb:PutItem","dynamodb:GetItem","dynamodb:UpdateItem"] resources = [aws_dynamodb_table.idempotency.arn] }
  statement { sid = "CloudWatchRead" actions = ["cloudwatch:GetMetricStatistics","cloudwatch:GetMetricData","cloudwatch:DescribeAlarms","logs:FilterLogEvents","logs:DescribeLogGroups","logs:DescribeLogStreams"] resources = ["*"] }
  statement { sid = "AwsContextReadOnly" actions = ["rds:DescribeDBClusters","rds:DescribeDBInstances","rds:DescribeEvents","ec2:DescribeInstances","ec2:DescribeInstanceStatus","elasticloadbalancing:Describe*","ecs:DescribeServices","ecs:DescribeClusters","ecs:DescribeTasks","autoscaling:DescribeAutoScalingGroups","autoscaling:DescribeScalingActivities","lambda:GetFunctionConfiguration"] resources = ["*"] }
  statement { sid = "BedrockInvoke" actions = ["bedrock:InvokeModel"] resources = ["*"] }
}
resource "aws_iam_policy" "task" { name = "${var.name_prefix}-task-policy" policy = data.aws_iam_policy_document.task.json }
resource "aws_iam_role_policy_attachment" "task" { role = aws_iam_role.ecs_task_role.name policy_arn = aws_iam_policy.task.arn }

resource "aws_ecs_task_definition" "this" {
  family = var.name_prefix
  requires_compatibilities = ["FARGATE"]
  network_mode = "awsvpc"
  cpu = "1024"
  memory = "2048"
  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn = aws_iam_role.ecs_task_role.arn
  container_definitions = jsonencode([
    {
      name = "mcp-server", image = var.mcp_image, essential = true,
      portMappings = [{ containerPort = 8000, hostPort = 8000, protocol = "tcp" }],
      environment = [{ name = "AWS_REGION", value = var.aws_region },{ name = "PARAMETER_PREFIX", value = var.parameter_prefix },{ name = "MCP_PORT", value = "8000" }],
      logConfiguration = { logDriver = "awslogs", options = { awslogs-group = aws_cloudwatch_log_group.mcp.name, awslogs-region = var.aws_region, awslogs-stream-prefix = "mcp" } }
    },
    {
      name = "agent", image = var.agent_image, essential = true,
      dependsOn = [{ containerName = "mcp-server", condition = "START" }],
      environment = [{ name = "AWS_REGION", value = var.aws_region },{ name = "PARAMETER_PREFIX", value = var.parameter_prefix }],
      logConfiguration = { logDriver = "awslogs", options = { awslogs-group = aws_cloudwatch_log_group.agent.name, awslogs-region = var.aws_region, awslogs-stream-prefix = "agent" } }
    }
  ])
}

resource "aws_ecs_service" "this" {
  name = var.name_prefix
  cluster = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.this.arn
  desired_count = var.desired_count
  launch_type = "FARGATE"
  network_configuration { subnets = var.private_subnet_ids security_groups = [aws_security_group.ecs_task.id] assign_public_ip = false }
}
output "alarm_queue_url" { value = aws_sqs_queue.alarm_queue.url }
output "audit_bucket" { value = aws_s3_bucket.audit.bucket }
output "idempotency_table" { value = aws_dynamodb_table.idempotency.name }
