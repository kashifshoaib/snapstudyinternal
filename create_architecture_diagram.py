#!/usr/bin/env python3
"""
SnapStudy Architecture Diagram Generator
Generates updated architecture and data flow diagrams for the SnapStudy platform
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import Lambda, ElasticContainerService
from diagrams.aws.database import Dynamodb, DynamodbTable
from diagrams.aws.storage import S3
from diagrams.aws.security import Cognito, IAM, WAF
from diagrams.aws.network import APIGateway, ElbApplicationLoadBalancer
from diagrams.aws.management import Cloudwatch
from diagrams.aws.ml import Bedrock, Textract, Transcribe, Polly
from diagrams.generic.blank import Blank
from diagrams.programming.framework import React, FastAPI
from diagrams.onprem.client import User, Users

def create_architecture_diagram():
    """Create the main architecture diagram"""
    
    with Diagram("SnapStudy Platform Architecture - 2024", 
                 show=False, 
                 direction="TB",
                 filename="snapstudy_architecture",
                 graph_attr={"bgcolor": "white", "pad": "0.5"}):
        
        # User Layer
        with Cluster("Users & Clients"):
            students = Users("Students & Learners")
            web_browser = React("React Frontend\n(Web Browser)")
            mobile_app = Blank("Mobile App\n(Future)")
        
        # API Gateway & Load Balancing
        with Cluster("API Gateway & Load Balancing"):
            alb = ElbApplicationLoadBalancer("Application\nLoad Balancer")
            api_gateway = APIGateway("API Gateway")
        
        # Backend Services
        with Cluster("Backend Services"):
            # Main FastAPI Application
            fastapi_app = Lambda("FastAPI Backend\n(Python 3.11)")
            
            # Microservices
            with Cluster("Core Services"):
                auth_svc = Lambda("Authentication\nService")
                lesson_svc = Lambda("Lesson\nManagement")
                ai_svc = Lambda("AI/ML\nProcessing")
                multimedia_svc = Lambda("Multimedia\nGeneration")
                analytics_svc = Lambda("Learning\nAnalytics")
                chat_svc = Lambda("AI Chat\nAssistant")
        
        # AI/ML Platform
        with Cluster("AI/ML Services"):
            bedrock = Bedrock("Amazon Bedrock\n(Claude 3.5)")
            textract = Textract("Document\nProcessing")
            transcribe = Transcribe("Speech to\nText")
            polly = Polly("Text to\nSpeech")
        
        # Data Storage
        with Cluster("Data Storage Layer"):
            # Authentication
            cognito = Cognito("User Pool\n& Identity")
            
            # Database Tables
            with Cluster("DynamoDB Tables"):
                users_db = DynamodbTable("Users")
                lessons_db = DynamodbTable("Lessons")
                micro_lessons_db = DynamodbTable("Micro Lessons")
                quizzes_db = DynamodbTable("Quizzes")
                engagement_db = DynamodbTable("User Engagement")
                chat_db = DynamodbTable("Chat History")
            
            # File Storage
            content_storage = S3("Content Storage\n(Documents, Media)")
        
        # Security & Monitoring
        with Cluster("Security & Monitoring"):
            waf = WAF("AWS WAF\nProtection")
            iam = IAM("IAM Roles\n& Policies")
            monitoring = Cloudwatch("CloudWatch\nLogs & Metrics")
        
        # User Flow
        students >> web_browser
        students >> mobile_app
        
        # Frontend to Backend
        web_browser >> Edge(label="HTTPS") >> alb
        mobile_app >> Edge(label="HTTPS") >> alb
        
        # Load Balancing
        waf >> alb
        alb >> api_gateway
        api_gateway >> fastapi_app
        
        # Backend Service Communication
        fastapi_app >> auth_svc
        fastapi_app >> lesson_svc
        fastapi_app >> ai_svc
        fastapi_app >> multimedia_svc
        fastapi_app >> analytics_svc
        fastapi_app >> chat_svc
        
        # AI/ML Integration
        ai_svc >> bedrock
        chat_svc >> bedrock
        multimedia_svc >> textract
        multimedia_svc >> transcribe
        multimedia_svc >> polly
        
        # Data Access
        auth_svc >> cognito
        auth_svc >> users_db
        lesson_svc >> lessons_db
        lesson_svc >> micro_lessons_db
        lesson_svc >> quizzes_db
        analytics_svc >> engagement_db
        chat_svc >> chat_db
        
        # Content Storage
        lesson_svc >> content_storage
        multimedia_svc >> content_storage
        
        # Security & Monitoring
        iam >> fastapi_app
        iam >> bedrock
        fastapi_app >> monitoring
        alb >> monitoring

def create_data_flow_diagram():
    """Create the data flow diagram"""
    
    with Diagram("SnapStudy Data Flow - Learning Journey", 
                 show=False, 
                 direction="LR",
                 filename="snapstudy_data_flow",
                 graph_attr={"bgcolor": "white", "pad": "0.5"}):
        
        # User Journey Start
        with Cluster("User Journey"):
            user = User("Student")
            upload = Blank("Document\nUpload")
            learning = Blank("Interactive\nLearning")
            assessment = Blank("Quiz &\nAssessment")
            analytics = Blank("Progress\nTracking")
        
        # Processing Pipeline
        with Cluster("Content Processing Pipeline"):
            document_proc = Textract("Document\nExtraction")
            ai_processing = Bedrock("AI Content\nGeneration")
            lesson_gen = Lambda("Lesson\nGeneration")
            multimedia_gen = Lambda("Multimedia\nCreation")
        
        # Generated Content
        with Cluster("Generated Learning Content"):
            micro_lessons = Blank("Micro\nLessons")
            audio_content = Polly("Audio\nNarration")
            video_content = Blank("Video\nContent")
            quizzes = Blank("Adaptive\nQuizzes")
        
        # Learning Experience
        with Cluster("Adaptive Learning Experience"):
            chat_ai = Bedrock("AI Study\nBuddy")
            progress_tracking = Cloudwatch("Learning\nAnalytics")
            personalization = Lambda("Content\nPersonalization")
        
        # Data Storage
        with Cluster("Data Persistence"):
            user_data = DynamodbTable("User\nProfiles")
            content_data = DynamodbTable("Learning\nContent")
            analytics_data = DynamodbTable("Engagement\nMetrics")
            media_storage = S3("Media\nAssets")
        
        # Data Flow Connections
        user >> upload >> document_proc
        document_proc >> ai_processing
        ai_processing >> lesson_gen
        lesson_gen >> micro_lessons
        
        # Multimedia Generation
        lesson_gen >> multimedia_gen
        multimedia_gen >> audio_content
        multimedia_gen >> video_content
        
        # Quiz Generation
        ai_processing >> quizzes
        
        # Learning Experience
        user >> learning >> micro_lessons
        learning >> audio_content
        learning >> video_content
        learning >> chat_ai
        
        # Assessment Flow
        user >> assessment >> quizzes
        assessment >> progress_tracking
        
        # Analytics and Personalization
        progress_tracking >> analytics
        analytics >> personalization
        personalization >> ai_processing
        
        # Data Storage
        user >> user_data
        micro_lessons >> content_data
        audio_content >> media_storage
        video_content >> media_storage
        progress_tracking >> analytics_data
        chat_ai >> analytics_data

if __name__ == "__main__":
    print("🎨 Generating SnapStudy Architecture Diagrams...")
    
    try:
        print("📊 Creating architecture diagram...")
        create_architecture_diagram()
        print("✅ Architecture diagram created: snapstudy_architecture.png")
        
        print("🔄 Creating data flow diagram...")
        create_data_flow_diagram()
        print("✅ Data flow diagram created: snapstudy_data_flow.png")
        
        print("🎉 All diagrams generated successfully!")
        
    except Exception as e:
        print(f"❌ Error generating diagrams: {e}")
        print("💡 Make sure you have the 'diagrams' package installed:")
        print("   pip install diagrams")