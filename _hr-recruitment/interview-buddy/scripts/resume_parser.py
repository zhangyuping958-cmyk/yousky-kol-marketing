"""
Resume parser — extracts text from PDF, DOCX, and TXT files.
"""
import re
from pathlib import Path


def parse_resume(file_path: str) -> dict:
    """Parse a resume file and return structured text content."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Resume not found: {file_path}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = _parse_pdf(path)
    elif suffix == ".docx":
        text = _parse_docx(path)
    elif suffix in (".txt", ".md"):
        text = path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    return {
        "file_name": path.name,
        "raw_text": text,
        "char_count": len(text),
        "sections": _extract_sections(text),
    }


def _parse_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    texts = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            texts.append(t)
    return "\n\n".join(texts)


def _parse_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _extract_sections(text: str) -> dict:
    """Try to identify common resume sections."""
    sections = {}
    patterns = {
        "education": r"(教育|学历|学校|毕业|Education|University|College|Bachelor|Master|PhD|B\.S\.|M\.S\.|B\.A\.|M\.A\.)",
        "experience": r"(工作经历|工作经验|实习|经历|Experience|Work|Employment|Internship)",
        "skills": r"(技能|专业技能|技术|Skills|Technical|Proficiency)",
        "projects": r"(项目|Projects|Project)",
        "languages": r"(语言|Languages|English|中文|普通话)",
        "contact": r"(电话|手机|邮箱|Email|Phone|Tel|微信|WeChat)",
    }

    lines = text.split("\n")
    for key, pattern in patterns.items():
        for i, line in enumerate(lines):
            if re.search(pattern, line, re.IGNORECASE):
                start = max(0, i)
                end = min(len(lines), i + 20)
                sections[key] = "\n".join(lines[start:end])
                break

    return sections
