# RUNBOOK-Aurora-PostgreSQL-DBA-Agent

## Purpose
DBA/SRE guidance for Aurora PostgreSQL alarms. Advisory-only.

## Safety Rules
- Do not restart, reboot, fail over, scale, modify parameters, terminate sessions, kill queries, change backups, or execute SQL automatically.
- Require human approval for availability-impacting, destructive, data-changing, cost-impacting, or topology-changing actions.
- Separate observed facts from inferred causes.

## Agent Output Format
Summary, Likely Cause, Confidence, Business Impact, Observed Evidence, Recommended Triage, Suggested Remediation, Human Approval Required, Rollback, Verification, ServiceNow Priority, Escalation.

## Common Context to Gather
Alarm details, cluster/instance status, writer/reader topology, engine version, instance class, recent RDS events, failover history, CPU, memory, connections, I/O, latency, storage, replica lag.

## Severity Model
Critical: writer unavailable, storage exhaustion, repeated failover. High: connection exhaustion, high writer CPU/memory, severe lag. Medium: reader degradation, latency, warning storage. Low: transient non-production.

## ServiceNow Incident Guidance
Create incidents for Medium or higher severity, production impact, backup failure, availability risk, connection exhaustion, or storage pressure.

## Human Approval Matrix
No approval: email, incident, audit, read-only context. Approval: scale, failover, restart, SQL, kill session, parameter modification.

## Agent Decision Rules
Prioritize availability, storage exhaustion, connection exhaustion, write latency, CPU, reader lag, deadlocks.

## High CPU Utilization
### Immediate Triage
Check writer vs reader CPU, connections, latency, recent failover/deployment/batch workload.
### Suggested Remediation
Review Performance Insights top SQL and waits; move reads to readers if safe; pause batch work with approval. Scaling, failover, query cancellation, parameter changes, restarts require approval.

## Connection Exhaustion
### Immediate Triage
Check sudden vs gradual growth, reconnect storm, app pool settings, idle transactions, recent deployment.
### Suggested Remediation
Ask app team to review pools/leaks; recommend PgBouncer/RDS Proxy for recurring churn. Killing sessions, max_connections changes, scaling require approval.

## Low Freeable Memory
### Immediate Triage
Correlate with connection growth, CPU, disk queue, parameter changes.
### Suggested Remediation
Reduce known batch concurrency; review memory-heavy queries, work_mem, and pool settings. Parameter changes and scaling require approval.

## Storage Pressure
### Immediate Triage
Check growth rate, bulk loads, long transactions, replication slot retention, temp files, autovacuum.
### Suggested Remediation
Pause non-critical bulk loads with approval; review retention; identify largest objects. Dropping/purging/vacuum full/terminating transactions require approval.

## Replica Lag / Replication Delay
### Immediate Triage
Identify affected reader, writer write volume, reader CPU/memory, concentrated reads.
### Suggested Remediation
Shift read traffic away from lagging reader if approved; route consistency-sensitive reads to writer if app owner approves. Scaling/restart/routing changes require approval.

## High Read or Write Latency
### Immediate Triage
Determine read vs write impact, correlate CPU/connections/IOPS/batch jobs/waits.
### Suggested Remediation
Throttle non-critical writes; move reporting to readers; review top SQL. Scaling, indexing, restart, failover require approval.

## Deadlocks
### Immediate Triage
Check whether isolated or increasing, deployment correlation, application transaction paths.
### Suggested Remediation
Recommend transaction ordering review and bounded retries with jitter. Killing sessions or code/index/isolation changes require approval.

## Freeable Local Storage Low on Instance
### Immediate Triage
Check temp-heavy queries, reports, sorts/hash joins, index builds, writer impact.
### Suggested Remediation
Move reports off writer; pause non-critical analytical queries with approval.

## Failover, Restart, or Availability Degradation
### Immediate Triage
Confirm current writer, instance health, RDS events, app DNS behavior, cluster endpoint usage.
### Suggested Remediation
Notify app team, verify cluster endpoint usage, monitor repeated failover. Manual failover/restart/topology changes require approval.
