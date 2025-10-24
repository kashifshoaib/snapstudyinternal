#!/usr/bin/env python3
"""
Autonomous AI Agent Solution Diagram Generator
Creates a comprehensive diagram showing autonomous AI agent architecture with AWS services
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import Lambda, ECS, ElasticBeanstalk
from diagrams.aws.storage import S3 as S3Bucket
from diagrams.aws.devtools import Codecommit, Codepipeline, Codebuild
from diagrams.aws.network import APIGateway, Route53, CloudFront, ElbApplicationLoadBalancer
from diagrams.aws.ml import Bedrock, Textract, Transcribe, Polly, Comprehend
from diagrams.aws.management import Cloudwatch, CloudwatchLogs, CloudwatchAlarm
from diagrams.aws.security import Cognito, IAM, WAF, SecretsManager
from diagrams.aws.database import DynamodbTable
from diagrams.aws.integration import SNS
from diagrams.aws.general import General
from diagrams.onprem.client import Users
from diagrams.programming.framework import React
from diagrams.generic.blank import Blank

def create_autonomous_ai_agent_diagram():
    """Create autonomous AI agent solution diagram based on the provided architecture"""
    
    with Diagram("Autonomous AI Agent - Solution Architecture", 
                 show=False, 
                 direction="LR",
                 filename="autonomous_ai_agent_solution",
                 graph_attr={"bgcolor": "white", "pad": "1.0", "rankdir": "LR"}):
        
        # User
        user = Users("User")
        
        # Development Pipeline
        with Cluster("Development Pipeline"):
            codecommit = Codecommit("AWS\\nCodeCommit")
            codepipeline = Codepipeline("AWS\\nCodePipeline")
            codebuild = Codebuild("AWS CodeBuild")
            api_gateway = APIGateway("Amazon API\\nGateway")
        
        # Core Processing
        with Cluster("Core Processing"):
            s3_bucket = S3Bucket("S3 Bucket")
            step_function = Lambda("AWS Step\\nFunction")
        
        # AI Services - Main Processing Box
        with Cluster("Amazon Bedrock", graph_attr={"style": "dashed"}):
            # Test Generation Lambda
            test_gen_lambda = Lambda("Test Generation\\nLambda")
            
            # AI Models
            with Cluster("AI Models"):
                converse_api = Blank("Amazon Converse API")
                nova_pro = Blank("Amazon Nova Pro")
            
            # Quality and Compliance
            quality_lambda = Lambda("Quality and\\nCompliance\\nLambda")
        
        # Monitoring and Notifications
        with Cluster("Monitoring & Notifications"):
            sns = SNS("Amazon SNS")
            cloudwatch = Cloudwatch("Amazon\\nCloudWatch")
            cloudtrail = General("AWS CloudTrail")
        
        # Flow Connections
        user >> Edge(label="Commit ID") >> codecommit
        codecommit >> Edge(label="Code Upload") >> s3_bucket
        codecommit >> Edge(label="Change List") >> codepipeline
        codepipeline >> Edge(label="Commit ID") >> api_gateway
        
        # API Gateway to Step Function
        api_gateway >> Edge(label="Prompt") >> step_function
        
        # Step Function to Bedrock Services
        step_function >> Edge(label="Test Code") >> test_gen_lambda
        test_gen_lambda >> Edge(label="Prompt") >> converse_api
        test_gen_lambda >> Edge(label="Prompt") >> nova_pro
        
        # Feedback Loop within Bedrock
        converse_api >> Edge(label="Feedback Loop", style="dashed") >> nova_pro
        nova_pro >> Edge(label="Feedback Loop", style="dashed") >> converse_api
        
        # Quality and Compliance Flow
        step_function >> Edge(label="Prompt") >> quality_lambda
        
        # Reporting and Monitoring
        step_function >> Edge(label="Report") >> sns
        quality_lambda >> Edge(label="Report") >> sns
        
        # CloudWatch and CloudTrail connections
        test_gen_lambda >> Edge(style="dotted") >> cloudwatch
        quality_lambda >> Edge(style="dotted") >> cloudwatch
        step_function >> Edge(style="dotted") >> cloudtrail

if __name__ == "__main__":
    print("🎨 Generating Autonomous AI Agent Solution Diagram...")
    
    try:
        create_autonomous_ai_agent_diagram()
        print("✅ Autonomous AI agent diagram created: autonomous_ai_agent_solution.png")
        print("📊 Diagram includes:")
        print("   • Development pipeline with CodeCommit, CodePipeline, CodeBuild")
        print("   • API Gateway for request routing")
        print("   • AWS Step Functions for orchestration")
        print("   • Amazon Bedrock with AI models (Converse API, Nova Pro)")
        print("   • Test generation and quality compliance lambdas")
        print("   • Monitoring with SNS, CloudWatch, and CloudTrail")
        print("   • Complete autonomous AI agent workflow")
        
    except Exception as e:
        print(f"❌ Error generating diagram: {e}")
        import traceback
        traceback.print_exc()