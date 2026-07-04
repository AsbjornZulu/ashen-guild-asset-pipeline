# Example run results

This file documents a test run of the asset pipeline.

## Test 1: grid-perfect example sheet

Input:

```text
assets_raw/example_grid_warrior_fixed.png
```

Command:

```bash
python3 tools/ashen_asset_pipeline.py slice-grid assets_raw/example_grid_warrior_fixed.png assets_processed/characters/example_grid_warrior \
  --rows 4 \
  --cols 14 \
  --key "#FF00FF" \
  --tolerance 30 \
  --despill \
  --pad 2 \
  --prefix example_warrior
```

Result:

```text
56 frame PNGs generated
manifest.json generated
_preview.png generated
```

This confirms that the pipeline works correctly when the source spritesheet is aligned to a real fixed grid.

## Test 2: generated warrior sheet from AI

Input:

```text
assets_raw/warrior_fixed.png
```

Command:

```bash
python3 tools/ashen_asset_pipeline.py slice-grid assets_raw/warrior_fixed.png assets_processed/characters/warrior \
  --rows 4 \
  --cols 14 \
  --key "#FF00FF" \
  --tolerance 55 \
  --despill \
  --pad 4 \
  --prefix warrior
```

Result:

```text
56 frame PNGs generated
manifest.json generated
_preview.png generated
```

Important observation:

The pipeline generated the expected number of files, but the preview showed that some sprites were cut incorrectly. This happened because the AI-generated source sheet is not aligned to a mathematically consistent 4x14 grid. Some sprites have uneven spacing and wider attack poses.

## Practical conclusion

The pipeline is working.

For best results, raw AI-generated spritesheets should follow one of these rules:

1. Use a true fixed grid where every frame cell has equal width and height.
2. Or use `slice-components` first when sprites are separated but not grid-aligned.
3. Or manually align the sheet in Pixelorama / LibreSprite / Photopea before running `slice-grid`.

Recommended production workflow:

```text
AI generation -> manual grid alignment/fixes -> slice-grid -> preview check -> game import
```
