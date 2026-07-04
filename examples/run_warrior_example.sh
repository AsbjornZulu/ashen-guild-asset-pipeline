#!/usr/bin/env bash
set -euo pipefail

# Example local run.
# Put your corrected spritesheet here first:
# assets_raw/warrior_fixed.png

python3 -m pip install -r requirements.txt

python3 tools/ashen_asset_pipeline.py slice-grid assets_raw/warrior_fixed.png assets_processed/characters/warrior \
  --rows 4 \
  --cols 14 \
  --key "#FF00FF" \
  --tolerance 55 \
  --despill \
  --pad 4 \
  --prefix warrior

printf '\nDone. Check:\n'
printf 'assets_processed/characters/warrior/_preview.png\n'
printf 'assets_processed/characters/warrior/manifest.json\n'
