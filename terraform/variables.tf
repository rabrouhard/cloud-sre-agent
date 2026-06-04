variable "aws_region" { type = string default = "us-gov-west-1" }
variable "name_prefix" { type = string default = "aurora-sre-agent" }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "agent_image" { type = string }
variable "mcp_image" { type = string }
variable "parameter_prefix" { type = string default = "/aurora-sre-agent" }
variable "runbook_bucket_name" { type = string }
variable "runbook_database_key" { type = string default = "runbooks/database_runbook.md" }
variable "runbook_infrastructure_key" { type = string default = "runbooks/infrastructure_runbook.md" }
variable "runbook_application_key" { type = string default = "runbooks/application_runbook.md" }
variable "runbook_kms_key_arn" { type = string default = null }
variable "desired_count" { type = number default = 1 }
