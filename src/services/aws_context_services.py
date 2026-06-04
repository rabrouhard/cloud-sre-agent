from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any
import boto3

def _metric(event):
    cfg = event.get("detail", {}).get("configuration", {})
    metrics = cfg.get("metrics", [])
    if metrics: return metrics[0].get("metricStat", {}).get("metric", {}).get("name")
    return cfg.get("metricName")

def _namespace(event):
    cfg = event.get("detail", {}).get("configuration", {})
    metrics = cfg.get("metrics", [])
    if metrics: return metrics[0].get("metricStat", {}).get("metric", {}).get("namespace")
    return cfg.get("namespace")

def _dimensions(event):
    cfg = event.get("detail", {}).get("configuration", {})
    metrics = cfg.get("metrics", [])
    if metrics:
        dims = metrics[0].get("metricStat", {}).get("metric", {}).get("dimensions", {})
        if isinstance(dims, dict): return [{"Name": k, "Value": v} for k, v in dims.items()]
        if isinstance(dims, list): return dims
    return cfg.get("dimensions", [])

def _dim(dimensions, name):
    for d in dimensions:
        if d.get("Name") == name: return d.get("Value")
    return None

class CloudWatchMetricMixin:
    def _metric_datapoints(self, namespace, metric_name, dimensions):
        if not namespace or not metric_name:
            return {"error":"namespace or metric name unavailable"}
        end = datetime.now(timezone.utc); start = end - timedelta(minutes=60)
        try:
            resp = self.cloudwatch.get_metric_statistics(
                Namespace=namespace, MetricName=metric_name, Dimensions=dimensions,
                StartTime=start, EndTime=end, Period=300,
                Statistics=["Average","Maximum","Minimum","Sum"])
            return {"datapoints": sorted(resp.get("Datapoints", []), key=lambda x: x["Timestamp"])}
        except Exception as exc:
            return {"error": str(exc)}

class AuroraService(CloudWatchMetricMixin):
    def __init__(self, region_name: str):
        self.rds = boto3.client("rds", region_name=region_name)
        self.cloudwatch = boto3.client("cloudwatch", region_name=region_name)

    def get_context(self, alarm_event: dict[str, Any]) -> dict[str, Any]:
        namespace, metric_name, dimensions = _namespace(alarm_event) or "AWS/RDS", _metric(alarm_event), _dimensions(alarm_event)
        cluster_id = _dim(dimensions, "DBClusterIdentifier") or _dim(dimensions, "DBInstanceIdentifier")
        ctx = {"cluster_id": cluster_id, "namespace": namespace, "metric_name": metric_name, "dimensions": dimensions, "metric": self._metric_datapoints(namespace, metric_name, dimensions)}
        if cluster_id:
            ctx["cluster"] = self._describe_cluster(cluster_id)
            ctx["events"] = self._describe_events(cluster_id)
        return ctx

    def _describe_cluster(self, cluster_id):
        try:
            r = self.rds.describe_db_clusters(DBClusterIdentifier=cluster_id)["DBClusters"][0]
            return {k: r.get(k) for k in ["DBClusterIdentifier","Status","Engine","EngineVersion","Endpoint","ReaderEndpoint","MultiAZ","DBClusterMembers","BackupRetentionPeriod","PreferredBackupWindow","PreferredMaintenanceWindow"]}
        except Exception as exc:
            return {"error": str(exc)}

    def _describe_events(self, cluster_id):
        try:
            r = self.rds.describe_events(SourceIdentifier=cluster_id, SourceType="db-cluster", Duration=1440)
            return [{"Date": e.get("Date"), "Message": e.get("Message"), "EventCategories": e.get("EventCategories")} for e in r.get("Events", [])[:25]]
        except Exception as exc:
            return [{"error": str(exc)}]

class InfrastructureService(CloudWatchMetricMixin):
    def __init__(self, region_name: str):
        self.cloudwatch = boto3.client("cloudwatch", region_name=region_name)
        self.ec2 = boto3.client("ec2", region_name=region_name)
        self.elbv2 = boto3.client("elbv2", region_name=region_name)
        self.ecs = boto3.client("ecs", region_name=region_name)
        self.autoscaling = boto3.client("autoscaling", region_name=region_name)
        self.lambda_client = boto3.client("lambda", region_name=region_name)

    def get_context(self, alarm_event: dict[str, Any]) -> dict[str, Any]:
        ns, metric_name, dims = _namespace(alarm_event), _metric(alarm_event), _dimensions(alarm_event)
        ctx = {"namespace": ns, "metric_name": metric_name, "dimensions": dims, "metric": self._metric_datapoints(ns, metric_name, dims)}
        if ns == "AWS/EC2": ctx["ec2"] = self._ec2(dims)
        elif ns == "AWS/ECS": ctx["ecs"] = self._ecs(dims)
        elif ns == "AWS/AutoScaling": ctx["autoscaling"] = self._asg(dims)
        elif ns == "AWS/Lambda": ctx["lambda"] = self._lambda(dims)
        elif ns in {"AWS/ApplicationELB","AWS/NetworkELB","AWS/ElasticLoadBalancing"}: ctx["load_balancer"] = {"dimensions": dims, "note": "Target/LB ARN mapping available from dimensions"}
        return ctx

    def _ec2(self, dims):
        ids = [d["Value"] for d in dims if d.get("Name") == "InstanceId"]
        if not ids: return {"note":"No InstanceId dimension found"}
        try:
            r = self.ec2.describe_instances(InstanceIds=ids)
            return {"instances": [i for res in r.get("Reservations", []) for i in res.get("Instances", [])]}
        except Exception as exc: return {"error": str(exc)}

    def _ecs(self, dims):
        cluster, service = _dim(dims,"ClusterName"), _dim(dims,"ServiceName")
        if not cluster: return {"note":"No ClusterName dimension found"}
        try:
            return self.ecs.describe_services(cluster=cluster, services=[service]) if service else {"cluster_name": cluster}
        except Exception as exc: return {"error": str(exc)}

    def _asg(self, dims):
        name = _dim(dims, "AutoScalingGroupName")
        if not name: return {"note":"No AutoScalingGroupName dimension found"}
        try: return self.autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[name])
        except Exception as exc: return {"error": str(exc)}

    def _lambda(self, dims):
        fn = _dim(dims, "FunctionName")
        if not fn: return {"note":"No FunctionName dimension found"}
        try: return self.lambda_client.get_function_configuration(FunctionName=fn)
        except Exception as exc: return {"error": str(exc)}

class ApplicationErrorService(CloudWatchMetricMixin):
    def __init__(self, region_name: str):
        self.cloudwatch = boto3.client("cloudwatch", region_name=region_name)
        self.logs = boto3.client("logs", region_name=region_name)

    def get_context(self, alarm_event: dict[str, Any]) -> dict[str, Any]:
        ns, metric_name, dims = _namespace(alarm_event), _metric(alarm_event), _dimensions(alarm_event)
        groups = self._log_groups(alarm_event)
        return {"namespace": ns, "metric_name": metric_name, "dimensions": dims, "metric": self._metric_datapoints(ns, metric_name, dims), "log_groups": groups, "recent_log_errors": [{"log_group": g, "events": self._recent_errors(g)} for g in groups[:3]]}

    def _log_groups(self, event):
        groups = set()
        for d in _dimensions(event):
            if d.get("Name") in {"LogGroupName","logGroupName"} and d.get("Value"): groups.add(d["Value"])
        cfg = event.get("detail", {}).get("configuration", {})
        for k in ["logGroupName","logGroupNames"]:
            v = cfg.get(k)
            if isinstance(v, str): groups.add(v)
            elif isinstance(v, list): groups.update(str(x) for x in v)
        alarm = event.get("detail", {}).get("alarmName", "")
        if "loggroup=" in alarm: groups.add(alarm.split("loggroup=",1)[1].split()[0])
        return sorted(groups)

    def _recent_errors(self, log_group):
        end_ms = int(datetime.now(timezone.utc).timestamp()*1000)
        start_ms = int((datetime.now(timezone.utc)-timedelta(minutes=30)).timestamp()*1000)
        pattern = '?ERROR ?Error ?error ?Exception ?exception ?Timeout ?timeout ?Traceback ?" 5" ?"status=5"'
        try:
            r = self.logs.filter_log_events(logGroupName=log_group, startTime=start_ms, endTime=end_ms, filterPattern=pattern, limit=25)
            return [{"timestamp": e.get("timestamp"), "logStreamName": e.get("logStreamName"), "message": (e.get("message","").replace("\n"," ")[:2000])} for e in r.get("events", [])]
        except Exception as exc:
            return [{"error": str(exc)}]
