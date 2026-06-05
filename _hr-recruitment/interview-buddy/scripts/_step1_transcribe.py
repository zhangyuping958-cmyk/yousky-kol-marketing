#!/usr/bin/env python3
"""Step 1: Whisper transcription -> save to temp file."""
import whisper, json

audio = "/Users/qisanjiudekeaiduo/Downloads/python3/Harlottecc/_hr-recruitment/邓棋面试录音.m4a"
print("Loading whisper tiny model...")
model = whisper.load_model("tiny")
print("Transcribing...")
result = model.transcribe(audio, language="zh")
with open("/tmp/_whisper_result.json", "w") as f:
    json.dump({"segments": result["segments"], "text": result["text"]}, f, ensure_ascii=False)
print(f"Done. {len(result['segments'])} segments, {len(result['text'])} chars")
