# UN WebTV Live Transcription Manual

This guide explains how to capture the live HLS URL from UN WebTV and run the transcription script with optional Google Docs integration.

---

## Step 1: Install prerequisites
-------------------------------------

1. Install Python 3.13 (or a compatible version).  
2. Install `ffmpeg`:
   - **macOS**: `brew install ffmpeg`  
   - **Ubuntu**: `sudo apt install ffmpeg`  
3. Install Python dependencies:

```bash
pip install -r requirements.txt
python -m playwright install
```

### Optional: Google Docs Integration

To enable live transcription to Google Docs:

```bash
pip install -r requirements_google_docs.txt
```

Then follow the [Google Docs Setup Guide](GOOGLE_DOCS_SETUP.md) to configure your credentials.

---

## Step 2: Capture the HLS (`.m3u8`) URL
-------------------------------------

1.  Open the UN WebTV page in a browser, e.g.:\
    `https://webtv.un.org/en/asset/k1z/k1zoobol5v`

2.  Open **Developer Tools** (usually `F12` or `Cmd+Option+I` / `Ctrl+Shift+I`).

3.  Go to the **Network** tab.

4.  In the filter box, type:

`m3u8`

1.  Click the **Play** button on the video.

2.  Look for a network request ending in `.m3u8`.

3.  Right-click the request → **Copy → Copy link address**.

4.  Keep this URL --- it is needed for the transcription script.

---

## Step 3: Activate the virtual environment
----------------------------------------

If not already active:

`source venv/bin/activate`

---

## Step 4: Run the transcription script
------------------------------------

### Basic Usage

Use the captured `.m3u8` URL as `URL` in the command below:

```bash
python live_un_transcriber.py URL --language en
```

### With Google Docs Integration

#### Option 1: Create New Google Doc (Default)
```bash
python live_un_transcriber.py "https://webtv.un.org/..." --language en
```
- Creates a new Google Doc for each transcription session
- Good for one-off transcriptions

#### Option 2: Use Existing Google Doc (Recommended)
```bash
python live_un_transcriber.py "https://webtv.un.org/..." --language en --google-doc-id "YOUR_DOC_ID"
```
- Appends transcriptions to an existing Google Doc
- Perfect for building a comprehensive record
- Keeps all transcriptions organized in one place

#### Option 3: Disable Google Docs
```bash
python live_un_transcriber.py "https://webtv.un.org/..." --language en --no-google-docs
```
- Runs with local files only (no Google Docs)

---

## How to Find Your Google Doc ID

### Method 1: From the URL (Easiest)
1. **Open your Google Doc** in the browser
2. **Look at the address bar**:
   ```
   https://docs.google.com/document/d/1ABC123DEF456GHI789JKL0123456789/edit
   ```
3. **Copy the string** between `/d/` and `/edit`:
   ```
   1ABC123DEF456GHI789JKL0123456789
   ```

### Method 2: From Google Drive
1. Go to [Google Drive](https://drive.google.com)
2. Right-click on your document
3. Select "Share" → "Copy link"
4. Extract the document ID from the link

---

## Output Files

The script creates a timestamped folder for each run (e.g., `transcription_run_20241219_143022/`) containing:

-   `transcript.srt` → standard subtitle format
-   `transcript.txt` → plain text with timestamps
-   `un_webtv_capture/segments/` → audio segments (if needed)

**With Google Docs**: Transcriptions also appear in real-time in your Google Doc!

---

## Command Line Options

```bash
python live_un_transcriber.py [URL] [OPTIONS]

Options:
  --model {tiny,base,small,medium,large-v3}  Whisper model size (default: base)
  --compute {int8,int8_float16,float16,float32}  Compute type (default: int8)
  --language LANGUAGE                         Force language (e.g., en)
  --out OUTPUT                               Output filename prefix (default: transcript)
  --google-doc-id DOC_ID                     Use existing Google Doc instead of creating new
  --no-google-docs                           Disable Google Docs integration
  --help                                     Show help message
```

---

## Examples

### Basic Transcription
```bash
python live_un_transcriber.py "https://cflive.kaltura.com/.../index.m3u8" --language en
```

### Transcription to Existing Google Doc
```bash
python live_un_transcriber.py "https://webtv.un.org/en/asset/k1z/k1zoobol5v" \
  --language en \
  --google-doc-id "1ABC123DEF456GHI789JKL0123456789"
```

### High-Quality Transcription
```bash
python live_un_transcriber.py "https://webtv.un.org/..." \
  --model large-v3 \
  --compute float16 \
  --language en
```

---

## Tips for Volunteers

-   Make sure the internet connection is stable.

-   You do **not** need to keep the UN WebTV tab open after copying the `.m3u8` URL --- the script will fetch the stream directly.

-   To stop the transcription, press `Ctrl+C`.

-   **Google Docs Integration**: Each transcription segment appears in real-time in your Google Doc with timestamps.

-   **Organization**: Use the `--google-doc-id` option to keep all transcriptions in one master document.

---

## Troubleshooting

### Google Docs Issues
- **"Credentials file not found"**: Follow the [Google Docs Setup Guide](GOOGLE_DOCS_SETUP.md)
- **"Authentication failed"**: Delete `token.json` and try again
- **"Permission denied"**: Make sure you granted permission in the browser

### General Issues
- **Audio not working**: Check if `ffmpeg` is installed
- **Transcription errors**: Try a different model size or compute type
- **Network issues**: Verify the `.m3u8` URL is still valid

---

## Advanced Features

- **Real-time transcription**: Watch transcriptions appear as they're generated
- **Multiple output formats**: SRT subtitles, plain text, and Google Docs
- **Flexible models**: Choose from tiny to large-v3 based on your needs
- **Language detection**: Automatic or force specific language
- **Robust streaming**: Handles network interruptions gracefully