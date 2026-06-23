# Local Skills

This repository contains a reproducible Codex skill package for user-problem-first product selection research.

## Contents

- `category-scout-reflection/`: Codex skill folder.
- `tests/`: Lightweight regression checks for the bundled scoring script.

## What HR Can Reproduce

The package does not require network access, API keys, package installation, or Codex runtime access to verify the scoring script. It uses only Python 3 standard library modules.

```bash
../scripts/run_real_sample.sh
```

Expected outputs:

- `/tmp/category-scout-output/scored_observations.csv`
- `/tmp/category-scout-output/scored_observations_zh.csv`
- `/tmp/category-scout-output/reflection_report.md`
- `/tmp/category-scout-output/dashboard.html`

To run regression checks from this repository root:

```bash
python3 tests/test_category_scout_reflection.py
```

From the project root, HR can also run:

```bash
./scripts/run_all_samples.sh
```

## Optional Codex Skill Install

To use it as a local Codex skill, copy or symlink `category-scout-reflection/` into the Codex skills directory:

```bash
mkdir -p ~/.codex/skills
ln -s "$(pwd)/category-scout-reflection" ~/.codex/skills/category-scout-reflection
```

Then ask Codex to use `$category-scout-reflection`.

## Notes

The example observations are intended for workflow reproduction. For production category decisions, collect fresh user-problem rows from ecommerce reviews, Q&A, social comments, and support forums before relying on the output.
