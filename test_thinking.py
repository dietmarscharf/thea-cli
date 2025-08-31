#!/usr/bin/env python3
"""Test different approaches to enable model thinking."""

import sys
import os
sys.path.insert(0, '/mnt/c/Projects/THEA')
from thea import process_with_model, pdf_to_base64_images, build_system_prompt, build_user_prompt, load_prompt_file

# Test file
test_pdf = "Belege/Konto_0021504006-Auszug_2022_0003.pdf"

# Test variations
test_prompts = [
    {
        "name": "Test 1: Explicit thinking instruction",
        "system": "You must use <thinking></thinking> tags for your analysis. First, wrap all your reasoning in <thinking> tags. Then provide JSON output.",
        "user": "Analyze this document. Start with <thinking> tags for your step-by-step analysis.",
        "format_mode": None
    },
    {
        "name": "Test 2: Chain of thought prompt",
        "system": "You are an AI that always shows its thinking process. Use <thinking> tags to show your reasoning before answering.",
        "user": "Let's think step by step. Use <thinking> tags to show your analysis of this bank statement.",
        "format_mode": None
    },
    {
        "name": "Test 3: No format restriction at all",
        "system": "Think freely and show your work. Use <thinking> tags for reasoning.",
        "user": "Analyze this bank statement. Think out loud in <thinking> tags first.",
        "format_mode": None
    },
    {
        "name": "Test 4: Format json with thinking request",
        "system": "Use <thinking> tags for analysis. Output JSON after thinking.",
        "user": "Show thinking in tags, then JSON.",
        "format_mode": "json"
    }
]

print("=== Testing Different Thinking Approaches ===\n")

# Get images
base64_images, pil_images = pdf_to_base64_images(test_pdf, dpi=150)
if not base64_images:
    print("Failed to load images")
    sys.exit(1)

for i, test in enumerate(test_prompts, 1):
    print(f"\n{'='*60}")
    print(f"Test {i}: {test['name']}")
    print(f"System: {test['system'][:100]}...")
    print(f"User: {test['user'][:100]}...")
    print(f"Format mode: {test['format_mode']}")
    print(f"{'='*60}")
    
    # Run a mini test
    import requests
    import json
    
    messages = [
        {"role": "system", "content": test['system']},
        {"role": "user", "content": test['user'], "images": base64_images}
    ]
    
    payload = {
        "model": "gemma3:27b",
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 500  # Short response for testing
        }
    }
    
    if test['format_mode'] == 'json':
        payload["format"] = "json"
    
    print("Sending request...")
    try:
        response = requests.post(
            "https://b1s.hey.bahn.business/api/chat",
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        if 'message' in result and 'content' in result['message']:
            content = result['message']['content']
            print(f"\nResponse preview (first 300 chars):")
            print(content[:300])
            
            # Check for thinking tags
            has_thinking = '<thinking>' in content
            print(f"\nContains <thinking> tags: {has_thinking}")
            
            if has_thinking:
                start = content.find('<thinking>')
                end = content.find('</thinking>')
                if end > start:
                    thinking_content = content[start+10:end]
                    print(f"Thinking content (first 200 chars): {thinking_content[:200]}...")
        else:
            print("No content in response")
            
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*60)

print("\n=== Test Complete ===")