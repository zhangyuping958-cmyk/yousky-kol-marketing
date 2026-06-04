"""
Voice memo transcriber for Mac Voice Memos.
Reads .m4a files from the Voice Memos directory and transcribes them.
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

VOICE_MEMOS_DIR = Path.home() / "Library/Application Support/com.apple.voicememos/Recordings"


def find_voice_memos(directory: str | None = None) -> list[dict]:
    """Find all .m4a voice memo files and return metadata."""
    search_dir = Path(directory) if directory else VOICE_MEMOS_DIR
    if not search_dir.exists():
        return []

    memos = []
    for f in sorted(search_dir.glob("*.m4a"), key=lambda x: x.stat().st_mtime, reverse=True):
        stat = f.stat()
        memos.append({
            "path": str(f),
            "name": f.name,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "duration": _get_duration(str(f)),
        })
    return memos


def _get_duration(file_path: str) -> str:
    """Get audio duration using ffprobe if available."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", file_path],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            info = json.loads(result.stdout)
            seconds = float(info.get("format", {}).get("duration", 0))
            mins, secs = divmod(int(seconds), 60)
            return f"{mins}:{secs:02d}"
    except Exception:
        pass
    return "unknown"


def get_latest_memo(directory: str | None = None) -> dict | None:
    """Get the most recent voice memo (by modification time)."""
    memos = find_voice_memos(directory)
    return memos[0] if memos else None


def transcribe(file_path: str, method: str = "whisper") -> str:
    """Transcribe a voice memo file to text.

    Args:
        file_path: Path to .m4a file
        method: "whisper" (local) or "openai" (API)
    """
    if method == "openai":
        return _transcribe_openai(file_path)
    else:
        return _transcribe_whisper(file_path)


def _transcribe_whisper(file_path: str) -> str:
    """Transcribe using local whisper."""
    # Use HF mirror for users in China
    if "HF_ENDPOINT" not in os.environ:
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

    try:
        import whisper
    except ImportError:
        print("Installing openai-whisper...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "openai-whisper"])
        import whisper

    model = whisper.load_model("base")
    result = model.transcribe(file_path, language="zh")
    return result["text"]


def _transcribe_openai(file_path: str) -> str:
    """Transcribe using OpenAI Whisper API."""
    import openai

    client = openai.OpenAI()
    with open(file_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="text",
        )
    return transcript


def transcribe_multiple(file_paths: list[str], method: str = "whisper") -> dict[str, str]:
    """Transcribe multiple files and return {filename: text}."""
    results = {}
    for fp in file_paths:
        name = Path(fp).name
        print(f"Transcribing: {name} ...")
        try:
            results[name] = transcribe(fp, method)
        except Exception as e:
            results[name] = f"[Transcription failed: {e}]"
    return results
