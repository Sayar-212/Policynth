import subprocess
import sys
import os

def install_requirements():
    """Install required packages"""
    print("Installing requirements...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def verify_env_file():
    """Verify .env file has required keys"""
    print("Verifying environment configuration...")
    
    required_keys = [
        "GEMINI_API_KEY",
        "PINECONE_API_KEY", 
        "PINECONE_INDEX_NAME"
    ]
    
    if not os.path.exists(".env"):
        print("ERROR: .env file not found!")
        return False
    
    with open(".env", "r") as f:
        env_content = f.read()
    
    missing_keys = []
    for key in required_keys:
        if key not in env_content or f"{key}=your_" in env_content:
            missing_keys.append(key)
    
    if missing_keys:
        print(f"ERROR: Missing or placeholder values for: {', '.join(missing_keys)}")
        print("Please update your .env file with actual API keys")
        return False
    
    print("Environment configuration verified!")
    return True

def main():
    """Main setup function"""
    print("=== LLM Document Query System Setup ===")
    
    try:
        # Install requirements
        install_requirements()
        
        # Verify environment
        if not verify_env_file():
            print("\nSetup incomplete. Please fix environment configuration.")
            return
        
        print("\n=== Setup Complete! ===")
        print("To start the system:")
        print("1. Run: python main.py")
        print("2. Test with: python test_client.py")
        print("3. API will be available at: http://localhost:8000")
        print("4. Documentation at: http://localhost:8000/docs")
        
    except Exception as e:
        print(f"Setup failed: {e}")

if __name__ == "__main__":
    main()