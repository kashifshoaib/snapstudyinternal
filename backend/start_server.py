#!/usr/bin/env python3
"""
Simple script to start the FastAPI development server.
"""

import os
import sys
import subprocess

def main():
    """Start the FastAPI development server."""
    print("🚀 Starting SnapStudy FastAPI Development Server")
    print("=" * 50)
    
    # Add src to Python path
    src_path = os.path.join(os.path.dirname(__file__), 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    # Check if uvicorn is available
    try:
        import uvicorn
        print("✅ uvicorn found")
    except ImportError:
        print("❌ uvicorn not found. Installing...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'uvicorn[standard]'])
            import uvicorn
            print("✅ uvicorn installed successfully")
        except Exception as e:
            print(f"❌ Failed to install uvicorn: {e}")
            print("Please install manually: pip install uvicorn[standard]")
            return
    
    # Set environment variables
    os.environ.setdefault('AWS_REGION', 'us-east-1')
    
    print("🌐 Server will be available at:")
    print("   - Local: http://localhost:8000")
    print("   - API Docs: http://localhost:8000/docs")
    print("   - ReDoc: http://localhost:8000/redoc")
    print()
    print("📡 AI Services endpoints:")
    print("   - Health Check: http://localhost:8000/api/v1/ai/health-check")
    print("   - Test Bedrock: http://localhost:8000/api/v1/ai/test-bedrock")
    print("   - Test Content Analysis: http://localhost:8000/api/v1/ai/test-content-analysis")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        # Start the server
        # Use reload only in development (not in production containers)
        is_development = os.getenv('ENVIRONMENT', 'development') == 'development'
        
        uvicorn.run(
            "src.api.main:app",
            host="0.0.0.0",
            port=8000,
            reload=is_development,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")


if __name__ == "__main__":
    main()