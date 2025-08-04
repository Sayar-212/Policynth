#!/usr/bin/env python3
"""
Test script for Policynth API with authentication
"""

import requests
import json

# API Configuration
BASE_URL = "http://localhost:8000/api/v1"
BEARER_TOKEN = "16bf0d621ee347f1a4b56589f04b1d3430e0b93e3a4faa109f64b4789400e9d8"

def test_api():
    """Test the Policynth API with authentication"""
    
    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Sample request
    payload = {
        "documents": "https://hackrx.blob.core.windows.net/assets/hackrx_6/policies/BAJHLIP23020V012223.pdf?sv=2023-01-03&st=2025-07-30T06%3A46%3A49Z&se=2025-09-01T06%3A46%3A00Z&sr=c&sp=rl&sig=9szykRKdGYj0BVm1skP%2BX8N9%2FRENEn2k7MQPUp33jyQ%3D",
        "questions": [
            "What is the definition of Accident?",
            "How many days of post-hospitalization expenses are covered?"
        ]
    }
    
    print("🧪 Testing Policynth API with Authentication")
    print("=" * 50)
    
    try:
        response = requests.post(
            f"{BASE_URL}/hackrx/run",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API Request Successful!")
            print(f"📋 Answers received: {len(result['answers'])}")
            
            for i, answer in enumerate(result['answers'], 1):
                print(f"\n{i}. Q: {payload['questions'][i-1]}")
                print(f"   A: {answer}")
        
        elif response.status_code == 401:
            print("❌ Authentication Failed - Invalid Bearer Token")
        
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Request Failed: {e}")

def test_invalid_token():
    """Test with invalid token"""
    
    headers = {
        "Authorization": "Bearer invalid_token_123",
        "Content-Type": "application/json"
    }
    
    payload = {
        "documents": "https://example.com/test.pdf",
        "questions": ["Test question?"]
    }
    
    print("\n🔒 Testing Invalid Token")
    print("=" * 30)
    
    try:
        response = requests.post(
            f"{BASE_URL}/hackrx/run",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 401:
            print("✅ Authentication properly rejected invalid token")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Request Failed: {e}")

if __name__ == "__main__":
    test_api()
    test_invalid_token()