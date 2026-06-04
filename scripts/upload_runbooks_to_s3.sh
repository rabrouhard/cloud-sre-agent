#!/usr/bin/env bash
set -euo pipefail
AWS_REGION="${AWS_REGION:-us-gov-west-1}"
: "${RUNBOOK_BUCKET_NAME:?Set RUNBOOK_BUCKET_NAME}"
aws s3 cp runbooks/database_runbook.md "s3://${RUNBOOK_BUCKET_NAME}/runbooks/database_runbook.md" --region "${AWS_REGION}"
aws s3 cp runbooks/infrastructure_runbook.md "s3://${RUNBOOK_BUCKET_NAME}/runbooks/infrastructure_runbook.md" --region "${AWS_REGION}"
aws s3 cp runbooks/application_runbook.md "s3://${RUNBOOK_BUCKET_NAME}/runbooks/application_runbook.md" --region "${AWS_REGION}"
echo "Uploaded runbooks to s3://${RUNBOOK_BUCKET_NAME}/runbooks/"
