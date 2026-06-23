#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 "$ROOT/local-skills/category-scout-reflection/scripts/category_scout_reflection.py" \
  --profile "$ROOT/examples/media_only_negative/profile.json" \
  --observations "$ROOT/examples/media_only_negative/observations.csv" \
  --out "$ROOT/examples/media_only_negative/output"

echo "Open: $ROOT/examples/media_only_negative/output/dashboard.html"
