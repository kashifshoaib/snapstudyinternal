#!/usr/bin/env python3
"""
Script to adjust Bedrock throttling settings on a running server.
"""

import requests
import sys
import json


def adjust_throttling(api_url: str, interval: float):
    """Adjust the throttling interval."""
    try:
        response = requests.post(
            f"{api_url}/api/v1/health/adjust-throttling",
            params={"interval_seconds": interval}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Successfully adjusted throttling interval to {interval}s")
            print(f"📊 Current stats: {json.dumps(data['current_stats'], indent=2)}")
        else:
            print(f"❌ Failed to adjust throttling: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error adjusting throttling: {e}")


def get_status(api_url: str):
    """Get current throttling status."""
    try:
        response = requests.get(f"{api_url}/api/v1/health/throttling-status")
        
        if response.status_code == 200:
            data = response.json()
            coordinator = data.get('coordinator', {})
            
            print("📊 Current Throttling Status:")
            print(f"   Total requests: {coordinator.get('total_requests', 0)}")
            print(f"   Throttled requests: {coordinator.get('throttled_requests', 0)}")
            print(f"   Throttle rate: {coordinator.get('throttle_rate', 0):.1f}%")
            print(f"   Current interval: {coordinator.get('current_min_interval', 0):.2f}s")
            print(f"   Time since last request: {coordinator.get('time_since_last_request', 0):.2f}s")
            
        else:
            print(f"❌ Failed to get status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error getting status: {e}")


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage:")
        print(f"  {sys.argv[0]} status [api_url]")
        print(f"  {sys.argv[0]} adjust <interval> [api_url]")
        print()
        print("Examples:")
        print(f"  {sys.argv[0]} status")
        print(f"  {sys.argv[0]} adjust 3.0")
        print(f"  {sys.argv[0]} adjust 1.5 http://localhost:8000")
        sys.exit(1)
    
    command = sys.argv[1]
    api_url = "http://localhost:8000"
    
    if command == "status":
        if len(sys.argv) > 2:
            api_url = sys.argv[2]
        get_status(api_url)
        
    elif command == "adjust":
        if len(sys.argv) < 3:
            print("❌ Please specify interval seconds")
            sys.exit(1)
        
        try:
            interval = float(sys.argv[2])
        except ValueError:
            print("❌ Invalid interval value")
            sys.exit(1)
        
        if len(sys.argv) > 3:
            api_url = sys.argv[3]
        
        adjust_throttling(api_url, interval)
        
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()