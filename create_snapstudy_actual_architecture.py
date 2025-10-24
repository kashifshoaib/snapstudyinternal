#!/usr/bin/env python3
"""
SnapStudy Actual Architecture Diagram Generator
Creates a comprehensive diagram showing the real SnapStudy implementation
Based on actual codebase analysis and architecture documentation
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import Lambda, ECS, ElasticBeanstalk
from diagrams.aws.storage import S3
from diagrams.aws.network import APIGateway, Route53, CloudFront, ElbApplicationLoadBalancer
from diagrams.aws.ml import Bedrock, Textract, Transcribe, Polly, Comprehend
from diagrams.aws.management import Cloudwatch, CloudwatchLogs, CloudwatchAlarm, StepFunctions
from diagrams.aws.security import Cognito, IAM, WAF, SecretsManager
from diagrams.aws.database import DynamodbTable
from diagrams.aws.integration import SNS, SQS
from diagrams.aws.analytics import Opensearch
from diagrams.onprem.client import Users
from diagrams.programming.framework import React, FastAPI
from diagrams.generic.blank import Blank

def create_snapstudy_architecture():
    """Create comprehensive SnapStudy architecture diagram based on actual implementation"""
    
    with Diagram("SnapStudy - Complete AI-Powered Learning Platform Architecture", 
                 show=False, 
                 direction="TB",
                 filename="snapstudy_actual_architecture",
                 graph_attr={"bgcolor": "white", "pad": "1.0", "rankdir": "TB"}):
        
        # ============================================================================
        # USER & CLIENT LAYER
        # ============================================================================
        with Cluster("👥 Users & Client Applications", graph_attr={"bgcolor": "lightblue"}):
            students = Users("Students & Educators")
            with Cluster("Frontend Applications"):
                react_app = React("React Web App\\n(TypeScript)\\nPort 3000")
                mobile_future = Blank("Mobile Apps\\n(iOS/Android)\\nFuture Release")
        
        # ============================================================================
        # CDN & DNS LAYER
        # ============================================================================
        with Cluster("🌐 Global Content Delivery & DNS", graph_attr={"bgcolor": "lightgreen"}):
            route53 = Route53("Route 53\\nDNS Management\\nDomain Routing")
            cloudfront = CloudFront("CloudFront CDN\\nGlobal Edge Locations\\nStatic Asset Caching")
            frontend_s3 = S3("Frontend Assets\\nS3 Static Hosting\\nReact Build Files")
        
        # ============================================================================
        # SECURITY & LOAD BALANCING LAYER
        # ============================================================================
        with Cluster("🛡️ Security & Load Balancing", graph_attr={"bgcolor": "lightyellow"}):
            waf = WAF("AWS WAF\\nWeb Application Firewall\\nRate Limiting (1000/5min)\\nSQL Injection Protection")
            alb = ElbApplicationLoadBalancer("Application Load Balancer\\nMulti-AZ Deployment\\nHealth Checks")
            api_gateway = APIGateway("API Gateway\\nREST API Management\\nRequest Validation\\nThrottling")
        
        # ==================================================================