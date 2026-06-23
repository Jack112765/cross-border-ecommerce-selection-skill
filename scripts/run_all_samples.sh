#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 "$ROOT/scripts/run_skill_tests.py"
"$ROOT/scripts/run_real_sample.sh"
"$ROOT/scripts/run_blender_sample.sh"
"$ROOT/scripts/run_media_only_negative.sh"
"$ROOT/scripts/validate_skill.sh"

echo "All category scout samples and checks completed."
