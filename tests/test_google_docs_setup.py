#!/usr/bin/env python3
"""
Test script to verify Google Docs integration setup.
Run this to check if everything is configured correctly.
"""

import os
from pathlib import Path

def check_setup():
    """Check the current setup status."""
    print("🔍 Google Docs Integration Setup Check")
    print("=" * 50)
    
    # Check if required packages are installed
    print("\n📦 Checking Python packages...")
    try:
        import google.auth
        import google_auth_oauthlib
        import googleapiclient
        print("✅ Google API packages are installed")
    except ImportError as e:
        print(f"❌ Missing packages: {e}")
        print("   Run: pip install -r requirements_google_docs.txt")
        return False
    
    # Check for credentials file
    print("\n🔑 Checking credentials...")
    credentials_path = Path("credentials.json")
    if credentials_path.exists():
        print("✅ credentials.json found")
        print(f"   Size: {credentials_path.stat().st_size} bytes")
    else:
        print("❌ credentials.json NOT found")
        print("   You need to:")
        print("   1. Go to Google Cloud Console")
        print("   2. Create OAuth 2.0 credentials")
        print("   3. Download as credentials.json")
        print("   4. Save in this directory")
        return False
    
    # Check for token file
    print("\n🎫 Checking authentication token...")
    token_path = Path("token.json")
    if token_path.exists():
        print("✅ token.json found (you're already authenticated)")
        print(f"   Size: {token_path.stat().st_size} bytes")
    else:
        print("⚠️  token.json not found (will be created on first run)")
    
    # Check file permissions
    print("\n🔒 Checking file permissions...")
    try:
        with open(credentials_path, 'r') as f:
            creds_content = f.read()
            if '"client_id"' in creds_content and '"client_secret"' in creds_content:
                print("✅ credentials.json appears to be valid")
            else:
                print("❌ credentials.json doesn't look like valid OAuth credentials")
                return False
    except Exception as e:
        print(f"❌ Error reading credentials.json: {e}")
        return False
    
    print("\n🎉 Setup looks good! You can now test the integration.")
    return True

def test_google_docs_integration():
    """Test the actual Google Docs integration."""
    print("\n🧪 Testing Google Docs Integration...")
    print("=" * 50)
    
    try:
        from google_docs_transcriber import setup_google_docs_integration
        
        print("📝 Attempting to authenticate...")
        transcriber = setup_google_docs_integration()
        
        if transcriber:
            print("✅ Authentication successful!")
            
            print("📄 Creating test document...")
            doc_id = transcriber.create_document("Test Transcription - Setup Verification")
            
            if doc_id:
                print(f"✅ Test document created!")
                print(f"   Document ID: {doc_id}")
                print(f"   URL: {transcriber.get_document_url()}")
                
                print("✍️  Adding test text...")
                success = transcriber.append_text("This is a test transcription to verify the setup is working correctly.")
                
                if success:
                    print("✅ Test text added successfully!")
                    print("🎯 Google Docs integration is fully working!")
                else:
                    print("❌ Failed to add test text")
                
                # Clean up
                transcriber.close()
            else:
                print("❌ Failed to create test document")
        else:
            print("❌ Authentication failed")
            return False
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False
    
    return True

def main():
    """Main test function."""
    print("🚀 Google Docs Integration Test Suite")
    print("=" * 50)
    
    # Check basic setup
    if not check_setup():
        print("\n❌ Setup check failed. Please fix the issues above and try again.")
        return
    
    # Test the integration
    if test_google_docs_integration():
        print("\n🎉 All tests passed! Your Google Docs integration is ready to use.")
        print("\nNext steps:")
        print("1. Integrate with your main transcription script")
        print("2. Run a real transcription session")
        print("3. Watch transcriptions appear in Google Docs in real-time!")
    else:
        print("\n❌ Integration test failed. Check the error messages above.")

if __name__ == "__main__":
    main()
