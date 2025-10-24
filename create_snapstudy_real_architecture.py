#!/usr/bin/env python3
"""
SnapStudy Real Architecture Diagram Generator
Creates the actual architecture diagram based on the real implementation
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import Lightsail
from diagrams.aws.storage import S3
from diagrams.aws.network import CloudFront
from diagrams.aws.ml import Bedrock, Textract, Transcribe, Polly
from diagrams.aws.database import Dynamodb
from diagrams.onprem.client import Users
from diagrams.programming.framework import React

def create_snapstudy_real_architecture():
    """Create the actual SnapStudy architecture diagram"""
    
    with Diagram("SnapStudy - Actual Implementation Architecture", 
                 show=False, 
                 direction="TB",
                 filename="snapstudy_real_architecture",
                 graph_attr={"bgcolor": "white", "pad": "1.0"}):
        
        # Users
        students = Users("Students & Educators")
        
        # Frontend Deployment
        with Cluster("Frontend Deployment"):
            react_app = React("React UI")
            s3_frontend = S3("S3 Static Hosting")
            cloudfront = CloudFront("CloudFront CDN")
        
        # Backend Deployment
        with Cluster("Backend Deployment"):
            lightsail = Lightsail("Lightsail Docker")
        
        # AI Agent System - CORE INNOVATION
        with Cluster("Bedrock AI Agent System"):
            # Bedrock AgentCore
            agent_core = Bedrock("Bedrock AgentCore")
            
            # Bedrock Agents
            learning_agent = Bedrock("Learning Agent")
            adaptive_agent = Bedrock("Adaptive Agent")
            
            # Bedrock Foundation Models
            bedrock_claude = Bedrock("Claude 3.5 Sonnet")
            bedrock_nova = Bedrock("Nova Pro")
            
            # Bedrock Services
            knowledge_base = Bedrock("Knowledge Base")
            guardrails = Bedrock("Guardrails")
        
        # AI/ML Processing Services
        with Cluster("AI/ML Processing"):
            textract = Textract("Textract")
            transcribe = Transcribe("Transcribe")
            polly = Polly("Polly")
        
        # Data Storage
        with Cluster("Data Storage"):
            # DynamoDB - 8 Tables
            dynamodb = Dynamodb("DynamoDB")
            
            # S3 Storage
            content_bucket = S3("Content Storage")
            audio_bucket = S3("Audio Storage")
        
        # User Access Flow
        students >> Edge(label="Access URL", color="blue") >> cloudfront
        cloudfront >> s3_frontend
        s3_frontend >> react_app
        
        # Backend API Flow
        react_app >> Edge(label="API Calls", color="green") >> lightsail
        
        # AI Agent Orchestration - CORE FEATURE
        lightsail >> Edge(label="Agent Requests", color="purple", style="bold") >> agent_core
        agent_core >> Edge(color="purple") >> learning_agent
        agent_core >> Edge(color="purple") >> adaptive_agent
        
        # Agent Interactions with Bedrock Services
        learning_agent >> Edge(label="RAG", color="orange") >> knowledge_base
        adaptive_agent >> Edge(label="RAG", color="orange") >> knowledge_base
        learning_agent >> Edge(label="Safety", color="red") >> guardrails
        adaptive_agent >> Edge(label="Safety", color="red") >> guardrails
        
        # Foundation Model Access
        learning_agent >> Edge(label="Text Gen", color="purple") >> bedrock_claude
        adaptive_agent >> Edge(label="Text Gen", color="purple") >> bedrock_claude
        learning_agent >> Edge(label="Multimodal", color="purple") >> bedrock_nova
        adaptive_agent >> Edge(label="Multimodal", color="purple") >> bedrock_nova
        
        # AI Processing Services
        lightsail >> Edge(label="OCR", color="orange") >> textract
        lightsail >> Edge(label="Speech", color="orange") >> transcribe
        lightsail >> Edge(label="TTS", color="orange") >> polly
        
        # Data Storage Access
        lightsail >> Edge(label="CRUD Ops", color="blue") >> dynamodb
        learning_agent >> Edge(label="Profile Data", color="blue") >> dynamodb
        adaptive_agent >> Edge(label="Analytics", color="blue") >> dynamodb
        
        # File Storage
        lightsail >> Edge(label="Upload/Download", color="green") >> content_bucket
        polly >> Edge(label="Audio Files", color="green") >> audio_bucket

if __name__ == "__main__":
    print("🎨 Generating SnapStudy Actual Implementation Architecture...")
    
    try:
        create_snapstudy_real_architecture()
        print("✅ Actual architecture diagram created: snapstudy_real_architecture.png")
        print("📊 Architecture Components:")
        print("   • Frontend: React UI on S3 + CloudFront")
        print("   • Backend: Lightsail Docker deployment")
        print("   • AI: Bedrock AgentCore with Learning & Adaptive Agents")
        print("   • Models: Claude 3.5 Sonnet + Nova Pro")
        print("   • Storage: DynamoDB (8 tables) + S3 buckets")
        print("   • AI Services: Textract, Transcribe, Polly")
        
    except Exception as e:
        print(f"❌ Error generating diagram: {e}")
        import traceback
        traceback.print_exc()