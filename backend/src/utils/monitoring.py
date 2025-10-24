"""
Performance monitoring and metrics utilities for SnapStudy backend.

Provides CloudWatch metrics, performance tracking, and system monitoring.
"""

import time
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from functools import wraps
import boto3
from botocore.exceptions import ClientError
import psutil
import os

from ..config import settings

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Performance monitoring and metrics collection."""
    
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch', region_name=settings.aws_region)
        self.namespace = "SnapStudy/API"
        self.metrics_buffer = []
        self.buffer_size = 20  # Send metrics in batches
    
    def track_execution_time(self, metric_name: str, dimensions: Optional[Dict[str, str]] = None):
        """Decorator to track function execution time."""
        
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    success = True
                    error_type = None
                except Exception as e:
                    success = False
                    error_type = type(e).__name__
                    raise
                finally:
                    execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                    
                    # Record metrics
                    self._record_execution_metrics(
                        metric_name, 
                        execution_time, 
                        success, 
                        error_type,
                        dimensions
                    )
                
                return result
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    success = True
                    error_type = None
                except Exception as e:
                    success = False
                    error_type = type(e).__name__
                    raise
                finally:
                    execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                    
                    # Record metrics
                    self._record_execution_metrics(
                        metric_name, 
                        execution_time, 
                        success, 
                        error_type,
                        dimensions
                    )
                
                return result
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator
    
    def _record_execution_metrics(
        self, 
        metric_name: str, 
        execution_time: float, 
        success: bool,
        error_type: Optional[str] = None,
        dimensions: Optional[Dict[str, str]] = None
    ):
        """Record execution metrics."""
        
        base_dimensions = dimensions or {}
        
        # Execution time metric
        self._add_metric(
            metric_name="ExecutionTime",
            value=execution_time,
            unit="Milliseconds",
            dimensions={**base_dimensions, "Operation": metric_name}
        )
        
        # Success/failure count
        self._add_metric(
            metric_name="OperationCount",
            value=1,
            unit="Count",
            dimensions={
                **base_dimensions, 
                "Operation": metric_name,
                "Status": "Success" if success else "Error"
            }
        )
        
        # Error type if failed
        if not success and error_type:
            self._add_metric(
                metric_name="ErrorCount",
                value=1,
                unit="Count",
                dimensions={
                    **base_dimensions,
                    "Operation": metric_name,
                    "ErrorType": error_type
                }
            )
    
    def _add_metric(
        self, 
        metric_name: str, 
        value: float, 
        unit: str = "Count",
        dimensions: Optional[Dict[str, str]] = None
    ):
        """Add metric to buffer."""
        
        metric_data = {
            'MetricName': metric_name,
            'Value': value,
            'Unit': unit,
            'Timestamp': datetime.utcnow()
        }
        
        if dimensions:
            metric_data['Dimensions'] = [
                {'Name': k, 'Value': v} for k, v in dimensions.items()
            ]
        
        self.metrics_buffer.append(metric_data)
        
        # Send metrics if buffer is full
        if len(self.metrics_buffer) >= self.buffer_size:
            asyncio.create_task(self._flush_metrics())
    
    async def _flush_metrics(self):
        """Send buffered metrics to CloudWatch."""
        
        if not self.metrics_buffer:
            return
        
        try:
            # Send metrics in batches (CloudWatch limit is 20 per request)
            batch_size = 20
            for i in range(0, len(self.metrics_buffer), batch_size):
                batch = self.metrics_buffer[i:i + batch_size]
                
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=batch
                )
            
            logger.debug(f"Sent {len(self.metrics_buffer)} metrics to CloudWatch")
            self.metrics_buffer.clear()
            
        except Exception as e:
            logger.error(f"Failed to send metrics to CloudWatch: {str(e)}")
            # Keep metrics in buffer for retry
    
    async def flush_all_metrics(self):
        """Flush all remaining metrics."""
        await self._flush_metrics()
    
    def record_custom_metric(
        self, 
        metric_name: str, 
        value: float, 
        unit: str = "Count",
        dimensions: Optional[Dict[str, str]] = None
    ):
        """Record a custom metric."""
        self._add_metric(metric_name, value, unit, dimensions)
    
    def record_api_request(
        self, 
        endpoint: str, 
        method: str, 
        status_code: int, 
        response_time_ms: float
    ):
        """Record API request metrics."""
        
        dimensions = {
            "Endpoint": endpoint,
            "Method": method,
            "StatusCode": str(status_code)
        }
        
        # Response time
        self._add_metric(
            metric_name="APIResponseTime",
            value=response_time_ms,
            unit="Milliseconds",
            dimensions=dimensions
        )
        
        # Request count
        self._add_metric(
            metric_name="APIRequestCount",
            value=1,
            unit="Count",
            dimensions=dimensions
        )
        
        # Error count for non-2xx responses
        if status_code >= 400:
            self._add_metric(
                metric_name="APIErrorCount",
                value=1,
                unit="Count",
                dimensions=dimensions
            )


class SystemMonitor:
    """System resource monitoring."""
    
    def __init__(self):
        self.performance_monitor = PerformanceMonitor()
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_mb = memory.available / (1024 * 1024)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free_gb = disk.free / (1024 * 1024 * 1024)
            
            # Process metrics
            process = psutil.Process(os.getpid())
            process_memory_mb = process.memory_info().rss / (1024 * 1024)
            process_cpu_percent = process.cpu_percent()
            
            return {
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count
                },
                "memory": {
                    "percent": memory_percent,
                    "available_mb": memory_available_mb,
                    "process_mb": process_memory_mb
                },
                "disk": {
                    "percent": disk_percent,
                    "free_gb": disk_free_gb
                },
                "process": {
                    "cpu_percent": process_cpu_percent,
                    "memory_mb": process_memory_mb
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}")
            return {}
    
    async def record_system_metrics(self):
        """Record system metrics to CloudWatch."""
        
        metrics = self.get_system_metrics()
        
        if not metrics:
            return
        
        try:
            # CPU metrics
            if 'cpu' in metrics:
                self.performance_monitor.record_custom_metric(
                    "SystemCPUUtilization",
                    metrics['cpu']['percent'],
                    "Percent"
                )
            
            # Memory metrics
            if 'memory' in metrics:
                self.performance_monitor.record_custom_metric(
                    "SystemMemoryUtilization",
                    metrics['memory']['percent'],
                    "Percent"
                )
                
                self.performance_monitor.record_custom_metric(
                    "ProcessMemoryUsage",
                    metrics['memory']['process_mb'],
                    "Megabytes"
                )
            
            # Disk metrics
            if 'disk' in metrics:
                self.performance_monitor.record_custom_metric(
                    "SystemDiskUtilization",
                    metrics['disk']['percent'],
                    "Percent"
                )
            
        except Exception as e:
            logger.error(f"Error recording system metrics: {str(e)}")


class AlertManager:
    """Alert management for system monitoring."""
    
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch', region_name=settings.aws_region)
        self.sns = boto3.client('sns', region_name=settings.aws_region)
    
    async def create_alarms(self):
        """Create CloudWatch alarms for monitoring."""
        
        alarms = [
            {
                'AlarmName': 'SnapStudy-HighErrorRate',
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 2,
                'MetricName': 'APIErrorCount',
                'Namespace': 'SnapStudy/API',
                'Period': 300,  # 5 minutes
                'Statistic': 'Sum',
                'Threshold': 10.0,
                'ActionsEnabled': True,
                'AlarmDescription': 'High error rate detected',
                'Unit': 'Count'
            },
            {
                'AlarmName': 'SnapStudy-HighResponseTime',
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 2,
                'MetricName': 'APIResponseTime',
                'Namespace': 'SnapStudy/API',
                'Period': 300,
                'Statistic': 'Average',
                'Threshold': 5000.0,  # 5 seconds
                'ActionsEnabled': True,
                'AlarmDescription': 'High response time detected',
                'Unit': 'Milliseconds'
            },
            {
                'AlarmName': 'SnapStudy-HighCPUUtilization',
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 3,
                'MetricName': 'SystemCPUUtilization',
                'Namespace': 'SnapStudy/API',
                'Period': 300,
                'Statistic': 'Average',
                'Threshold': 80.0,
                'ActionsEnabled': True,
                'AlarmDescription': 'High CPU utilization detected',
                'Unit': 'Percent'
            },
            {
                'AlarmName': 'SnapStudy-HighMemoryUtilization',
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 3,
                'MetricName': 'SystemMemoryUtilization',
                'Namespace': 'SnapStudy/API',
                'Period': 300,
                'Statistic': 'Average',
                'Threshold': 85.0,
                'ActionsEnabled': True,
                'AlarmDescription': 'High memory utilization detected',
                'Unit': 'Percent'
            }
        ]
        
        for alarm in alarms:
            try:
                self.cloudwatch.put_metric_alarm(**alarm)
                logger.info(f"Created alarm: {alarm['AlarmName']}")
            except Exception as e:
                logger.error(f"Failed to create alarm {alarm['AlarmName']}: {str(e)}")


# Global instances
performance_monitor = PerformanceMonitor()
system_monitor = SystemMonitor()
alert_manager = AlertManager()

# Convenience decorators
def monitor_performance(metric_name: str, dimensions: Optional[Dict[str, str]] = None):
    """Decorator for monitoring function performance."""
    return performance_monitor.track_execution_time(metric_name, dimensions)

def monitor_api_endpoint(endpoint_name: str):
    """Decorator for monitoring API endpoint performance."""
    return monitor_performance(f"API_{endpoint_name}", {"EndpointType": "API"})

def monitor_service_call(service_name: str):
    """Decorator for monitoring service call performance."""
    return monitor_performance(f"Service_{service_name}", {"ServiceType": "Internal"})

def monitor_aws_call(service_name: str):
    """Decorator for monitoring AWS service call performance."""
    return monitor_performance(f"AWS_{service_name}", {"ServiceType": "AWS"})