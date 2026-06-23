#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 "$ROOT/local-skills/category-scout-reflection/scripts/category_scout_reflection.py" \
  --profile "$ROOT/examples/portable_blender/profile.json" \
  --observations "$ROOT/examples/portable_blender/observations_2026-06-22.csv" \
  --out "$ROOT/examples/portable_blender/output"

echo "Open: $ROOT/examples/portable_blender/output/dashboard.html"
