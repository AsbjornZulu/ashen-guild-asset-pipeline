# Example: full Ashen Guild sprite pipeline

This example shows the practical workflow for a warrior, zombie, or enemy spritesheet.

## Goal

Convert one generated spritesheet into clean, transparent, individually named PNG frames that the game can load directly.

## Pipeline overview

```text
AI generation -> manual correction -> Python pipeline -> game loader
```

## 1. AI generation

Generate or download a raw spritesheet and save it here:

```text
assets_raw/warrior_raw.png
```

Recommended sheet structure for 4-direction characters:

```text
4 rows:
- Row 1 = north
- Row 2 = south
- Row 3 = east
- Row 4 = west

14 columns:
- 1-4   = idle
- 5-10  = walk
- 11-14 = attack
```

Use a flat chroma background:

```text
#FF00FF
```

## 2. Manual correction

Open the raw spritesheet in Pixelorama, LibreSprite, Photopea, or another free editor.

Fix only the bad frames:

- missing sword
- missing shield
- wrong direction
- wrong attack pose
- broken silhouette
- magenta border contamination

Export the corrected sheet as:

```text
assets_raw/warrior_fixed.png
```

## 3. Run the pipeline locally

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Slice the corrected warrior sheet:

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

Expected output:

```text
assets_processed/characters/warrior/warrior_north_idle_01.png
assets_processed/characters/warrior/warrior_north_idle_02.png
assets_processed/characters/warrior/warrior_north_walk_01.png
assets_processed/characters/warrior/warrior_north_attack_01.png
assets_processed/characters/warrior/manifest.json
assets_processed/characters/warrior/_preview.png
```

## 4. Run the pipeline with GitHub Actions

Instead of running locally:

1. Upload `warrior_fixed.png` to `assets_raw/`.
2. Go to **Actions**.
3. Select **Process game assets**.
4. Click **Run workflow**.
5. Use these inputs:

```text
mode: slice-grid
input_file: assets_raw/warrior_fixed.png
output_dir: assets_processed/characters/warrior
key: #FF00FF
tolerance: 55
rows: 4
cols: 14
prefix: warrior
```

The workflow commits the generated PNGs into `assets_processed/characters/warrior` and uploads them as an artifact.

## 5. Game loading convention

The pipeline names files like this:

```text
{character}_{direction}_{animation}_{frame}.png
```

Example:

```text
warrior_north_idle_01.png
warrior_north_walk_04.png
warrior_south_attack_03.png
```

This makes it easy to load animations programmatically in Godot, JavaScript, Unity, or another engine.

## Recommended loop

```text
1. Generate sheet
2. Fix obvious mistakes manually
3. Run pipeline
4. Check _preview.png
5. If a frame is bad, fix only that area
6. Run pipeline again
7. Use final PNGs in game
```
