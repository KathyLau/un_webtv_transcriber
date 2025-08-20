#!/usr/bin/env python3
"""
Test script to create a new Google Docs tab and write sample text into it.
"""

import sys
from pathlib import Path


def test_google_docs_create_tab():
    """Create a new tab in the specified Google Doc and write sample text."""

    # Check if Google Docs integration is available
    try:
        from google_docs_transcriber import GoogleDocsTranscriber
    except ImportError:
        print("❌ Google Docs integration not available")
        print("Please install: pip install -r requirements_google_docs.txt")
        return False

    # Document ID from user
    DOCUMENT_ID = "1xAtJeimO9Eoe-59IJNfFpV4i-MCG0i44KkNgr6Zjvf8"

    print("🧪 Testing Google Docs Tab Creation")
    print("=" * 50)
    print(f"Target Document ID: {DOCUMENT_ID}")

    try:
        # Initialize Google Docs transcriber
        print("\n📝 Initializing Google Docs integration...")
        transcriber = GoogleDocsTranscriber()

        # Authenticate
        print("🔐 Authenticating...")
        if not transcriber.authenticate():
            print("❌ Authentication failed")
            return False
        print("✅ Authentication successful!")

        # Open existing document
        print(f"\n📄 Opening existing document...")
        if not transcriber.open_existing_document(DOCUMENT_ID):
            print("❌ Failed to open document")
            return False
        print("✅ Document opened successfully!")
        print(f"📖 Document URL: {transcriber.get_document_url()}")

        # Write test content to the existing document
        print("\n📝 Writing test content to end of document (last tab if available)...")
        
        try:
            # Add a clear section separator and test content
            test_content = """


═══════════════════════════════════════════════════════════════════════════════
                                TEST CONTENT
═══════════════════════════════════════════════════════════════════════════════

This is a test to verify that the Google Docs integration is working correctly.

The quick brown fox jumps over the lazy dog. This pangram contains every letter of the English alphabet at least once.

Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

This test was performed to ensure that the live transcription system can successfully write to your existing Google Doc. If you can see this text, the integration is working perfectly! 🎉

═══════════════════════════════════════════════════════════════════════════════

"""
            
            # Append to the end of the last tab (falls back to first tab if tabs unsupported)
            if transcriber.append_text_to_last_tab(test_content):
                print("✅ Test content added successfully at end of document!")
            else:
                print("❌ Failed to add test content")
                return False
                
        except Exception as e:
            print(f"❌ Error adding test content: {e}")
            return False

        print("\n🎉 Test completed successfully!")
        print(f"📖 Check your document: {transcriber.get_document_url()}")
        print("\nYou should see:")
        print("- Content appended at the end of the document (last tab if present)")
        print("- A clearly separated 'TEST CONTENT' section")
        print("- Box-style borders around the test content")
        print("\nIf your doc has multiple tabs, content should appear in the final tab. Otherwise it will append to the body.")
        return True

    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False


def main():
    """Main function."""
    print("🚀 Google Docs Tab Creation Test")
    print("=" * 50)

    success = test_google_docs_create_tab()

    if success:
        print("\n✅ Test passed! A new tab was created and written to.")
    else:
        print("\n❌ Test failed. Please check the error messages above.")


if __name__ == "__main__":
    main()
