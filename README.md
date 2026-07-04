# Ashen Guild Asset Pipeline

Free Python pipeline for creating and processing pixel-art game assets for **Ashen Guild**.

## What it does

- Pixel-perfect upscale with nearest-neighbor.
- Remove magenta / green / blue chroma backgrounds.
- Clean border color contamination with despill.
- Slice character spritesheets by grid.
- Auto-slice separated props by connected components.
- Export transparent PNG files.
- Generate `manifest.json`.
- Generate `_preview.png`.
- Optional GitHub Actions workflow for processing assets from the browser.

## Install locally

```bash
python3 -m pip install -r requirements.txt
```

## Folder structure

```text
assets_raw/         # Put original generated spritesheets here
assets_processed/   # Pipeline outputs go here
tools/              # Python pipeline script
examples/           # Optional examples / notes
```

## 1. Pixel-perfect upscale

```bash
python3 tools/ashen_asset_pipeline.py upscale assets_raw/input.png assets_processed/input_4x.png --scale 4
```

## 2. Remove magenta background

```bash
python3 tools/ashen_asset_pipeline.py clean assets_raw/input.png assets_processed/input_clean.png \
  --key "#FF00FF" \
  --tolerance 55 \
  --despill \
  --crop
```

Useful chroma keys:

```text
Magenta: #FF00FF
Green:   #00FF00
Blue:    #0000FF
Cyan:    #00FFFF
```

## 3. Slice 4-direction character spritesheets

For the current warrior/zombie format:

```text
4 rows = north, south, east, west
14 columns = idle 4 + walk 6 + attack 4
```

Run:

```bash
python3 tools/ashen_asset_pipeline.py slice-grid assets_raw/warrior.png assets_processed/warrior \
  --rows 4 \
  --cols 14 \
  --key "#FF00FF" \
  --tolerance 55 \
  --despill \
  --pad 4 \
  --prefix warrior
```

Output example:

```text
warrior_north_idle_01.png
warrior_north_idle_02.png
warrior_north_walk_01.png
warrior_north_attack_01.png
manifest.json
_preview.png
```

## 4. Slice separated props automatically

Good for environment sheets where each object is separated by chroma background.

```bash
python3 tools/ashen_asset_pipeline.py slice-components assets_raw/props.png assets_processed/props \
  --key "#FF00FF" \
  --tolerance 55 \
  --despill \
  --min-area 64 \
  --pad 4 \
  --prefix prop
```

## GitHub Actions usage

You can process assets without running Python locally:

1. Upload a PNG into `assets_raw/`.
2. Go to **Actions**.
3. Choose **Process game assets**.
4. Click **Run workflow**.
5. Fill the inputs:

```text
mode: slice-grid / slice-components / clean / upscale
input_file: assets_raw/your_sheet.png
output_dir: assets_processed/your_asset
key: #FF00FF
rows: 4
cols: 14
prefix: warrior
```

The workflow commits generated outputs into `assets_processed/` and also uploads them as a workflow artifact.

## Recommended Ashen Guild workflow

1. Generate spritesheet with AI.
2. Put raw PNG in `assets_raw/`.
3. Run the pipeline.
4. Check `_preview.png`.
5. Manually fix only bad frames in Pixelorama / LibreSprite / Photopea.
6. Use the final transparent PNGs in the game asset folder.

## Notes

- This pipeline does **not** create missing animations.
- It automates the boring work: cleaning, slicing, naming, exporting and previewing.
- For best results, use spritesheets with flat solid chroma background and consistent grid layouts.
