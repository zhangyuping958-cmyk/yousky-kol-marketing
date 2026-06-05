#!/bin/bash
# Extract text from .pptx files
# Usage: ./pptx2text.sh <path-to-pptx>

set -euo pipefail

PPTX="$1"
TMPDIR=$(mktemp -d)

cleanup() { rm -rf "$TMPDIR"; }
trap cleanup EXIT

unzip -q "$PPTX" -d "$TMPDIR"

for slide in "$TMPDIR"/ppt/slides/slide*.xml; do
    num=$(basename "$slide" .xml | sed 's/slide//')
    echo "===== 幻灯片 $num ====="
    grep -o '<a:t>[^<]*</a:t>' "$slide" | sed 's|<a:t>||g;s|</a:t>||g'
    echo ""
done
