"""
Voice memo transcriber for Mac Voice Memos.
Reads .m4a files from the Voice Memos directory and transcribes them.

Supports:
  - whisper (openai-whisper): plain transcription, no speaker labels
  - whisperx: transcription + speaker diarization (needs HF token)
  - openai: OpenAI Whisper API
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

VOICE_MEMOS_DIR = Path.home() / "Library/Application Support/com.apple.voicememos/Recordings"

# Auto-load .env from project root
_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
if _ENV_PATH.exists():
    for line in _ENV_PATH.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            if key.strip() not in os.environ:
                os.environ[key.strip()] = val.strip()

HF_TOKEN = os.environ.get("HF_TOKEN", "")


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
        method: "whisper" (plain), "whisperx" (with speaker diarization), "openai" (API)
    """
    if method == "openai":
        return _transcribe_openai(file_path)
    elif method == "whisperx":
        return _transcribe_whisperx(file_path)
    else:
        return _transcribe_whisper(file_path)


def _transcribe_whisper(file_path: str) -> str:
    """Transcribe using local whisper (no speaker labels)."""
    if "HF_ENDPOINT" not in os.environ:
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

    try:
        import whisper
    except ImportError:
        print("Installing openai-whisper...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "openai-whisper"])
        import whisper

    model = whisper.load_model("small")
    result = model.transcribe(file_path, language="zh")
    return result["text"]


def _transcribe_whisperx(file_path: str) -> str:
    """Transcribe + speaker diarization using whisper + pyannote.

    Runs whisper and pyannote in SEPARATE subprocesses to avoid
    OpenMP segfault when both libs load in the same process.

    Returns text with speaker labels like:
        [SPEAKER_00] 你好...
        [SPEAKER_01] 我想问一下...
    """
    import tempfile

    if not HF_TOKEN:
        print("  No HF_TOKEN — falling back to plain whisper")
        return _transcribe_whisper(file_path)

    # Step 1: whisper transcription in a subprocess
    print("  [1/2] Transcribing with whisper (subprocess)...")
    whisper_script = """
import whisper, json, sys
model = whisper.load_model("small")
result = model.transcribe(sys.argv[1], language="zh")
json.dump({"segments": result["segments"]}, open(sys.argv[2], "w"), ensure_ascii=False)
print(f"whisper_done: {len(result['segments'])} segments")
"""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        whisper_out = tmp.name

    subprocess.run(
        [sys.executable, "-c", whisper_script, file_path, whisper_out],
        check=True, timeout=600,
    )

    # Step 2: pyannote diarization + merge in a subprocess
    print("  [2/2] Diarizing speakers (subprocess)...")
    # Need to convert m4a to wav first for torchaudio
    wav_path = file_path
    if file_path.lower().endswith(".m4a"):
        wav_path = file_path + ".tmp.wav"
        subprocess.run([
            "ffmpeg", "-y", "-i", file_path,
            "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000",
            wav_path,
        ], capture_output=True, check=True, timeout=120)

    pyannote_script = f"""
import json, torch, sys, numpy as np
from scipy.io import wavfile
from sklearn.cluster import KMeans
import librosa

with open({whisper_out!r}) as f:
    data = json.load(f)
segments = data["segments"]

# Load audio
sr, audio_np = wavfile.read({wav_path!r})
audio_np = audio_np.astype(np.float32) / 32768.0
if audio_np.ndim > 1:
    audio_np = audio_np.mean(axis=1)

# MFCC + delta features + Agglomerative clustering
num_speakers = 2
segment_features = []
valid_segments = []

for seg in segments:
    s, e = seg["start"], seg["end"]
    start_sample = int(s * sr)
    end_sample = int(e * sr)
    if end_sample - start_sample < sr * 0.3:
        continue
    chunk = audio_np[start_sample:end_sample]
    if len(chunk) == 0:
        continue
    mfcc = librosa.feature.mfcc(y=chunk, sr=sr, n_mfcc=13)
    delta = librosa.feature.delta(mfcc)
    ddelta = librosa.feature.delta(mfcc, order=2)
    combined = np.concatenate([
        mfcc.mean(axis=1), delta.mean(axis=1), ddelta.mean(axis=1),
    ])
    segment_features.append(combined)
    valid_segments.append(seg)

if len(segment_features) < num_speakers:
    for seg in segments:
        print(f"[面试官] {{seg['text'].strip()}}")
    sys.exit(0)

X = np.stack(segment_features)
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import AgglomerativeClustering
X = StandardScaler().fit_transform(X)
labels = AgglomerativeClustering(n_clusters=num_speakers).fit_predict(X)

# Heuristic: interviewer shorter, candidate longer
cluster_durs = {{0: [], 1: []}}
for seg, lbl in zip(valid_segments, labels):
    cluster_durs[lbl].append(seg["end"] - seg["start"])
avg0 = np.mean(cluster_durs[0]) if cluster_durs[0] else 0
avg1 = np.mean(cluster_durs[1]) if cluster_durs[1] else 0
lmap = {{0: "候选人", 1: "面试官"}} if avg0 >= avg1 else {{0: "面试官", 1: "候选人"}}

# Build initial labels for all segments
seg_to_label = {{}}
for seg, label in zip(valid_segments, labels):
    seg_to_label[id(seg)] = lmap[label]

# Context smoothing: fix isolated mislabels using majority of neighbors
seg_list = list(segments)
for i, seg in enumerate(seg_list):
    if id(seg) not in seg_to_label:
        continue
    window = 3
    neighbors = []
    for j in range(max(0, i-window), min(len(seg_list), i+window+1)):
        if j != i and id(seg_list[j]) in seg_to_label:
            neighbors.append(seg_to_label[id(seg_list[j])])
    if neighbors:
        from collections import Counter
        majority = Counter(neighbors).most_common(1)[0][0]
        # If current label differs from all neighbors, flip it
        if seg_to_label[id(seg)] != majority and len(set(neighbors)) == 1:
            seg_to_label[id(seg)] = majority

# Output with speaker labels
for seg in segments:
    label = seg_to_label.get(id(seg), "?")
    print(f"[{{label}}] {{seg['text'].strip()}}")
"""
    result = subprocess.run(
        [sys.executable, "-c", pyannote_script],
        capture_output=True, text=True, timeout=600,
    )

    # Cleanup temp wav
    if wav_path != file_path:
        try:
            os.unlink(wav_path)
        except Exception:
            pass
    try:
        os.unlink(whisper_out)
    except Exception:
        pass

    if result.returncode != 0:
        print(f"  Diarization failed: {result.stderr}")
        # Fall back to plain transcription
        return _transcribe_whisper(file_path)

    return result.stdout


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
