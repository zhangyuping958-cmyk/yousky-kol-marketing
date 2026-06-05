#!/usr/bin/env python3
"""Image text extractor — fallback when Read tool can't handle images."""
import subprocess, sys, os
from pathlib import Path

def ocr_image(image_path: str, lang: str = "chi_sim+eng") -> str:
    """Extract text from an image using tesseract OCR."""
    path = Path(image_path)
    if not path.exists():
        return f"[File not found: {image_path}]"

    # Check if tesseract has the requested language
    result = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True)
    available = result.stdout

    # Fall back to available languages
    for l in [lang, "chi_sim+eng", "eng"]:
        if all(ln in available for ln in l.split("+")):
            lang = l
            break

    try:
        result = subprocess.run(
            ["tesseract", str(path), "stdout", "-l", lang],
            capture_output=True, text=True, timeout=120,
        )
        return result.stdout.strip()
    except Exception as e:
        return f"[OCR failed: {e}]"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = ocr_image(sys.argv[1])
        print(text)
    else:
        print("Usage: python ocr_image.py <image_path>")
