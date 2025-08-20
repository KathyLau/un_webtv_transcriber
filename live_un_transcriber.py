import argparse
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import List
import shutil

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel
import librosa

# Google Docs integration
try:
    from google_docs_transcriber import setup_google_docs_integration
    GOOGLE_DOCS_AVAILABLE = True
except ImportError:
    GOOGLE_DOCS_AVAILABLE = False
    print("[info] Google Docs integration not available")

# ---- Config you can tweak quickly ----
SEGMENT_SECONDS = 15            # shorter = lower latency, higher CPU overhead
OVERLAP_SECONDS = 2   # Add overlap between segments
SAMPLE_RATE = 16000             # what we feed the ASR
MODEL_NAME = "base"             # "tiny", "base", "small", "medium", "large-v3"
COMPUTE_TYPE = "int8"           # "int8", "int8_float16", "float16", "float32" (choose per your hardware)
LANGUAGE = None                 # e.g., "en" to force English; None = auto-detect
# -------------------------------------

FFMPEG_LOGLEVEL = "error"
DEFAULT_GOOGLE_DOC_ID = "11MIv61fFgXI5-8ZvCKz84IpiMSqt3oSiKNGaAzvxvDM" #"1xAtJeimO9Eoe-59IJNfFpV4i-MCG0i44KkNgr6Zjvf8"

def ts_format(s: float) -> str:
    # SRT timestamp: HH:MM:SS,mmm
    millis = int(round(s * 1000))
    h = millis // 3_600_000
    m = (millis % 3_600_000) // 60_000
    sec = (millis % 60_000) // 1000
    ms = millis % 1000
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"

def stable_file(path: Path, wait: float = 1.2, min_checks: int = 2) -> bool:
    """Enhanced stability check with multiple verifications"""
    if not path.exists():
        return False
    
    sizes = []
    for _ in range(min_checks):
        try:
            size = path.stat().st_size
            sizes.append(size)
            time.sleep(wait / min_checks)
        except (FileNotFoundError, OSError):
            return False
    
    # File is stable if all size checks are equal and > 0
    return len(set(sizes)) == 1 and sizes[0] > 0

def discover_media_url(page_url: str) -> str:
    """
    Resolve a playable media URL.
    Simpler policy: accept direct .m3u8 URLs as-is, otherwise use yt-dlp to resolve.
    """
    u = page_url.strip()
    # Direct HTTP(S) m3u8 links
    if u.startswith("http://") or u.startswith("https://"):
        if u.lower().endswith(".m3u8"):
            return u

    # Fallback: try to resolve from a webpage using yt-dlp
    try:
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "-g", "-f", "bestaudio/best",
            u
        ]
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True).strip()
        for line in out.splitlines():
            if line.startswith("http"):
                return line.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Could not resolve media URL. yt-dlp failed: {e.output}") from e
    raise RuntimeError("Could not resolve a media URL from the provided input.")

def start_ffmpeg_segmenter(media_url: str, seg_dir: Path, loglevel: str = FFMPEG_LOGLEVEL, debug: bool = False) -> subprocess.Popen:
    """
    Spawn ffmpeg with overlapping segments to prevent missing audio
    """
    seg_pattern = str(seg_dir / "seg_%Y%m%d_%H%M%S.wav")
    # The key is to use segment_time but reduce the actual advance time
    actual_advance = SEGMENT_SECONDS - OVERLAP_SECONDS  # e.g., 15 - 3 = 12 seconds advance
    
    ffmpeg_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", loglevel,

        # Input (HLS) + reconnection flags for robustness
        "-reconnect", "1", 
        "-reconnect_streamed", "1",
        "-reconnect_at_eof", "1",
        "-rw_timeout", "15000000",  # 15s
        "-i", media_url,

        # Audio only, resample to 16k mono PCM
        "-vn",
        "-ac", "1",
        "-ar", str(SAMPLE_RATE),
        "-acodec", "pcm_s16le",

        # Create overlapping segments by using both segment_time and segment_list
        "-f", "segment",
        "-segment_time", str(SEGMENT_SECONDS),       # Length of each segment (e.g., 15s)
        "-segment_start_number", "0",
        "-segment_wrap", "0",                        # Don't wrap around
        "-segment_clocktime_wrap_duration", str(actual_advance), # Advance by less than segment_time
        "-strftime", "1",
        seg_pattern
    ]
    
    if debug:
        print(f"[debug] Segment length: {SEGMENT_SECONDS}s, Advance: {actual_advance}s, Overlap: {OVERLAP_SECONDS}s")
        print(f"[debug] ffmpeg cmd: {' '.join(ffmpeg_cmd)}")
        
    return subprocess.Popen(
        ffmpeg_cmd,
        stdout=(None if debug else subprocess.DEVNULL),
        stderr=(None if debug else subprocess.DEVNULL),
    )

def transcribe_loop(seg_dir: Path, srt_path: Path, txt_path: Path,
                    google_transcriber=None, language: str = None, 
                    model_name: str = MODEL_NAME, compute_type: str = COMPUTE_TYPE):
    """
    Watch for new WAV segments; transcribe and append to .srt, .txt, and Google Docs.
    """
    model = WhisperModel(model_name, compute_type=compute_type)
    print(f"[info] Loaded model: {model_name} (compute_type={compute_type})")
    next_index = 1
    global_offset = 0.0  # seconds elapsed across processed segments
    seen_files: List[Path] = []

    srt_path.write_text("", encoding="utf-8")
    txt_path.write_text("", encoding="utf-8")

    try:
        while True:
            wavs = sorted(seg_dir.glob("seg_*.wav"))
            new_files = [p for p in wavs if p not in seen_files]
            for wav in new_files:
                if not stable_file(wav):
                    # If still growing, check on next iteration
                    continue

                # Get exact duration to keep SRT timing continuous
                audio, sr = sf.read(str(wav), dtype="float32", always_2d=False)
                if sr != SAMPLE_RATE:
                    # safety: shouldn't happen because ffmpeg sets it
                    audio = librosa.resample(audio, orig_sr=sr, target_sr=SAMPLE_RATE)
                    sr = SAMPLE_RATE
                duration = len(audio) / float(sr)

                # Transcribe chunk
                segments, info = model.transcribe(
                    str(wav),
                    language=language,
                    vad_filter=True,  # Re-enable VAD
                    vad_parameters={
                        'min_silence_duration_ms': 100,  # Shorter silence detection
                        'max_speech_duration_s': 30,     # Longer speech segments
                        'threshold': 0.3                 # Lower threshold for speech detection
                    },
                    beam_size=5,
                    condition_on_previous_text=True,
                    initial_prompt=None,
                    temperature=0.0,  # More consistent output
                    compression_ratio_threshold=2.4,
                    log_prob_threshold=-1.0,
                    no_speech_threshold=0.5  # Lower threshold
                )

                srt_lines = []
                txt_lines = []

                for seg in segments:
                    start = global_offset + seg.start
                    end = global_offset + seg.end
                    text = seg.text.strip()
                    if not text:
                        continue

                    # Console preview
                    print(f"[{ts_format(start)} → {ts_format(end)}] {text}")

                    # Build SRT block
                    srt_lines.append(f"{next_index}")
                    srt_lines.append(f"{ts_format(start)} --> {ts_format(end)}")
                    srt_lines.append(text)
                    srt_lines.append("")  # blank line
                    next_index += 1

                    # Plain text with timestamps
                    txt_lines.append(f"[{ts_format(start)}] {text}")
                    
                    # Send to Google Docs if available
                    if google_transcriber and text.strip():
                        try:
                            success = google_transcriber.append_transcription_segment(
                                text, ts_format(start), ts_format(end)
                            )
                            if success:
                                print(f"[google] ✓ Sent to Google Doc: {text[:50]}...")
                            else:
                                print(f"[google] ✗ Failed to send to Google Doc")
                        except Exception as e:
                            print(f"[google] ✗ Error sending to Google Doc: {e}")

                # Append to files
                if srt_lines:
                    with srt_path.open("a", encoding="utf-8") as f:
                        f.write("\n".join(srt_lines) + "\n")
                if txt_lines:
                    with txt_path.open("a", encoding="utf-8") as f:
                        f.write("\n".join(txt_lines) + "\n")

                # Mark processed
                seen_files.append(wav)
                global_offset += duration

            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[info] Stopping transcription loop...")

def main():
    parser = argparse.ArgumentParser(description="Live UN WebTV Transcriber (HLS -> Whisper + Google Docs)")
    parser.add_argument("page_url", help="UN WebTV page URL (e.g., https://webtv.un.org/en/asset/k1z/k1zoobol5v)")
    parser.add_argument("--model", default=MODEL_NAME, help="faster-whisper model (tiny/base/small/medium/large-v3)")
    parser.add_argument("--compute", default=COMPUTE_TYPE, help="compute_type (int8/int8_float16/float16/float32)")
    parser.add_argument("--language", default=LANGUAGE, help="Force language (e.g., en), default: auto")
    parser.add_argument("--out", default="transcript", help="Output path prefix (creates transcript.srt & transcript.txt)")
    parser.add_argument("--no-google-docs", action="store_true", help="Disable Google Docs integration")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging (ffmpeg + processing)")
    parser.add_argument("--google-doc-id", help="Existing Google Doc ID to append transcriptions to (instead of creating new)")
    args = parser.parse_args()

    # Resolve media URL
    print("[info] Resolving media URL via yt-dlp...")
    media_url = discover_media_url(args.page_url)
    print(f"[info] Media URL resolved:\n{media_url}")

    # Set up Google Docs integration (if available and not disabled)
    google_transcriber = None
    if GOOGLE_DOCS_AVAILABLE and not args.no_google_docs:
        print("[info] Setting up Google Docs integration...")
        try:
            google_transcriber = setup_google_docs_integration()
            if google_transcriber:
                # Prefer CLI arg; otherwise fall back to hardcoded default
                target_doc_id = args.google_doc_id or DEFAULT_GOOGLE_DOC_ID
                if target_doc_id:
                    # Open existing document (hardcoded or provided)
                    print(f"[info] Opening existing Google Doc: {target_doc_id}")
                    if google_transcriber.open_existing_document(target_doc_id):
                        print("[info] Successfully opened existing Google Doc!")
                        print(f"[info] Document: {google_transcriber.get_document_url()}")
                    else:
                        print("[warning] Failed to open provided Google Doc, creating new one instead")
                        doc_id = google_transcriber.create_document("UN WebTV Live Transcription")
                        if doc_id:
                            print(f"[info] Created new Google Doc: {doc_id}")
                            print(f"[info] Document: {google_transcriber.get_document_url()}")
                        else:
                            print("[warning] Failed to create Google Doc, continuing with local files only")
                            google_transcriber.close()
                            google_transcriber = None
                else:
                    # Create new document
                    print("[info] Creating new Google Doc for this session...")
                    doc_id = google_transcriber.create_document("UN WebTV Live Transcription")
                    if doc_id:
                        print(f"[info] Created new Google Doc: {doc_id}")
                        print(f"[info] Document: {google_transcriber.get_document_url()}")
                    else:
                        print("[warning] Failed to create Google Doc, continuing with local files only")
                        google_transcriber.close()
                        google_transcriber = None
                
                if google_transcriber:
                    print("[info] Google Docs integration ready!")
                    # Probe write to confirm permissions early
                    try:
                        start_banner = (
                            "\n\n==== Session started "
                            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
                            "====\n"
                        )
                        ok = google_transcriber.append_text_to_last_tab(start_banner)
                        if ok:
                            print("[google] ✓ Verified write access to Google Doc")
                        else:
                            print("[google] ✗ Initial write failed; disabling Google Docs integration")
                            google_transcriber.close()
                            google_transcriber = None
                    except Exception as e:
                        print(f"[google] ✗ Initial write error: {e}")
                        try:
                            google_transcriber.close()
                        except Exception:
                            pass
                        google_transcriber = None
            else:
                print("[warning] Google Docs setup failed, continuing with local files only")
        except Exception as e:
            print(f"[warning] Google Docs integration error: {e}")
            print("[info] Continuing with local files only")
    else:
        if not GOOGLE_DOCS_AVAILABLE:
            print("[info] Google Docs integration not available")
        elif args.no_google_docs:
            print("[info] Google Docs integration disabled by user")

    # Modern layout: timestamped outputs in transcripts/, temp segments per run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    workdir = Path.cwd() / "un_webtv_capture"
    seg_dir = workdir / f"segments_{timestamp}"
    seg_dir.mkdir(parents=True, exist_ok=True)
    transcripts_dir = Path.cwd() / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    srt_path = transcripts_dir / f"{args.out}_{timestamp}.srt"
    txt_path = transcripts_dir / f"{args.out}_{timestamp}.txt"
    print(f"[info] Transcripts directory: {transcripts_dir}")
    print(f"[info] SRT file: {srt_path}")
    print(f"[info] TXT file: {txt_path}")
    print(f"[info] Segments directory (temporary): {seg_dir}")
    cleanup_segments_on_exit = True

    # Start ffmpeg
    print("[info] Starting ffmpeg segmenter...")
    ff = start_ffmpeg_segmenter(media_url, seg_dir, loglevel=("info" if args.debug else FFMPEG_LOGLEVEL), debug=args.debug)

    def handle_sig(sig, frame):
        print("\n[info] Caught signal, shutting down ffmpeg...")
        try:
            ff.terminate()
        except Exception:
            pass
        if google_transcriber:
            google_transcriber.close()
        if cleanup_segments_on_exit:
            try:
                shutil.rmtree(seg_dir, ignore_errors=True)
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    try:
        transcribe_loop(seg_dir, srt_path, txt_path, google_transcriber=google_transcriber,
                        language=args.language, model_name=args.model, compute_type=args.compute)
    finally:
        try:
            ff.terminate()
        except Exception:
            pass
        if google_transcriber:
            google_transcriber.close()
        if cleanup_segments_on_exit:
            try:
                shutil.rmtree(seg_dir, ignore_errors=True)
            except Exception:
                pass

if __name__ == "__main__":
    main()
