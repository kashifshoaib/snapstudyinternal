#!/usr/bin/env python3
"""
Beanstalk entry point for SnapStudy FastAPI application.
Uses a2wsgi to wrap ASGI app for WSGI compatibility.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # Add src to Python path
    src_path = os.path.join(os.path.dirname(__file__), 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    logger.info(f"Added {src_path} to Python path")
    
    # Set environment variables
    os.environ.setdefault('ENVIRONMENT', 'production')
    os.environ.setdefault('AWS_REGION', 'us-east-1')
    
    # Import the FastAPI app
    logger.info("Importing FastAPI app...")
    from src.api.main import app
    
    # Use a2wsgi to wrap ASGI app for WSGI compatibility
    from a2wsgi import ASGIMiddleware
    application = ASGIMiddleware(app)
    
    logger.info("FastAPI app wrapped with a2wsgi successfully")
    
except Exception as e:
    logger.error(f"Failed to import FastAPI app: {str(e)}")
    import traceback
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Store error for fallback
    startup_error = str(e)
    
    # Create a simple WSGI fallback
    def application(environ, start_response):
        status = '200 OK'
        headers = [('Content-type', 'application/json')]
        start_response(status, headers)
        response_body = f'{{"message": "SnapStudy API - Fallback Mode", "error": "{startup_error}"}}'
        return [response_body.encode('utf-8')]

if __name__ == "__main__":
    import uvicorn
    # For local testing, run the ASGI app directly
    try:
        from src.api.main import app
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except:
        print("FastAPI app not available for local testing")