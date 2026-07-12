#!/usr/bin/env python3
"""Clean magenta-background sprite atlases and auto-slice individual FX sprites.

Designed for AI-generated pixel-art sheets where magenta has bled into
anti-aliased sprite borders. Uses a Color-to-Alpha style unmixing pass,
near-key knockout, edge despill, optional luminance palette mapping, and
proximity-based fragment grouping.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import deque
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageColor, ImageDraw

RGB = tuple[int, int, int]
RGBA = tuple[int, int, int, int]
Box = tuple[int, int, int, int, int]

PALETTES: dict[str, list[RGB]] = {
    "blood": [(26, 5, 6), (42, 10, 12), (74, 15, 18), (110, 22, 27), (138, 31, 36)],
    "mud": [(20, 16, 12), (44, 33, 22), (78, 58, 39), (114, 90, 62), (150, 124, 92)],
}


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def color_distance_sq(a: RGB, b: RGB) -> int:
    return sum((a[i] - b[i]) ** 2 for i in range(3))


def parse_key(value: str, image: Image.Image) -> RGB:
    if value.lower() == "auto":
        return detect_border_color(image)
    return ImageColor.getrgb(value)


def detect_border_color(image: Image.Image) -> RGB:
    image = image.convert("RGBA")
    px = image.load()
    width, height = image.size
    counts: dict[RGB, int] = {}

    for x in range(width):
        for y in (0, height - 1):
            r, g, b, a = px[x, y]
            if a:
                counts[(r, g, b)] = counts.get((r, g, b), 0) + 1
    for y in range(height):
        for x in (0, width - 1):
            r, g, b, a = px[x, y]
            if a:
                counts[(r, g, b)] = counts.get((r, g, b), 0) + 1

    return max(counts.items(), key=lambda item: item[1])[0] if counts else (255, 0, 255)


def color_to_alpha(
    image: Image.Image,
    key: RGB,
    transparency_threshold: float,
    opacity_threshold: float,
) -> Image.Image:
    """Approximate GIMP Color to Alpha while preserving anti-aliased edges."""
    image = image.convert("RGBA")
    output = Image.new("RGBA", image.size)
    src = image.load()
    dst = output.load()
    kr, kg, kb = (channel / 255.0 for channel in key)

    for y in range(image.height):
        for x in range(image.width):
            r, g, b, original_alpha = src[x, y]
            if original_alpha == 0:
                dst[x, y] = (0, 0, 0, 0)
                continue

            channels = (r / 255.0, g / 255.0, b / 255.0)
            key_channels = (kr, kg, kb)
            alpha_candidates: list[float] = []

            for channel, key_channel in zip(channels, key_channels):
                if channel > key_channel:
                    alpha_candidates.append(
                        (channel - key_channel) / (1.0 - key_channel)
                        if key_channel < 1.0 else 0.0
                    )
                elif channel < key_channel:
                    alpha_candidates.append(
                        (key_channel - channel) / key_channel
                        if key_channel > 0.0 else 0.0
                    )
                else:
                    alpha_candidates.append(0.0)

            alpha = max(alpha_candidates) * (original_alpha / 255.0)
            if alpha <= transparency_threshold:
                dst[x, y] = (0, 0, 0, 0)
                continue
            if alpha >= opacity_threshold:
                alpha = 1.0

            nr = clamp01((channels[0] - kr * (1.0 - alpha)) / alpha)
            ng = clamp01((channels[1] - kg * (1.0 - alpha)) / alpha)
            nb = clamp01((channels[2] - kb * (1.0 - alpha)) / alpha)
            dst[x, y] = (
                round(nr * 255),
                round(ng * 255),
                round(nb * 255),
                round(alpha * 255),
            )
    return output


def knockout_near_key(image: Image.Image, key: RGB, tolerance: int) -> Image.Image:
    image = image.convert("RGBA")
    px = image.load()
    tolerance_sq = tolerance * tolerance
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = px[x, y]
            if a and color_distance_sq((r, g, b), key) <= tolerance_sq:
                px[x, y] = (r, g, b, 0)
    return image


def despill_edges(image: Image.Image, key: RGB, strength: float = 0.8) -> Image.Image:
    image = image.convert("RGBA")
    px = image.load()
    alpha = image.getchannel("A").load()

    def touches_transparency(x: int, y: int) -> bool:
        for yy in range(max(0, y - 1), min(image.height, y + 2)):
            for xx in range(max(0, x - 1), min(image.width, x + 2)):
                if alpha[xx, yy] == 0:
                    return True
        return False

    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = px[x, y]
            if not a or not touches_transparency(x, y):
                continue

            if key[0] > 200 and key[2] > 200 and key[1] < 80:
                if r > g + 10 and b > g + 10:
                    reduction = round(min(r - g, b - g) * strength)
                    px[x, y] = (max(0, r - reduction), g, max(0, b - reduction), a)
            elif key[1] > 200:
                excess = max(0, g - max(r, b))
                px[x, y] = (r, max(0, round(g - excess * strength)), b, a)
            elif key[2] > 200:
                excess = max(0, b - max(r, g))
                px[x, y] = (r, g, max(0, round(b - excess * strength)), a)
    return image


def recolor_luminance(image: Image.Image, palette_name: str) -> Image.Image:
    palette = PALETTES[palette_name]
    output = Image.new("RGBA", image.size)
    src = image.convert("RGBA").load()
    dst = output.load()
    max_index = len(palette) - 1

    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = src[x, y]
            if not a:
                continue
            luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
            position = luminance * max_index
            low = int(math.floor(position))
            high = min(max_index, low + 1)
            blend = position - low
            color_a, color_b = palette[low], palette[high]
            dst[x, y] = (
                round(color_a[0] * (1 - blend) + color_b[0] * blend),
                round(color_a[1] * (1 - blend) + color_b[1] * blend),
                round(color_a[2] * (1 - blend) + color_b[2] * blend),
                a,
            )
    return output


def alpha_mask(image: Image.Image) -> list[list[bool]]:
    px = image.convert("RGBA").load()
    return [[px[x, y][3] > 0 for x in range(image.width)] for y in range(image.height)]


def find_components(mask: list[list[bool]], min_area: int) -> list[Box]:
    height = len(mask)
    width = len(mask[0]) if height else 0
    seen = [[False] * width for _ in range(height)]
    boxes: list[Box] = []

    for y in range(height):
        for x in range(width):
            if seen[y][x] or not mask[y][x]:
                continue
            queue = deque([(x, y)])
            seen[y][x] = True
            x0 = x1 = x
            y0 = y1 = y
            area = 0

            while queue:
                current_x, current_y = queue.popleft()
                area += 1
                x0, x1 = min(x0, current_x), max(x1, current_x)
                y0, y1 = min(y0, current_y), max(y1, current_y)
                for next_x, next_y in (
                    (current_x + 1, current_y),
                    (current_x - 1, current_y),
                    (current_x, current_y + 1),
                    (current_x, current_y - 1),
                ):
                    if (
                        0 <= next_x < width
                        and 0 <= next_y < height
                        and mask[next_y][next_x]
                        and not seen[next_y][next_x]
                    ):
                        seen[next_y][next_x] = True
                        queue.append((next_x, next_y))

            if area >= min_area:
                boxes.append((x0, y0, x1 + 1, y1 + 1, area))
    return sorted(boxes, key=lambda box: (box[1], box[0]))


def boxes_are_close(a: Box, b: Box, distance: int) -> bool:
    ax0, ay0, ax1, ay1, _ = a
    bx0, by0, bx1, by1, _ = b
    horizontal_gap = max(0, max(ax0, bx0) - min(ax1, bx1))
    vertical_gap = max(0, max(ay0, by0) - min(ay1, by1))
    return horizontal_gap <= distance and vertical_gap <= distance


def merge_nearby_boxes(boxes: list[Box], distance: int) -> list[Box]:
    boxes = boxes[:]
    changed = True
    while changed:
        changed = False
        merged: list[Box] = []
        used = [False] * len(boxes)

        for index, box in enumerate(boxes):
            if used[index]:
                continue
            x0, y0, x1, y1, area = box
            used[index] = True
            expanded = True

            while expanded:
                expanded = False
                for other_index, other_box in enumerate(boxes):
                    if used[other_index]:
                        continue
                    current = (x0, y0, x1, y1, area)
                    if boxes_are_close(current, other_box, distance):
                        ox0, oy0, ox1, oy1, other_area = other_box
                        x0, y0 = min(x0, ox0), min(y0, oy0)
                        x1, y1 = max(x1, ox1), max(y1, oy1)
                        area += other_area
                        used[other_index] = True
                        expanded = True
                        changed = True
            merged.append((x0, y0, x1, y1, area))
        boxes = sorted(merged, key=lambda box: (box[1], box[0]))
    return boxes


def create_preview(output_dir: Path, files: Iterable[Path]) -> None:
    files = list(files)
    if not files:
        return
    images = [Image.open(path).convert("RGBA") for path in files]
    cell_width = max(image.width for image in images) + 12
    cell_height = max(image.height for image in images) + 12
    columns = min(10, max(1, math.ceil(math.sqrt(len(images)))))
    rows = math.ceil(len(images) / columns)
    canvas = Image.new("RGBA", (columns * cell_width, rows * cell_height), (25, 25, 25, 255))
    draw = ImageDraw.Draw(canvas)

    for index, image in enumerate(images):
        x = (index % columns) * cell_width + (cell_width - image.width) // 2
        y = (index // columns) * cell_height + (cell_height - image.height) // 2
        canvas.alpha_composite(image, (x, y))
        draw.text(((index % columns) * cell_width + 2, (index // columns) * cell_height + 2), str(index + 1), fill="white")
    canvas.save(output_dir / "_preview.png")


def preview_background(image: Image.Image, path: Path, color: RGBA) -> None:
    canvas = Image.new("RGBA", image.size, color)
    canvas.alpha_composite(image, (0, 0))
    canvas.save(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean and slice magenta-background FX sprite atlases")
    parser.add_argument("input", help="Input PNG atlas")
    parser.add_argument("output_dir", help="Output directory")
    parser.add_argument("--key", default="auto", help="Background key color, e.g. #FF00FF or auto")
    parser.add_argument("--transparency-threshold", type=float, default=0.036)
    parser.add_argument("--opacity-threshold", type=float, default=0.80)
    parser.add_argument("--knockout-tolerance", type=int, default=24)
    parser.add_argument("--despill-strength", type=float, default=0.80)
    parser.add_argument("--palette", choices=["none", "blood", "mud"], default="none")
    parser.add_argument("--merge-distance", type=int, default=24)
    parser.add_argument("--min-area", type=int, default=6)
    parser.add_argument("--pad", type=int, default=6)
    parser.add_argument("--prefix", default="fx")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    source = Image.open(input_path).convert("RGBA")
    key = parse_key(args.key, source)
    cleaned = color_to_alpha(source, key, args.transparency_threshold, args.opacity_threshold)
    cleaned = knockout_near_key(cleaned, key, args.knockout_tolerance)
    cleaned = despill_edges(cleaned, key, args.despill_strength)

    if args.palette != "none":
        cleaned = recolor_luminance(cleaned, args.palette)

    cleaned.save(output_dir / "_cleaned.png")
    preview_background(cleaned, output_dir / "_cleaned_preview_black.png", (20, 20, 20, 255))
    preview_background(cleaned, output_dir / "_cleaned_preview_white.png", (240, 240, 240, 255))

    boxes = find_components(alpha_mask(cleaned), args.min_area)
    if args.merge_distance > 0:
        boxes = merge_nearby_boxes(boxes, args.merge_distance)

    manifest: list[dict] = []
    files: list[Path] = []
    for index, (x0, y0, x1, y1, area) in enumerate(boxes, start=1):
        x0 = max(0, x0 - args.pad)
        y0 = max(0, y0 - args.pad)
        x1 = min(cleaned.width, x1 + args.pad)
        y1 = min(cleaned.height, y1 + args.pad)
        sprite = cleaned.crop((x0, y0, x1, y1))
        filename = f"{args.prefix}_{index:03d}.png"
        output_path = output_dir / filename
        sprite.save(output_path)
        files.append(output_path)
        manifest.append({
            "filename": filename,
            "source_bbox": [x0, y0, x1 - x0, y1 - y0],
            "width": sprite.width,
            "height": sprite.height,
            "pixel_area": area,
            "key_color": list(key),
            "palette": args.palette,
        })

    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    create_preview(output_dir, files)
    print(f"Detected key color: {key}")
    print(f"Exported {len(files)} sprites to {output_dir}")


if __name__ == "__main__":
    main()
