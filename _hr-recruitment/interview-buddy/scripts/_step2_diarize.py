#!/usr/bin/env python3
"""Step 2: Speaker diarization -> merge with whisper output."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from transcriber import HF_TOKEN
import torch
import torchaudio

audio = "/Users/qisanjiudekeaiduo/Downloads/python3/Harlottecc/_hr-recruitment/邓棋面试录音.m4a"
wav_audio = "/tmp/_interview_audio.wav"

# Convert m4a to wav via ffmpeg (torchaudio can't read m4a)
import subprocess, os.path
if not os.path.exists(wav_audio):
    print("Converting m4a to wav...")
    subprocess.run([
        "ffmpeg", "-y", "-i", audio,
        "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000",
        wav_audio
    ], capture_output=True, check=True)
    print("Conversion done")

# Load whisper result
with open("/tmp/_whisper_result.json") as f:
    data = json.load(f)
segments = data["segments"]
print(f"Loaded {len(segments)} whisper segments")

# Load audio via torchaudio
print("Loading audio...")
waveform, sample_rate = torchaudio.load(wav_audio)
if waveform.shape[0] > 1:
    waveform = torch.mean(waveform, dim=0, keepdim=True)

# Diarization
print("Running speaker diarization...")
from pyannote.audio import Pipeline
device = torch.device("cpu")
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    token=HF_TOKEN,
)
pipeline = pipeline.to(device)

diarization = pipeline({
    "waveform": waveform,
    "sample_rate": sample_rate,
})
print(f"Diarization done. Found speakers.")

# Merge
lines = []
for seg in segments:
    start = seg["start"]
    end = seg["end"]
    text = seg["text"].strip()
    mid = (start + end) / 2
    speaker = ""
    for turn, _, spk in diarization.itertracks(yield_label=True):
        if turn.start <= mid <= turn.end:
            speaker = spk
            break
    label = f"[{speaker}]" if speaker else "[?]"
    lines.append(f"{label} {text}")

out_path = "/Users/qisanjiudekeaiduo/Downloads/python3/Harlottecc/_hr-recruitment/邓棋面试转录_带说话人.txt"
with open(out_path, "w") as f:
    f.write("\n".join(lines))
print(f"Saved to: {out_path}")
