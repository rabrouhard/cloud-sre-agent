# RUNBOOK-Application-Error-SRE-Agent

## Purpose
SRE guidance for application errors detected through CloudWatch alarms, metric filters, Logs, synthetics, and application metrics.

## Safety Rules
- Do not deploy, rollback, restart services, change feature flags, routing, or dependencies automatically.
- Require approval for behavior, data, routing, capacity, or customer experience changes.
- Summarize log patterns without exposing secrets, PII, tokens, or full stack traces.

## Agent Output Format
Summary, Likely Cause, Confidence, Business Impact, Observed Evidence, Recommended Triage, Suggested Remediation, Human Approval Required, Rollback, Verification, ServiceNow Priority, Escalation.

## Common Context to Gather
Alarm details, app metric datapoints, log groups, recent error samples, log streams, deployment timing if available, request/error rate, latency, 4XX/5XX, canary failures, related infra/database alarms.

## Severity Model
Critical: widespread outage, sustained 5XX, critical path failure. High: elevated production errors, high latency, timeouts, canary failure. Medium: moderate partial impact. Low: transient isolated.

## ServiceNow Incident Guidance
Create incidents for Medium or higher severity, production impact, critical endpoint failure, canary failure, repeated spikes, customer degradation.

## Human Approval Matrix
No approval: read logs, summarize, incident, email, audit. Approval: rollback, deploy, restart, feature flag, routing, scale.

## Agent Decision Rules
Prioritize customer-facing 5XX, timeouts, critical transaction failures, canary failures, non-critical background errors.

## Application Error Rate
### Immediate Triage
Check error rate, affected service, samples, deployments, dependency errors, infra/database alarms.
### Suggested Remediation
Ask app owner to review changes, top exceptions, dependency health. Rollback/restart requires approval.

## Application Exceptions
### Immediate Triage
Group by exception class/message, affected endpoint/job, first-seen time, frequency, version.
### Suggested Remediation
Bug triage, rollback if deploy-related, defensive handling if dependency-related. Code/rollback requires approval.

## Application 5XX Errors
### Immediate Triage
Check whether 5XX is app or load balancer generated. Review logs, target health, dependencies, database health.
### Suggested Remediation
Rollback if deploy-correlated, dependency failover if approved, scale if saturation. Requires approval.

## Application 4XX Errors
### Immediate Triage
Determine expected client behavior vs auth failure, bad release, routing issue, API contract break.
### Suggested Remediation
Check auth providers, API changes, client deployment, validation. Config/routing/code changes require approval.

## Application Latency
### Immediate Triage
Check p95/p99 latency, request count, error rate, slow endpoints, DB/dependency latency, infra saturation.
### Suggested Remediation
Identify bottleneck by endpoint/dependency. Scaling, rollback, caching or DB changes require approval.

## Application Timeouts
### Immediate Triage
Identify inbound, outbound dependency, database, queue processing, background job.
### Suggested Remediation
Check dependency health, DB, circuit breakers/retries, queue backlog. Timeout/restart changes require approval.

## Failed Requests
### Immediate Triage
Scope by endpoint, customer segment, region, version, dependency.
### Suggested Remediation
Correlate with release/dependency. Rollback/hotfix requires approval.

## CloudWatch Log Error Pattern
### Immediate Triage
Review recent matched logs, group by message, first occurrence, affected streams, secret/PII risk.
### Suggested Remediation
App team review code path, deployment correlation, dependency failures. Do not paste full sensitive logs.

## Synthetic Canary Failure
### Immediate Triage
Check failing step, artifact, endpoint, DNS/TLS, auth, regional scope.
### Suggested Remediation
Endpoint validation and app owner escalation. Disabling canary/routing/rollback requires approval.
