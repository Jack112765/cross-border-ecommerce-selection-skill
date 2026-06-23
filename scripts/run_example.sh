#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 "$ROOT/local-skills/category-scout-reflection/scripts/category_scout_reflection.py" \
  --profile "$ROOT/examples/portable_ice_maker/profile.json" \
  --observations "$ROOT/examples/portable_ice_maker/observations_2026-06-23.csv" \
  --out "$ROOT/category-scout-output/example"

echo "Open: $ROOT/category-scout-output/example/dashboard.html"
