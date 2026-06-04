from src.domain.alarm_classifier import AlarmClassifier
from src.domain.models import AlarmDomain

def event(namespace, metric, alarm_name="test"):
    return {"source":"aws.cloudwatch","detail-type":"CloudWatch Alarm State Change","account":"123","region":"us-gov-west-1","detail":{"alarmName":alarm_name,"state":{"reason":"threshold crossed"},"configuration":{"metrics":[{"metricStat":{"metric":{"namespace":namespace,"name":metric,"dimensions":{}}}}]}}}

def test_database_classification():
    c = AlarmClassifier().classify(event("AWS/RDS", "DatabaseConnections", "aurora-prod-connections"))
    assert c.domain == AlarmDomain.DATABASE
    assert c.category == "aurora_connection_exhaustion"

def test_infrastructure_classification():
    c = AlarmClassifier().classify(event("AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", "alb-5xx"))
    assert c.domain == AlarmDomain.INFRASTRUCTURE

def test_application_classification():
    c = AlarmClassifier().classify(event("AWS/Logs", "ErrorCount", "app-error-loggroup=/aws/ecs/app"))
    assert c.domain == AlarmDomain.APPLICATION
