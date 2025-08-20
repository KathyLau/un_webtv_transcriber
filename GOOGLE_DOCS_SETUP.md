# Google Docs Live Transcription Setup Guide

This guide will help you set up live transcription to Google Docs using the Google Docs API.

## Prerequisites

- Python 3.7+
- Google account
- Google Cloud Project (free tier available)

## Step 1: Install Dependencies

Install the required Google API packages:

```bash
pip install -r requirements_google_docs.txt
```

Or install manually:

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

## Step 2: Set Up Google Cloud Project

1. **Go to [Google Cloud Console](https://console.cloud.google.com/)**
2. **Create a new project** or select an existing one
3. **Enable the Google Docs API:**
   - Go to "APIs & Services" > "Library"
   - Search for "Google Docs API"
   - Click on it and press "Enable"

## Step 3: Create Credentials

1. **Go to "APIs & Services" > "Credentials"**
2. **Click "Create Credentials" > "OAuth 2.0 Client IDs"**
3. **Choose "Desktop application"** (since you're running locally)
4. **Give it a name** (e.g., "Live Transcription")
5. **Download the JSON file** and save it as `credentials.json` in your project directory

## Step 4: First Run Authentication

When you first run the script with Google Docs integration:

1. **The script will open a browser window**
2. **Sign in with your Google account**
3. **Grant permission** to access your Google Docs
4. **A token file will be saved** for future use

## Step 5: Integration with Your Script

### Option 1: Minimal Integration (Recommended)

Add these few lines to your main transcription script:

```python
# At the top of your file
from google_docs_transcriber import setup_google_docs_integration

# In your main function, after argument parsing
google_transcriber = setup_google_docs_integration()

# In your transcribe_loop, after processing each segment
if google_transcriber and text.strip():
    google_transcriber.append_transcription_segment(text, ts_format(start), ts_format(end))

# At the end, clean up
if google_transcriber:
    google_transcriber.close()
```

### Option 2: Full Integration

See `example_google_docs_integration.py` for a complete example of how to modify your script.

## File Structure

After setup, your project should look like:

```
bbnj/
├── live_un_transcriber.py          # Your main script
├── google_docs_transcriber.py      # Google Docs integration module
├── requirements_google_docs.txt     # Google Docs dependencies
├── example_google_docs_integration.py  # Integration examples
├── GOOGLE_DOCS_SETUP.md            # This setup guide
├── credentials.json                 # Your Google API credentials
├── token.json                      # OAuth token (created automatically)
└── un_webtv_capture/              # Transcription output folders
```

## Usage Examples

### Basic Usage

```python
from google_docs_transcriber import GoogleDocsTranscriber

# Set up and authenticate
transcriber = GoogleDocsTranscriber()
transcriber.authenticate()

# Create a new document
doc_id = transcriber.create_document("Live UN Meeting Transcription")

# Send transcriptions
transcriber.append_transcription_segment(
    "Hello, welcome to the meeting.", 
    "00:00:00,000", 
    "00:00:03,500"
)

# Get the document URL
print(f"Live document: {transcriber.get_document_url()}")
```

### Advanced Usage

```python
# Open an existing document
transcriber.open_existing_document("your_document_id_here")

# Append plain text
transcriber.append_text("Additional notes here")

# Custom document title
transcriber.create_document("Custom Meeting Title")
```

## Troubleshooting

### Common Issues

1. **"Credentials file not found"**
   - Make sure `credentials.json` is in your project directory
   - Check the file path in your code

2. **"Authentication failed"**
   - Delete `token.json` and try again
   - Make sure you have internet access
   - Check that the Google Docs API is enabled

3. **"Permission denied"**
   - Make sure you granted permission in the browser
   - Check that your Google account has access to Google Docs

4. **"API quota exceeded"**
   - Google Docs API has generous free limits
   - Check your Google Cloud Console for usage

### Getting Help

- Check the [Google Docs API documentation](https://developers.google.com/docs/api)
- Verify your credentials in [Google Cloud Console](https://console.cloud.google.com/)
- Check the console output for specific error messages

## Security Notes

- **Never commit `credentials.json` or `token.json` to version control**
- **Add them to your `.gitignore` file**
- **The token file contains sensitive authentication data**
- **Credentials are tied to your Google account**

## Performance Considerations

- **Google Docs API has rate limits** (but they're generous)
- **Each API call adds a small delay** to transcription
- **Consider batching multiple segments** if you need higher performance
- **The integration gracefully handles API failures** and continues with local files

## Next Steps

1. **Test the integration** with a short transcription
2. **Customize the document format** if needed
3. **Add error handling** for your specific use case
4. **Consider adding timestamps** or other metadata

Happy transcribing! 🎤📝
