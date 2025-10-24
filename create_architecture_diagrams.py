#!/usr/bin/env python3
"""
SnapStudy Architecture Diagram Generator

Generates architecture and data flow diagrams for the SnapStudy platform.
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import Lambda, ECS, Fargate
from diagrams.aws.database import Dynamodb, DynamodbTable
from diagrams.aws.storage import S3
from diagrams.aws.network import ApiGateway, CloudFront, ElbApplicationLoadBalancer
from diagrams.aws.security import Cognito, Waf, IAM, SecretsManager
from diagrams.aws.analytics import Cloudwatch, CloudwatchLogs
from diagrams.aws.ml import Bedrock, Textract, Transcribe, Polly
from diagrams.aws.general import General, User
from diagrams.onprem.client import Users, Client
from diagrams.programming.framework import React, FastAPI
from diagrams.programming.language import Python, TypeScript
from diagrams.generic.blank import Blank
from diagrams.generic.compute import Rack
from diagrams.generic.device import Mobile, Tablet
from diagrams.generic.network import Firewall
import os

def create_architecture_diagram():
    """Create the main architecture diagram."""
    
    with Diagram("SnapStudy Platform Architecture", 
                 show=False, 
                 direction="TB",
                 filename="snapstudy_architecture",
                 graph_attr={"bgcolor": "white", "pad": "0.5"}):
        
        # User Layer
        with Cluster("Users & Clients"):
            students = Users("Students & Learners")
            web_browser = Client("Web Browser")
            mobile_app = Mobile("Mobile App (Future)")
        
        # Frontend Layer
        with Cluster("Frontend Layer"):
            react_app = React("React Frontend\n(TypeScript)")
            static_assets = S3("Static Assets\n(S3 + CloudFront)")
        
        # Security & Load Balancing
        with Cluster("Security & Load Balancing"):
            waf = Waf("AWS WAF")
            alb = ElbApplicationLoadBalancer("Application\nLoad Balancer")
            api_gateway = ApiGateway("API Gateway")
        
        # Backend Services
        with Cluster("Backend Services"):
            # Main API
            fastapi_backend = Lambda("FastAPI Backend\n(Python)")
            
            # Microservices
            with Cluster("Core Services"):
                auth_service = Lambda("Authentication\nService")
                lesson_service = Lambda("Lesson\nManagement")
                ai_service = Lambda("AI/ML\nServices")
                multimedia_service = Lambda("Multimedia\nProcessor")
                analytics_service = Lambda("Analytics\nEngine")
                chat_service = Lambda("Agentic Chat\nService")
        
        # AI/ML Platform
        with Cluster("AI/ML Platform"):
            bedrock = Bedrock("Amazon Bedrock\n(Claude 3.5)")
            textract = Textract("Document\nProcessing")
            transcribe = Transcribe("Speech to Text")
            polly = Polly("Text to Speech")
        
        # Data Storage
        with Cluster("Data Storage Layer"):
            # Authentication
            cognito = Cognito("User Pool\n& Identity")
            
            # DynamoDB Tables
            with Cluster("DynamoDB Tables"):
                users_table = DynamodbTable("Users")
                lessons_table = DynamodbTable("Lessons")
                micro_lessons_table = DynamodbTable("Micro Lessons")
                quizzes_table = DynamodbTable("Quizzes")
                engagement_table = DynamodbTable("User Engagement")
                chat_table = DynamodbTable("Chat History")
            
            # Content Storage
            content_s3 = S3("Content Storage\n(Documents, Media)")
        
        # Monitoring & Security
        with Cluster("Monitoring & Operations"):
            cloudwatch = Cloudwatch("CloudWatch\nMetrics & Logs")
            iam = IAM("IAM Roles\n& Policies")
            secrets = SecretsManager("Secrets\nManagement")
        
        # User Flow
        students >> web_browser
        students >> mobile_app
        
        # Frontend Flow
        web_browser >> react_app
        mobile_app >> react_app
        react_app >> static_assets
        
        # Security Flow
        react_app >> waf
        waf >> alb
        alb >> api_gateway
        api_gateway >> fastapi_backend
        
        # Backend Service Flow
        fastapi_backend >> auth_service
        fastapi_backend >> lesson_service
        fastapi_backend >> ai_service
        fastapi_backend >> multimedia_service
        fastapi_backend >> analytics_service
        fastapi_backend >> chat_service
        
        # AI/ML Flow
        ai_service >> bedrock
        chat_service >> bedrock
        multimedia_service >> textract
        multimedia_service >> transcribe
        multimedia_service >> polly
        
        # Data Flow
        auth_service >> cognito
        auth_service >> users_table
        lesson_service >> lessons_table
        lesson_service >> micro_lessons_table
        lesson_service >> quizzes_table
        lesson_service >> content_s3
        analytics_service >> engagement_table
        chat_service >> chat_table
        multimedia_service >> content_s3
        
        # Monitoring Flow
        fastapi_backend >> cloudwatch
        alb >> cloudwatch
        api_gateway >> cloudwatch
        
        # Security Flow
        fastapi_backend >> iam
        bedrock >> iam
        content_s3 >> iam
        fastapi_backend >> secrets

def create_data_flow_diagram():
    """Create the data flow diagram."""
    
    with Diagram("SnapStudy Data Flow", 
                 show=False, 
                 direction="LR",
                 filename="snapstudy_data_flow",
                 graph_attr={"bgcolor": "white", "pad": "0.5"}):
        
        # Input Sources
        with Cluster("Content Input"):
            user_upload = Users("User Uploads\nDocuments")
            document = General("PDF/DOC/PPT\nFiles")
        
        # Processing Pipeline
        with Cluster("AI Processing Pipeline"):
            textract_proc = Textract("Document\nExtraction")
            ai_analysis = Bedrock("AI Content\nAnalysis")
            lesson_gen = Lambda("Lesson\nGeneration")
            quiz_gen = Lambda("Quiz\nGeneration")
        
        # Content Generation
        with Cluster("Multimedia Generation"):
            text_content = General("Text\nContent")
            audio_gen = Polly("Audio\nGeneration")
            video_gen = Lambda("Video\nGeneration")
        
        # Storage & Delivery
        with Cluster("Content Storage"):
            processed_content = S3("Processed\nContent")
            lesson_db = DynamodbTable("Lesson\nDatabase")
            media_storage = S3("Media\nStorage")
        
        # User Interaction
        with Cluster("User Experience"):
            learning_interface = React("Learning\nInterface")
            progress_tracking = Lambda("Progress\nTracking")
            adaptive_engine = Bedrock("Adaptive\nLearning")
        
        # Analytics & Feedback
        with Cluster("Analytics Pipeline"):
            user_analytics = DynamodbTable("User\nEngagement")
            learning_analytics = Lambda("Learning\nAnalytics")
            recommendations = Bedrock("AI\nRecommendations")
        
        # Data Flow Connections
        user_upload >> document
        document >> textract_proc
        textract_proc >> ai_analysis
        ai_analysis >> lesson_gen
        ai_analysis >> quiz_gen
        
        # Content Generation Flow
        lesson_gen >> text_content
        text_content >> audio_gen
        text_content >> video_gen
        
        # Storage Flow
        lesson_gen >> lesson_db
        quiz_gen >> lesson_db
        audio_gen >> media_storage
        video_gen >> media_storage
        text_content >> processed_content
        
        # User Experience Flow
        lesson_db >> learning_interface
        media_storage >> learning_interface
        processed_content >> learning_interface
        learning_interface >> progress_tracking
        progress_tracking >> adaptive_engine
        
        # Analytics Flow
        progress_tracking >> user_analytics
        user_analytics >> learning_analytics
        learning_analytics >> recommendations
        recommendations >> adaptive_engine
        
        # Feedback Loop
        adaptive_engine >> Edge(label="Personalized\nContent", style="dashed") >> learning_interface

def main():
    """Generate both diagrams."""
    print("🎨 Generating SnapStudy architecture diagrams...")
    
    try:
        # Create architecture diagram
        print("📊 Creating architecture diagram...")
        create_architecture_diagram()
        print("✅ Architecture diagram created: snapstudy_architecture.png")
        
        # Create data flow diagram
        print("🔄 Creating data flow diagram...")
        create_data_flow_diagram()
        print("✅ Data flow diagram created: snapstudy_data_flow.png")
        
        print("\n🎉 All diagrams generated successfully!")
        print("📁 Files created:")
        print("   • snapstudy_architecture.png")
        print("   • snapstudy_data_flow.png")
        
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("💡 Install with: pip install diagrams")
    except Exception as e:
        print(f"❌ Error generating diagrams: {e}")

if __name__ == "__main__":
    main()