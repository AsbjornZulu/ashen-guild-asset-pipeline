#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, math
from collections import deque
from pathlib import Path
from PIL import Image, ImageDraw

def hex_color(s):
    named = {"magenta":"#FF00FF", "green":"#00FF00", "blue":"#0000FF", "cyan":"#00FFFF"}
    s = named.get(s.lower(), s).strip()
    if s.startswith("#"): s = s[1:]
    if len(s) != 6: raise ValueError("Use color like #FF00FF")
    return tuple(int(s[i:i+2], 16) for i in (0,2,4))

def dist2(a,b):
    return sum((a[i]-b[i])**2 for i in range(3))

def remove_chroma(img, key=(255,0,255), tolerance=45, despill=False):
    img = img.convert("RGBA")
    px = img.load()
    w,h = img.size
    transparent = [[False]*w for _ in range(h)]

    for y in range(h):
        for x in range(w):
            r,g,b,a = px[x,y]
            if a == 0 or dist2((r,g,b), key) <= tolerance*tolerance:
                px[x,y] = (r,g,b,0)
                transparent[y][x] = True

    if not despill:
        return img

    def near_clear(x,y):
        for yy in range(max(0,y-1), min(h,y+2)):
            for xx in range(max(0,x-1), min(w,x+2)):
                if transparent[yy][xx]: return True
        return False

    # Simple magenta/green/blue despill on border pixels.
    for y in range(h):
        for x in range(w):
            r,g,b,a = px[x,y]
            if a == 0 or not near_clear(x,y):
                continue

            if key == (255,0,255): # magenta fringe: reduce red/blue if both dominate green
                if r > g + 20 and b > g + 20:
                    target = max(g, min(r,b)-20)
                    r = int(r - (r-target)*0.7)
                    b = int(b - (b-target)*0.7)
                    px[x,y] = (max(0,min(255,r)), g, max(0,min(255,b)), a)
            elif key == (0,255,0): # green fringe
                if g > r + 20 and g > b + 20:
                    target = max(r,b)
                    g = int(g - (g-target)*0.7)
                    px[x,y] = (r, max(0,min(255,g)), b, a)
            elif key == (0,0,255): # blue fringe
                if b > r + 20 and b > g + 20:
                    target = max(r,g)
                    b = int(b - (b-target)*0.7)
                    px[x,y] = (r, g, max(0,min(255,b)), a)
    return img

def crop_alpha(img, pad=4):
    img = img.convert("RGBA")
    box = img.getchannel("A").getbbox()
    if not box: return img
    x0,y0,x1,y1 = box
    return img.crop((max(0,x0-pad), max(0,y0-pad), min(img.width,x1+pad), min(img.height,y1+pad)))

def preview(out_dir, files):
    if not files: return
    imgs = [Image.open(f).convert("RGBA") for f in files]
    cw = max(i.width for i in imgs) + 12
    ch = max(i.height for i in imgs) + 12
    cols = min(10, max(1, math.ceil(math.sqrt(len(imgs)))))
    rows = math.ceil(len(imgs)/cols)
    canvas = Image.new("RGBA", (cols*cw, rows*ch), (25,25,25,255))
    draw = ImageDraw.Draw(canvas)
    for i,img in enumerate(imgs):
        x = (i%cols)*cw + (cw-img.width)//2
        y = (i//cols)*ch + (ch-img.height)//2
        canvas.alpha_composite(img, (x,y))
        draw.text(((i%cols)*cw+2, (i//cols)*ch+2), str(i+1), fill=(220,220,220,255))
    canvas.save(Path(out_dir)/"_preview.png")

def cmd_upscale(a):
    img = Image.open(a.input).convert("RGBA")
    out = img.resize((img.width*a.scale, img.height*a.scale), Image.Resampling.NEAREST)
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    out.save(a.output)
    print(f"Original: {img.width}x{img.height}")
    print(f"Upscaled: {out.width}x{out.height}")
    print(f"Saved: {a.output}")

def cmd_clean(a):
    img = Image.open(a.input).convert("RGBA")
    out = remove_chroma(img, hex_color(a.key), a.tolerance, a.despill)
    if a.crop: out = crop_alpha(out, a.pad)
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    out.save(a.output)
    print(f"Saved: {a.output}")

def name_for(prefix, rows, row, cols, col):
    dirs4 = ["north","south","east","west"]
    dirs8 = ["north","north_east","east","south_east","south","south_west","west","north_west"]
    dirs = dirs8 if rows == 8 else dirs4 if rows == 4 else [f"row{i+1}" for i in range(rows)]
    d = dirs[row] if row < len(dirs) else f"row{row+1}"
    if cols == 14:
        if col < 4: return f"{prefix}_{d}_idle_{col+1:02d}.png"
        if col < 10: return f"{prefix}_{d}_walk_{col-3:02d}.png"
        return f"{prefix}_{d}_attack_{col-9:02d}.png"
    return f"{prefix}_{d}_{col+1:02d}.png"

def cmd_grid(a):
    out_dir = Path(a.output_dir); out_dir.mkdir(parents=True, exist_ok=True)
    img = Image.open(a.input).convert("RGBA")
    if a.clean:
        img = remove_chroma(img, hex_color(a.key), a.tolerance, a.despill)

    cw, ch = img.width // a.cols, img.height // a.rows
    manifest, files = [], []

    for r in range(a.rows):
        for c in range(a.cols):
            x0,y0 = c*cw, r*ch
            x1 = img.width if c == a.cols-1 else (c+1)*cw
            y1 = img.height if r == a.rows-1 else (r+1)*ch
            frame = img.crop((x0,y0,x1,y1))
            if a.crop: frame = crop_alpha(frame, a.pad)
            fn = name_for(a.prefix, a.rows, r, a.cols, c)
            path = out_dir / fn
            frame.save(path)
            files.append(path)
            manifest.append({"filename":fn,"row":r+1,"col":c+1,"source_bbox":[x0,y0,x1-x0,y1-y0],"width":frame.width,"height":frame.height})

    (out_dir/"manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    preview(out_dir, files)
    print(f"Saved {len(files)} frames to {out_dir}")

def alpha_mask(img):
    img = img.convert("RGBA"); px = img.load(); w,h = img.size
    return [[px[x,y][3] > 0 for x in range(w)] for y in range(h)]

def components(mask, min_area):
    h = len(mask); w = len(mask[0]) if h else 0
    seen = [[False]*w for _ in range(h)]
    res = []
    for y in range(h):
        for x in range(w):
            if seen[y][x] or not mask[y][x]: continue
            q = deque([(x,y)]); seen[y][x] = True
            minx=maxx=x; miny=maxy=y; area=0
            while q:
                cx,cy = q.popleft(); area += 1
                minx,miny,maxx,maxy = min(minx,cx),min(miny,cy),max(maxx,cx),max(maxy,cy)
                for nx,ny in ((cx+1,cy),(cx-1,cy),(cx,cy+1),(cx,cy-1)):
                    if 0 <= nx < w and 0 <= ny < h and mask[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True; q.append((nx,ny))
            if area >= min_area: res.append((minx,miny,maxx+1,maxy+1,area))
    return sorted(res, key=lambda b:(b[1],b[0]))

def cmd_components(a):
    out_dir = Path(a.output_dir); out_dir.mkdir(parents=True, exist_ok=True)
    img = Image.open(a.input).convert("RGBA")
    img = remove_chroma(img, hex_color(a.key), a.tolerance, a.despill)
    boxes = components(alpha_mask(img), a.min_area)
    manifest, files = [], []
    for i,(x0,y0,x1,y1,area) in enumerate(boxes,1):
        x0,y0,x1,y1 = max(0,x0-a.pad), max(0,y0-a.pad), min(img.width,x1+a.pad), min(img.height,y1+a.pad)
        crop = img.crop((x0,y0,x1,y1))
        fn = f"{a.prefix}_{i:03d}.png"
        path = out_dir / fn
        crop.save(path)
        files.append(path)
        manifest.append({"filename":fn,"x":x0,"y":y0,"width":crop.width,"height":crop.height,"area":area,"category":"unknown"})
    (out_dir/"manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    preview(out_dir, files)
    print(f"Saved {len(files)} assets to {out_dir}")

def main():
    p = argparse.ArgumentParser("Ashen Guild free pixel-art asset pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    up = sub.add_parser("upscale")
    up.add_argument("input"); up.add_argument("output"); up.add_argument("--scale", type=int, default=4)
    up.set_defaults(func=cmd_upscale)

    clean = sub.add_parser("clean")
    clean.add_argument("input"); clean.add_argument("output")
    clean.add_argument("--key", default="#FF00FF"); clean.add_argument("--tolerance", type=int, default=45)
    clean.add_argument("--despill", action="store_true"); clean.add_argument("--crop", action="store_true")
    clean.add_argument("--pad", type=int, default=4)
    clean.set_defaults(func=cmd_clean)

    grid = sub.add_parser("slice-grid")
    grid.add_argument("input"); grid.add_argument("output_dir")
    grid.add_argument("--rows", type=int, required=True); grid.add_argument("--cols", type=int, required=True)
    grid.add_argument("--key", default="#FF00FF"); grid.add_argument("--tolerance", type=int, default=45)
    grid.add_argument("--despill", action="store_true"); grid.add_argument("--pad", type=int, default=4)
    grid.add_argument("--prefix", default="sprite")
    grid.add_argument("--no-clean", dest="clean", action="store_false"); grid.set_defaults(clean=True)
    grid.add_argument("--no-crop", dest="crop", action="store_false"); grid.set_defaults(crop=True)
    grid.set_defaults(func=cmd_grid)

    comp = sub.add_parser("slice-components")
    comp.add_argument("input"); comp.add_argument("output_dir")
    comp.add_argument("--key", default="#FF00FF"); comp.add_argument("--tolerance", type=int, default=45)
    comp.add_argument("--despill", action="store_true"); comp.add_argument("--min-area", type=int, default=64)
    comp.add_argument("--pad", type=int, default=4); comp.add_argument("--prefix", default="asset")
    comp.set_defaults(func=cmd_components)

    a = p.parse_args()
    a.func(a)

if __name__ == "__main__":
    main()
