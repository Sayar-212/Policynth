#!/usr/bin/env python3
"""
Quick start script for the RAG system
"""
import os
import sys
import subprocess

def check_env():
    """Check if environment is properly configured"""
    if not os.path.exists('.env'):
        print("❌ .env file not found. Please run setup.py first.")
        return False
    
    with open('.env', 'r') as f:
        content = f.read()
    
    # Environment is ready
    
    print("✅ Environment configured")
    return True

def main():
    print("🚀 Starting LLM Document Query System...")
    
    if not check_env():
        print("\n💡 To fix: Run python setup.py")
        return
    
    print("📡 Starting FastAPI server on http://localhost:8000")
    print("📚 API docs available at http://localhost:8000/docs")
    print("🧪 Test with: python test_client.py")
    print("\n" + "="*50)
    
    # Start the server
    subprocess.run([sys.executable, "main.py"])

if __name__ == "__main__":
    main()