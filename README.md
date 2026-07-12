# Ashen Guild Asset Pipeline

Free Python pipeline for creating and processing pixel-art game assets for **Ashen Guild**.

## What it does

- Pixel-perfect upscale with nearest-neighbor.
- Remove magenta / green / blue chroma backgrounds.
- Clean border color contamination with despill.
- Slice character spritesheets by grid.
- Auto-slice separated props by connected components.
- Clean magenta halos from AI-generated FX atlases.
- Auto-detect the real chroma color from image borders.
- Merge detached droplets / particles into one effect.
- Optionally recolor neutral FX into a dark blood or mud palette.
- Export transparent PNG files.
- Generate `manifest.json` and `_preview.png`.
- Optional GitHub Actions workflow for processing assets from the browser.

## Install locally

```bash
python3 -m pip install -r requirements.txt
```

## Folder structure

```text
assets_raw/         # Put original generated spritesheets here
assets_processed/   # Pipeline outputs go here
tools/              # Python pipeline scripts
examples/           # Optional examples / notes
```

## 1. Pixel-perfect upscale

```bash
python3 tools/ashen_asset_pipeline.py upscale assets_raw/input.png assets_processed/input_4x.png --scale 4
```

## 2. Remove a simple chroma background

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

For the current warrior / zombie format:

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

## 5. Process magenta-background FX sheets

Use `tools/process_fx.py` for AI-generated particle, splash, dirt, impact or decal atlases where magenta remains inside the anti-aliased sprite borders.

The processor performs:

1. automatic background-color detection from the outer image border;
2. Color-to-Alpha style unmixing;
3. removal of pixels still very close to the chroma color;
4. magenta / green / blue edge despill;
5. optional luminance-based recoloring;
6. connected-component detection;
7. proximity grouping of detached droplets and fragments;
8. export of individual transparent PNG files.

### Recommended blood-FX command

```bash
python3 tools/process_fx.py assets_raw/particles.png assets_processed/effects/blood_particles \
  --key auto \
  --transparency-threshold 0.036 \
  --opacity-threshold 0.80 \
  --knockout-tolerance 24 \
  --despill-strength 0.80 \
  --palette blood \
  --merge-distance 24 \
  --min-area 6 \
  --pad 6 \
  --prefix blood_particle
```

### Preserve the original colors

Use `--palette none` when the assets should keep their current colors:

```bash
python3 tools/process_fx.py assets_raw/impact_fx.png assets_processed/effects/impact_fx \
  --key auto \
  --palette none \
  --merge-distance 20 \
  --min-area 6 \
  --pad 6 \
  --prefix impact
```

### Outputs

```text
_cleaned.png
_cleaned_preview_black.png
_cleaned_preview_white.png
_preview.png
manifest.json
blood_particle_001.png
blood_particle_002.png
...
```

The black and white previews make remaining chroma halos easy to detect before importing the files into the game.

### Settings guide

```text
transparency threshold  0.025–0.050
opacity threshold       0.75–0.90
knockout tolerance      16–30
merge distance          12–30
minimum area            4–12 for tiny particles
padding                 4–8 pixels
```

- Increase `--knockout-tolerance` if flat magenta pixels remain.
- Increase `--despill-strength` if the edges still look purple.
- Reduce `--opacity-threshold` if the sprite colors change too much.
- Increase `--merge-distance` if droplets belonging to one effect are exported separately.
- Reduce `--merge-distance` if neighboring effects are incorrectly merged.

## GitHub Actions usage

You can process assets without running Python locally:

1. Upload a PNG into `assets_raw/`.
2. Go to **Actions**.
3. Choose **Process game assets**.
4. Click **Run workflow**.
5. Choose the required processing mode.

Available modes:

```text
clean
upscale
slice-grid
slice-components
process-fx
```

For an FX atlas use values similar to:

```text
mode: process-fx
input_file: assets_raw/particles.png
output_dir: assets_processed/effects/blood_particles
key: auto
prefix: blood_particle
palette: blood
transparency_threshold: 0.036
opacity_threshold: 0.80
merge_distance: 24
min_area: 6
pad: 6
```

The workflow commits generated outputs into `assets_processed/` and also uploads them as a workflow artifact.

## Recommended Ashen Guild workflow

1. Generate a spritesheet with AI.
2. Put the raw PNG in `assets_raw/`.
3. Run the relevant pipeline mode.
4. Check `_preview.png` and the black / white cleaned previews.
5. Manually fix only the few remaining bad frames in Pixelorama, LibreSprite, GIMP or Photopea.
6. Use the final transparent PNGs in the game assets folder.

## Notes

- This pipeline does **not** create missing animations.
- It automates cleaning, slicing, naming, exporting, recoloring and previewing.
- Perfect automatic grouping is not guaranteed when separate effects overlap or have no spacing.
- For best results, keep visible spacing between neighboring sprites in the generated sheet.
