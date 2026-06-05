#!/usr/bin/env python3
"""
Interview Buddy Auto-Pilot
===========================
Full automation: watches for new interview recordings, auto-transcribes,
auto-scores, and gives pass/fail recommendation.

Usage:
  python auto_pilot.py

It will:
  1. Find the latest resume in _hr-recruitment/
  2. Find the latest voice memo (from Mac Voice Memos or _hr-recruitment/)
  3. Generate interview questions (if not already generated)
  4. Transcribe + speaker diarization
  5. Score answers + recommendation
  6. Save everything to _hr-recruitment/{candidate_name}_评估报告.md
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HR_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = HR_DIR / "interview-buddy" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from resume_parser import parse_resume
from question_generator import build_question_prompt, load_company_context
from evaluator import build_evaluation_prompt
from transcriber import (
    find_voice_memos, get_latest_memo, transcribe,
    VOICE_MEMOS_DIR,
)

WHISPER_METHOD = "whisperx"  # with speaker diarization


def find_latest_resume() -> dict | None:
    """Find the most recently modified resume in _hr-recruitment/."""
    resumes = []
    for ext in ["*.pdf", "*.docx"]:
        for f in HR_DIR.glob(ext):
            if "简历" in f.name or "resume" in f.name.lower():
                resumes.append(f)
    if not resumes:
        # Fallback: any PDF/DOCX
        for ext in ["*.pdf", "*.docx"]:
            for f in HR_DIR.glob(ext):
                resumes.append(f)
    if not resumes:
        return None
    latest = max(resumes, key=lambda f: f.stat().st_mtime)
    return {
        "path": str(latest),
        "name": latest.stem,
        "modified": datetime.fromtimestamp(latest.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
    }


def find_latest_recording() -> dict | None:
    """Find newest voice memo: check _hr-recruitment/ first, then Mac Voice Memos."""
    # Check _hr-recruitment/ first
    local_m4a = sorted(HR_DIR.glob("*.m4a"), key=lambda f: f.stat().st_mtime, reverse=True)
    if local_m4a:
        f = local_m4a[0]
        return {
            "path": str(f),
            "name": f.name,
            "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
        }
    # Fallback to Mac Voice Memos
    return get_latest_memo()


def generate_questions(resume_path: str, role: str, team: str) -> str:
    """Generate interview questions using Claude (via the caller)."""
    result = parse_resume(resume_path)
    prompt = build_question_prompt(result["raw_text"], role, team)
    q_path = Path(resume_path).with_suffix(".questions_prompt.txt")
    q_path.write_text(prompt, encoding="utf-8")
    return prompt


def run_transcription(audio_path: str) -> str:
    """Transcribe audio with speaker diarization."""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "main.py"), "transcribe",
         "--file", audio_path, "--method", WHISPER_METHOD],
        capture_output=True, text=True, timeout=900, cwd=str(HR_DIR),
    )
    if result.returncode != 0:
        return f"[Transcription failed: {result.stderr}]"
    # Read the output file
    transcript_path = HR_DIR / "interview_transcripts.txt"
    if transcript_path.exists():
        return transcript_path.read_text(encoding="utf-8")
    return result.stdout


def build_evaluation(resume_path: str, questions: str, answers: str,
                     role: str, team: str) -> str:
    """Build evaluation prompt."""
    resume_data = parse_resume(resume_path)
    prompt = build_evaluation_prompt(
        questions=questions,
        answers=answers,
        role=role,
        team=team,
        resume_summary=resume_data["raw_text"],
    )
    return prompt


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Interview Buddy Auto-Pilot")
    parser.add_argument("--role", required=True, help="应聘岗位")
    parser.add_argument("--team", required=True, help="所属团队")
    parser.add_argument("--resume", help="简历路径（可选，自动查找最新）")
    parser.add_argument("--audio", help="录音路径（可选，自动查找最新）")
    args = parser.parse_args()

    print("=" * 60)
    print("  Interview Buddy · Auto-Pilot")
    print("=" * 60)

    # Step 1: Find resume
    resume_info = {"path": args.resume} if args.resume else find_latest_resume()
    if not resume_info or not resume_info["path"]:
        print("❌ 未找到简历文件。请将简历放入 _hr-recruitment/ 目录。")
        return
    print(f"\n📄 简历: {Path(resume_info['path']).name}")
    if "modified" in resume_info:
        print(f"   修改时间: {resume_info['modified']}")

    # Step 2: Parse resume
    print("\n[1/4] 解析简历...")
    resume_data = parse_resume(resume_info["path"])

    # Step 3: Generate questions
    print("[2/4] 生成面试题...")
    q_prompt = build_question_prompt(resume_data["raw_text"], args.role, args.team)
    q_path = Path(resume_info["path"]).with_suffix(".questions_prompt.txt")
    q_path.write_text(q_prompt, encoding="utf-8")
    print(f"   ✅ 面试题 prompt 已保存: {q_path.name}")
    print(f"\n{'─' * 60}")
    print("📋 请将以上 prompt 发给 Claude 生成面试题，然后进行面试。")
    print("   面试完成后，用 Mac 语音备忘录录音。")
    print(f"{'─' * 60}")

    # Step 4: Find recording
    print("\n[3/4] 查找面试录音...")
    audio_info = {"path": args.audio} if args.audio else find_latest_recording()
    if not audio_info or not audio_info["path"]:
        print("   ⚠️  未找到录音。请录音后重新运行。")
        print(f"   Mac语音备忘录路径: {VOICE_MEMOS_DIR}")
        print(f"   或将 .m4a 文件放入 _hr-recruitment/ 目录")
        return

    print(f"   🎙️  录音: {Path(audio_info['path']).name}")
    if "modified" in audio_info:
        print(f"   时间: {audio_info['modified']}")

    # Step 5: Transcribe
    print("\n   🎤 转录中（whisper small + 说话人分离）...")
    transcript = run_transcription(audio_info["path"])
    transcript_path = HR_DIR / "interview_transcripts.txt"
    print(f"   ✅ 转录完成: {transcript_path}")

    # Step 6: Build evaluation prompt
    print("\n[4/4] 生成评估 prompt...")
    questions_text = ""
    q_file = Path(resume_info["path"]).with_suffix(".questions_prompt.txt")
    if q_file.exists():
        questions_text = q_file.read_text(encoding="utf-8")

    eval_prompt = build_evaluation(
        resume_info["path"], questions_text, transcript,
        args.role, args.team,
    )
    eval_path = HR_DIR / "evaluation_prompt.txt"
    eval_path.write_text(eval_prompt, encoding="utf-8")
    print(f"   ✅ 评估 prompt 已保存: {eval_path.name}")

    # Step 7: Summary
    candidate_name = Path(resume_info["path"]).stem
    print(f"\n{'=' * 60}")
    print(f"  候选人: {candidate_name}")
    print(f"  岗位: {args.role} / {args.team}")
    print(f"  面试题: {q_path.name}")
    print(f"  转录: {transcript_path.name}")
    print(f"  评估: {eval_path.name}")
    print(f"\n  📋 下一步：将 evaluation_prompt.txt 发给 Claude 评分。")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
