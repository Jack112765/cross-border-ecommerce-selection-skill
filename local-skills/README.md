# Local Skills

This repository contains a reproducible Codex skill package for user-problem-first product selection research.

## Contents

- `category-scout-reflection/`: Codex skill folder.
- `tests/`: Lightweight regression checks for the bundled scoring script.

## What HR Can Reproduce

The package does not require network access, API keys, package installation, or Codex runtime access to verify the scoring script. It uses only Python 3 standard library modules.

From the project root:

```bash
./scripts/run_real_sample.sh
```

Expected outputs:

- `examples/portable_ice_maker/output/scored_observations.csv`
- `examples/portable_ice_maker/output/scored_observations_zh.csv`
- `examples/portable_ice_maker/output/reflection_report.md`
- `examples/portable_ice_maker/output/dashboard.html`

To run core regression checks from the project root:

```bash
python3 ./scripts/run_skill_tests.py
```

To run all samples plus the Codex Skill manifest validator, install PyYAML first:

```bash
python3 -m pip install --target .local-python-packages -r requirements.txt
./scripts/run_all_samples.sh
```

If PyYAML is not installed, run the sample scripts individually instead:

```bash
./scripts/run_real_sample.sh
./scripts/run_blender_sample.sh
./scripts/run_media_only_negative.sh
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
