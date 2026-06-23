#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VALIDATOR="/Users/jake/.codex/skills/.system/skill-creator/scripts/quick_validate.py"

PYTHONPATH="${ROOT}/.local-python-packages:${PYTHONPATH:-}" \
python3 "$VALIDATOR" "$ROOT/local-skills/category-scout-reflection"

