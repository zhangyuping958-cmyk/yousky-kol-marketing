#!/usr/bin/env python3
"""
Interview Buddy — 面试搭子 CLI
================================
A tool to assist with candidate interviews at Yousky.

Workflow:
  1. parse   — Parse candidate's resume
  2. gen-q   — Output the prompt for generating interview questions
  3. memos   — Find Mac Voice Memos
  4. transcribe — Transcribe voice memos to text
  5. eval    — Output the prompt for evaluating candidate answers

Usage:
  python main.py parse <resume.pdf>
  python main.py gen-q <resume.pdf> --role "KOL达人拓展" --team "达人合作/KOL团队"
  python main.py memos
  python main.py transcribe <file.m4a>
  python main.py transcribe --all
  python main.py eval <questions.txt> <answers.txt> --role "..." --team "..." --resume <file>
"""
import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from resume_parser import parse_resume
from question_generator import build_question_prompt, load_company_context
from transcriber import find_voice_memos, get_latest_memo, transcribe, transcribe_multiple
from evaluator import build_evaluation_prompt


def cmd_parse(args):
    """Parse a resume file and output text."""
    result = parse_resume(args.file)
    out_path = Path(args.file).with_suffix(".parsed.txt")
    out_path.write_text(result["raw_text"], encoding="utf-8")
    print(f"✅ 简历解析完成: {result['file_name']}")
    print(f"   字符数: {result['char_count']}")
    print(f"   识别段落: {list(result['sections'].keys())}")
    print(f"   已保存: {out_path}")
    if args.print:
        print("\n" + "=" * 60)
        print(result["raw_text"][:3000])


def cmd_gen_q(args):
    """Generate the prompt for interview questions."""
    result = parse_resume(args.file)
    prompt = build_question_prompt(
        resume_text=result["raw_text"],
        role=args.role,
        team=args.team,
    )
    out_path = Path(args.file).with_suffix(".questions_prompt.txt")
    out_path.write_text(prompt, encoding="utf-8")
    print(f"✅ 面试题生成 prompt 已保存: {out_path}")
    print(f"   岗位: {args.role} / {args.team}")
    print(f"\n📋 请将以下 prompt 发给 Claude 生成面试题，或直接在这里对话。")


def cmd_memos(args):
    """Find and list Mac Voice Memos."""
    directory = args.dir or None
    memos = find_voice_memos(directory)
    if not memos:
        print("❌ 未找到语音备忘录。")
        print(f"   默认路径: ~/Library/Application Support/com.apple.voicememos/Recordings/")
        print(f"   你也可以用 --dir 指定其他目录。")
        return

    print(f"🎙️  找到 {len(memos)} 条语音备忘录:\n")
    for i, m in enumerate(memos):
        print(f"  [{i}] {m['name']}")
        print(f"      日期: {m['modified']}  |  大小: {m['size_mb']}MB  |  时长: {m['duration']}")


def cmd_transcribe(args):
    """Transcribe voice memos."""
    method = args.method or "whisper"

    if args.latest:
        memo = get_latest_memo(args.dir or None)
        if not memo:
            print("❌ 未找到语音备忘录。")
            return
        print(f"🎙️  最新录音: {memo['name']} ({memo['modified']}, {memo['duration']})")
        files = [memo["path"]]
    elif args.all:
        memos = find_voice_memos(args.dir or None)
        if not memos:
            print("❌ 未找到语音备忘录。")
            return
        files = [m["path"] for m in memos]
    elif args.file:
        files = [args.file]
    else:
        print("❌ 请指定 --file、--latest 或 --all")
        return

    results = transcribe_multiple(files, method)

    out_path = Path("interview_transcripts.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        for name, text in results.items():
            f.write(f"\n{'=' * 60}\n")
            f.write(f"文件: {name}\n")
            f.write(f"{'=' * 60}\n")
            f.write(text)
            f.write("\n")

    print(f"✅ 转录完成，共 {len(results)} 条，已保存至: {out_path}")


def cmd_eval(args):
    """Generate the evaluation prompt."""
    questions = Path(args.questions_file).read_text(encoding="utf-8")
    answers = Path(args.answers_file).read_text(encoding="utf-8")

    resume_summary = ""
    if args.resume:
        result = parse_resume(args.resume)
        resume_summary = result["raw_text"]

    prompt = build_evaluation_prompt(
        questions=questions,
        answers=answers,
        role=args.role,
        team=args.team,
        resume_summary=resume_summary,
    )

    out_path = Path("evaluation_prompt.txt")
    out_path.write_text(prompt, encoding="utf-8")
    print(f"✅ 评估 prompt 已保存: {out_path}")
    print(f"   岗位: {args.role} / {args.team}")


def main():
    parser = argparse.ArgumentParser(
        description="Interview Buddy — Yousky面试搭子",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py parse 张振简历.pdf
  python main.py gen-q 张振简历.pdf --role "KOL达人拓展" --team "达人合作/KOL团队"
  python main.py memos
  python main.py transcribe --all
  python main.py eval questions.txt answers.txt --role "..." --team "..." --resume 张振简历.pdf
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # parse
    p = sub.add_parser("parse", help="解析简历文件")
    p.add_argument("file", help="简历文件路径 (.pdf/.docx/.txt)")
    p.add_argument("--print", action="store_true", help="打印解析结果")
    p.set_defaults(func=cmd_parse)

    # gen-q
    p = sub.add_parser("gen-q", help="生成面试题 prompt")
    p.add_argument("file", help="简历文件路径")
    p.add_argument("--role", required=True, help="应聘岗位名称")
    p.add_argument("--team", required=True, help="所属团队")
    p.set_defaults(func=cmd_gen_q)

    # memos
    p = sub.add_parser("memos", help="查找 Mac 语音备忘录")
    p.add_argument("--dir", help="语音文件目录（可选）")
    p.set_defaults(func=cmd_memos)

    # transcribe
    p = sub.add_parser("transcribe", help="转录语音备忘录")
    p.add_argument("--file", help="单个 .m4a 文件路径")
    p.add_argument("--latest", action="store_true", help="转录最新一条语音备忘录")
    p.add_argument("--all", action="store_true", help="转录所有语音备忘录")
    p.add_argument("--method", choices=["whisper", "openai"], default="whisper", help="转录方式")
    p.add_argument("--dir", help="语音文件目录（配合 --all 使用）")
    p.set_defaults(func=cmd_transcribe)

    # eval
    p = sub.add_parser("eval", help="生成评估 prompt")
    p.add_argument("questions_file", help="面试题文本文件")
    p.add_argument("answers_file", help="候选人回答文本文件")
    p.add_argument("--role", required=True, help="应聘岗位")
    p.add_argument("--team", required=True, help="所属团队")
    p.add_argument("--resume", help="简历文件（可选，用于交叉参考）")
    p.set_defaults(func=cmd_eval)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
