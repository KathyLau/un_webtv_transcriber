"""
Google Docs Live Transcription Integration

This module provides functionality to send live transcriptions to a Google Doc.
Requires Google Docs API setup and authentication.
"""

import os
import time
from pathlib import Path
from typing import Optional, List
import json

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    print("[warning] Google Docs integration not available. Install required packages:")
    print("  pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

# Google Docs API scopes
SCOPES = ['https://www.googleapis.com/auth/documents']

class GoogleDocsTranscriber:
    """
    Handles live transcription to Google Docs.
    """
    
    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.json"):
        """
        Initialize the Google Docs transcriber.
        
        Args:
            credentials_path: Path to your Google API credentials JSON file
            token_path: Path to store/load the OAuth token
        """
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.service = None
        self.document_id = None
        self.document_title = None
        
        if not GOOGLE_AVAILABLE:
            raise ImportError("Google Docs integration not available. Install required packages.")
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google Docs API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        creds = None
        
        # Load existing token if available
        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
            except Exception as e:
                print(f"[warning] Could not load existing token: {e}")
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"[warning] Could not refresh token: {e}")
                    creds = None
            
            if not creds:
                if not self.credentials_path.exists():
                    print(f"[error] Credentials file not found: {self.credentials_path}")
                    print("Please download your Google API credentials and save as 'credentials.json'")
                    return False
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), SCOPES)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    print(f"[error] Authentication failed: {e}")
                    return False
        
        # Save the credentials for next run
        try:
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        except Exception as e:
            print(f"[warning] Could not save token: {e}")
        
        # Build the service
        try:
            self.service = build('docs', 'v1', credentials=creds)
            print("[info] Successfully authenticated with Google Docs API")
            return True
        except Exception as e:
            print(f"[error] Could not build Google Docs service: {e}")
            return False
    
    def create_document(self, title: str = None) -> Optional[str]:
        """
        Create a new Google Doc for transcription.
        
        Args:
            title: Document title (default: "Live Transcription - {timestamp}")
            
        Returns:
            Document ID if successful, None otherwise
        """
        if not self.service:
            print("[error] Not authenticated. Call authenticate() first.")
            return None
        
        if not title:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            title = f"Live Transcription - {timestamp}"
        
        self.document_title = title
        
        try:
            document = {
                'title': title
            }
            doc = self.service.documents().create(body=document).execute()
            self.document_id = doc['documentId']
            print(f"[info] Created Google Doc: {title}")
            print(f"[info] Document URL: https://docs.google.com/document/d/{self.document_id}")
            return self.document_id
        except HttpError as e:
            print(f"[error] Failed to create Google Doc: {e}")
            return None
    
    def open_existing_document(self, document_id: str) -> bool:
        """
        Open an existing Google Doc for transcription.
        
        Args:
            document_id: The Google Doc ID to use
            
        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            print("[error] Not authenticated. Call authenticate() first.")
            return False
        
        try:
            doc = self.service.documents().get(documentId=document_id).execute()
            self.document_id = document_id
            self.document_title = doc.get('title')
            print(f"[info] Opened existing Google Doc: {self.document_title}")
            print(f"[info] Document URL: https://docs.google.com/document/d/{self.document_id}")
            return True
        except HttpError as e:
            print(f"[error] Failed to open Google Doc {document_id}: {e}")
            return False
    
    def append_text(self, text: str, timestamp: str = None) -> bool:
        """
        Append text to the Google Doc (defaults to first tab if tabs are present).
        """
        if not self.service or not self.document_id:
            print("[error] No document open. Call create_document() or open_existing_document() first.")
            return False
        
        if not text.strip():
            return True
        
        try:
            # Get current document to find end position (first tab or whole doc if no tabs)
            doc = self.service.documents().get(documentId=self.document_id).execute()
            body = doc.get('body') or {}
            content = body.get('content', [])
            end_index = (content[-1]['endIndex'] - 1) if content else 1
            
            # Prepare the text to insert
            if timestamp:
                insert_text = f"\n[{timestamp}] {text}"
            else:
                insert_text = f"\n{text}"
            
            # Insert the text (no tabId specified: targets first tab)
            requests = [
                {
                    'insertText': {
                        'location': {
                            'index': end_index
                        },
                        'text': insert_text
                    }
                }
            ]
            
            self.service.documents().batchUpdate(
                documentId=self.document_id,
                body={'requests': requests}
            ).execute()
            
            return True
            
        except HttpError as e:
            print(f"[error] Failed to append text to Google Doc: {e}")
            return False
    
    def append_transcription_segment(self, text: str, start_time: str, end_time: str) -> bool:
        """
        Append a transcription segment with timing information.
        
        Args:
            text: Transcribed text
            start_time: Start timestamp (HH:MM:SS,mmm format)
            end_time: End timestamp (HH:MM:SS,mmm format)
            
        Returns:
            True if successful, False otherwise
        """
        if not text.strip():
            return True
        
        timestamp = f"{start_time} → {end_time}"
        # Prefer appending to the end of the last tab if available; fallback to first tab
        return self.append_text_to_last_tab(text, timestamp)
    
    # ---- New tab-aware helpers ----
    def _get_all_tabs(self) -> List[dict]:
        """Return a flat list of all tabs in UI order. Requires tabs-enabled Docs API."""
        doc = self.service.documents().get(documentId=self.document_id, includeTabsContent=True).execute()
        all_tabs: List[dict] = []
        
        def add_with_children(tab: dict):
            all_tabs.append(tab)
            for child in tab.get('childTabs', []) or []:
                add_with_children(child)
        
        for tab in doc.get('tabs', []) or []:
            add_with_children(tab)
        return all_tabs
    
    def append_text_to_tab(self, text: str, tab_id: str, timestamp: str = None) -> bool:
        """Append text to a specific tab by tab_id, at the end of that tab."""
        if not self.service or not self.document_id:
            print("[error] No document open. Call create_document() or open_existing_document() first.")
            return False
        if not text.strip():
            return True
        try:
            doc = self.service.documents().get(documentId=self.document_id, includeTabsContent=True).execute()
            target_tab = None
            for tab in doc.get('tabs', []) or []:
                # flatten
                stack = [tab]
                while stack:
                    t = stack.pop()
                    if t.get('tabProperties', {}).get('tabId') == tab_id:
                        target_tab = t
                        stack = []
                        break
                    for child in t.get('childTabs', []) or []:
                        stack.append(child)
                if target_tab:
                    break
            if not target_tab:
                print(f"[warning] Tab id {tab_id} not found; falling back to first tab")
                return self.append_text(text, timestamp)
            body = (target_tab.get('documentTab') or {}).get('body') or {}
            content = body.get('content', [])
            end_index = (content[-1]['endIndex'] - 1) if content else 1
            insert_text = f"\n[{timestamp}] {text}" if timestamp else f"\n{text}"
            requests = [
                {
                    'insertText': {
                        'location': {
                            'tabId': tab_id,
                            'index': end_index
                        },
                        'text': insert_text
                    }
                }
            ]
            self.service.documents().batchUpdate(documentId=self.document_id, body={'requests': requests}).execute()
            return True
        except HttpError as e:
            print(f"[error] Failed to append text to tab: {e}")
            return False
        except TypeError as e:
            # includeTabsContent might not be supported; fall back
            print(f"[warning] Tabs API not available in client: {e}")
            return self.append_text(text, timestamp)
    
    def append_text_to_last_tab(self, text: str, timestamp: str = None) -> bool:
        """Append text to the end of the last tab in the document. Falls back to first tab."""
        try:
            tabs = self._get_all_tabs()
            if not tabs:
                print("[info] No tabs detected; appending to first tab")
                return self.append_text(text, timestamp)
            last_tab = tabs[-1]
            tab_id = (last_tab.get('tabProperties') or {}).get('tabId')
            if not tab_id:
                print("[warning] Last tab has no tabId; appending to first tab")
                return self.append_text(text, timestamp)
            return self.append_text_to_tab(text, tab_id, timestamp)
        except HttpError as e:
            print(f"[warning] Tabs retrieval failed: {e}; appending to first tab")
            return self.append_text(text, timestamp)
        except TypeError as e:
            print(f"[warning] Tabs API not supported by client: {e}; appending to first tab")
            return self.append_text(text, timestamp)
    
    def get_document_url(self) -> Optional[str]:
        """
        Get the URL of the current document.
        
        Returns:
            Document URL if available, None otherwise
        """
        if self.document_id:
            return f"https://docs.google.com/document/d/{self.document_id}"
        return None
    
    def close(self):
        """Clean up resources."""
        if self.service:
            self.service.close()
            self.service = None


def setup_google_docs_integration(credentials_path: str = "credentials.json") -> Optional[GoogleDocsTranscriber]:
    """
    Helper function to set up Google Docs integration.
    
    Args:
        credentials_path: Path to Google API credentials file
        
    Returns:
        Configured GoogleDocsTranscriber instance if successful, None otherwise
    """
    if not GOOGLE_AVAILABLE:
        print("[warning] Google Docs integration not available")
        return None
    
    try:
        transcriber = GoogleDocsTranscriber(credentials_path)
        if transcriber.authenticate():
            return transcriber
        else:
            print("[error] Google Docs authentication failed")
            return None
    except Exception as e:
        print(f"[error] Failed to setup Google Docs integration: {e}")
        return None


# Example usage and testing
if __name__ == "__main__":
    print("Google Docs Transcriber Module")
    print("=" * 40)
    
    if not GOOGLE_AVAILABLE:
        print("Required packages not installed. Run:")
        print("pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    else:
        print("Google Docs integration is available!")
        print("\nTo use this module:")
        print("1. Set up Google Cloud Project and enable Docs API")
        print("2. Download credentials.json from Google Cloud Console")
        print("3. Import and use in your main script")
