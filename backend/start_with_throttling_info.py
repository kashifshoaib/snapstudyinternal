#!/usr/bin/env python3
"""
Start the server with throttling configuration information.
"""

import os
import sys
import subprocess
import time

def print_throttling_config():
    """Print current throttling configuration."""
    print("\n" + "="*60)
    print("🔧 BEDROCK THROTTLING CONFIGURATION")
    print("="*60)
    
    print("📊 Rate Limits:")
    print(f"   Max RPM: {os.getenv('BEDROCK_MAX_RPM', '80')}")
    print(f"   Agent Max RPM: {os.getenv('BEDROCK_AGENT_MAX_RPM', '40')}")
    print(f"   Model Max RPM: {os.getenv('BEDROCK_MODEL_MAX_RPM', '60')}")
    print(f"   Burst Capacity: {os.getenv('BEDROCK_BURST_CAPACITY', '10')}")
    
    print("\n🕐 Request Coordination:")
    print(f"   Max Concurrent: {os.getenv('MAX_CONCURRENT_REQUESTS', '2')}")
    print(f"   Processing Delay: {os.getenv('REQUEST_PROCESSING_DELAY', '0.8')}s")
    print(f"   Coordinator Min Interval: 4.0s (hardcoded)")
    
    print("\n🔄 Retry Configuration:")
    print(f"   Max Retries: 6")
    print(f"   Base Delay: 2.0s")
    print(f"   Max Delay: 120.0s")
    print(f"   Backoff Multiplier: 2.5x")
    
    print("\n📡 Monitoring Endpoints:")
    print(f"   Health: http://localhost:8000/api/v1/health/")
    print(f"   Throttling Status: http://localhost:8000/api/v1/health/throttling-status")
    print(f"   Bedrock Health: http://localhost:8000/api/v1/health/bedrock")
    
    print("\n🛠️  Management Commands:")
    print(f"   Check Status: python backend/adjust_throttling.py status")
    print(f"   Adjust Interval: python backend/adjust_throttling.py adjust 5.0")
    print(f"   Quick Test: python backend/quick_test.py")
    
    print("="*60)
    print("🚀 Starting server with throttling protection enabled...")
    print("="*60 + "\n")


def main():
    """Main function."""
    print_throttling_config()
    
    # Change to backend directory
    os.chdir('backend')
    
    # Start the server
    try:
        subprocess.run([
            sys.executable, '-m', 'uvicorn', 
            'src.api.main:app', 
            '--reload', 
            '--host', '0.0.0.0', 
            '--port', '8000'
        ])
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")


if __name__ == "__main__":
    main()