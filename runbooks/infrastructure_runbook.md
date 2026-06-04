# RUNBOOK-Infrastructure-SRE-Agent

## Purpose
SRE guidance for infrastructure CloudWatch alarms across EC2, ECS, load balancers, Auto Scaling, Lambda, network, disk, memory, and throttling.

## Safety Rules
- Do not terminate, reboot, replace, scale, detach, drain, or modify infrastructure automatically.
- Require human approval for availability, capacity, cost, routing, security group, IAM, or network path changes.
- Prefer diagnostics and impact assessment before disruptive action.

## Agent Output Format
Summary, Likely Cause, Confidence, Business Impact, Observed Evidence, Recommended Triage, Suggested Remediation, Human Approval Required, Rollback, Verification, ServiceNow Priority, Escalation.

## Common Context to Gather
Alarm details, namespace, metric, dimensions, datapoints, EC2 state/type, ECS desired/running/pending counts, LB target health, ASG desired/min/max, Lambda errors/throttles/duration.

## Severity Model
Critical: production outage, all targets unhealthy, capacity unavailable. High: major latency, 5XX, repeated status failures. Medium: single degraded host, moderate latency. Low: transient non-production.

## ServiceNow Incident Guidance
Create incidents for Medium or higher severity, production impact, all-target failure, capacity shortfall, or service degradation.

## Human Approval Matrix
No approval: metrics/status, incident, email, audit. Approval: reboot/terminate, change capacity, drain task, modify routing, change SG/NACL/IAM.

## Agent Decision Rules
Prioritize customer impact, availability, capacity, latency, error rates, optimization.

## EC2 Status Check Failure
### Immediate Triage
Determine instance vs system status check, instance state, recent events, app impact, ASG replacement capability.
### Suggested Remediation
System check: stop/start or replace with approval. Instance check: investigate OS/app/disk/memory/network. Reboot/replacement requires approval.

## EC2 CPU Credit Exhaustion
### Immediate Triage
Check CPUCreditBalance, CPUUtilization, burstable family, sustained workload.
### Suggested Remediation
Reduce workload, scale out, change instance class, or move off burstable. Requires approval.

## Infrastructure Memory Pressure
### Immediate Triage
Check memory, swap, process growth, deployment correlation, app errors.
### Suggested Remediation
Ask app owner to investigate leak/runaway process. Restart/reboot/scale requires approval.

## Disk or Filesystem Pressure
### Immediate Triage
Identify filesystem, growth rate, log growth, temp files, retention failure.
### Suggested Remediation
Recommend log rotation cleanup, retention review, volume expansion. Deleting files/resizing/restarting requires approval.

## Network Saturation or Packet Loss
### Immediate Triage
Check traffic, packet drops, ENI limits, load balancer metrics, spikes.
### Suggested Remediation
Traffic analysis, scaling, instance class review, network path investigation. Routing/security changes require approval.

## Load Balancer High Latency
### Immediate Triage
Check target response time, healthy hosts, requests, 5XX/4XX, deployment timing.
### Suggested Remediation
Identify slow target/service, backend saturation. Scaling/routing changes require approval.

## Load Balancer 5XX Errors
### Immediate Triage
Differentiate ELB 5XX vs target 5XX. Check target health, logs, dependencies, deployments.
### Suggested Remediation
Escalate to app team for target 5XX. Investigate TLS/security/listener changes for ELB 5XX. Rollback/drain/routing changes require approval.

## Load Balancer Unhealthy Targets
### Immediate Triage
Identify target group/hosts, health check path/port, SGs, deploys, startup.
### Suggested Remediation
Review health check, app start, rollback if deploy-related. Deregistration/change requires approval.

## ECS Service Health
### Immediate Triage
Compare desired/running/pending, task stop reasons, health checks, CPU/memory, image pull, secrets/config.
### Suggested Remediation
Rollback if deploy caused failures; inspect logs. Force deployment/scaling/rollback/task kill requires approval.

## Auto Scaling Capacity or Health
### Immediate Triage
Check desired/min/max, failed launches, lifecycle hooks, launch template, subnets, quotas.
### Suggested Remediation
Quota/subnet/capacity investigation. Capacity/template changes require approval.

## Lambda Errors or Throttles
### Immediate Triage
Check Errors, Throttles, Duration, concurrency, DLQ, iterator age, deployment.
### Suggested Remediation
Review logs, concurrency, retry/DLQ, rollback if deploy-related. Config/code changes require approval.

## AWS API or Service Throttling
### Immediate Triage
Identify service/API/caller/rate pattern/blast radius.
### Suggested Remediation
Exponential backoff with jitter, batching, quota increase, load reduction. Requires approval.

## General Infrastructure Alarm
### Immediate Triage
Identify resource, scope, duration, related alarms, recent changes, customer impact.
### Suggested Remediation
Determine capacity, availability, network, deployment, or dependency cause. Changes require approval.
