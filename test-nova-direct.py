#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append(os.path.join('backend', 'src'))

from backend.src.services.bedrock import BedrockService

async def test_nova_direct():
    print("Testing Nova directly...")
    bedrock = BedrockService()
    
    test_prompts = [
        "What is 2+2?",
        "Explain photosynthesis in simple terms",
        "Hello, how are you?"
    ]
    
    for prompt in test_prompts:
        print(f"\nPrompt: {prompt}")
        try:
            response = await bedrock.invoke_claude(prompt, max_tokens=200, temperature=0.7)
            print(f"Response: {response[:200]}...")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_nova_direct())