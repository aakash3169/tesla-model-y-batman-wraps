#!/usr/bin/env python3
"""Paint Shop PNGs for 2025+ Model Y Juniper, masked to official Tesla templates."""
import os
import random
import zipfile
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "dist", "Wraps")
os.makedirs(OUT, exist_ok=True)
TEMPLATES = {
    "Prem": os.path.join(ROOT, "templates", "premium_template.png"),
    "Std": os.path.join(ROOT, "templates", "base_template.png"),
}
YELLOW = (245, 196, 0, 255)
BLACK = (12, 12, 14, 255)
RED = (150, 32, 32, 255)

def load_mask(path):
    im = Image.open(path).convert("RGBA")
    px = im.load()
    w, h = im.size
    mask = Image.new("L", (w, h), 0)
    mp = mask.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 128 and r > 200 and g > 200 and b > 200:
                mp[x, y] = 255
    return mask

def components(mask):
    px = mask.load()
    w, h = mask.size
    visited = bytearray(w * h)
    comps = []
    for y in range(h):
        row = y * w
        for x in range(w):
            i = row + x
            if visited[i] or px[x, y] == 0:
                continue
            stack = [(x, y)]
            visited[i] = 1
            minx = maxx = x
            miny = maxy = y
            n = sx = sy = 0
            while stack:
                cx, cy = stack.pop()
                n += 1
                sx += cx
                sy += cy
                minx, maxx = min(minx, cx), max(maxx, cx)
                miny, maxy = min(miny, cy), max(maxy, cy)
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h:
                        j = ny * w + nx
                        if not visited[j] and px[nx, ny]:
                            visited[j] = 1
                            stack.append((nx, ny))
            if n >= 300:
                comps.append({"n": n, "box": (minx, miny, maxx, maxy), "cx": sx / n, "cy": sy / n, "w": maxx - minx + 1, "h": maxy - miny + 1})
    return comps

def classify(comps):
    roles = {}
    for i, c in enumerate(comps):
        c["id"] = i
        roles[i] = "panel"
    for c in comps:
        if c["cy"] < 140 and c["w"] > 400:
            roles[c["id"]] = "front_bumper"
        elif 140 < c["cy"] < 360 and 350 < c["cx"] < 670 and c["w"] > 180 and c["n"] > 20000:
            roles[c["id"]] = "hood"
    for c in comps:
        if roles[c["id"]] != "panel":
            continue
        side = "L" if c["cx"] < 512 else "R"
        if c["cy"] < 400 and c["w"] > 140 and c["h"] > 160:
            roles[c["id"]] = f"fender_{side}"
        elif c["h"] > 350 and c["w"] < 80:
            roles[c["id"]] = f"roof_{side}"
        elif 400 <= c["cy"] < 620 and c["h"] > 160 and c["w"] > 100:
            roles[c["id"]] = f"door_f_{side}"
        elif 620 <= c["cy"] < 780 and c["h"] > 140 and c["w"] > 100:
            roles[c["id"]] = f"door_r_{side}"
        elif c["cy"] >= 800 and c["w"] > 100 and c["h"] > 120 and (c["cx"] < 300 or c["cx"] > 720):
            roles[c["id"]] = f"quarter_{side}"
        elif c["cy"] > 860 and 400 < c["cx"] < 624 and c["w"] > 180 and c["h"] < 90:
            roles[c["id"]] = "liftgate"
        elif c["cy"] > 940 and 400 < c["cx"] < 624:
            roles[c["id"]] = "rear_bumper"
        elif c["n"] < 2500 and 330 < c["cy"] < 430:
            roles[c["id"]] = f"mirror_{side}"
    return roles

def bat_points(cx, cy, s):
    raw = [(0.00, 0.42), (0.10, 0.22), (0.08, 0.05), (0.22, 0.10), (0.38, -0.02), (0.62, -0.28), (0.95, -0.55), (0.72, -0.22), (0.55, -0.05), (0.42, 0.02), (0.28, -0.18), (0.16, -0.42), (0.06, -0.22), (0.00, -0.30)]
    pts = [(cx + x * s, cy + y * s) for x, y in raw]
    pts += [(cx - x * s, cy + y * s) for x, y in reversed(raw[1:])]
    return pts

def draw_bat(draw, cx, cy, s, fill, oval=None):
    if oval:
        ow, oh = oval
        draw.ellipse((cx - ow, cy - oh, cx + ow, cy + oh), fill=YELLOW)
        draw_bat(draw, cx, cy + s * 0.06, s * 0.72, fill)
        return
    draw.polygon(bat_points(cx, cy, s), fill=fill)

def paint(mask, comps, roles, kind):
    w, h = mask.size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    base = {"stealth": (16, 16, 18, 255), "armor": (10, 10, 12, 255), "tactical": (34, 34, 36, 255)}.get(kind, (22, 10, 36, 255))
    draw.bitmap((0, 0), mask, fill=base)
    if kind == "batwing":
        grad = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        gp, mp = grad.load(), mask.load()
        for y in range(h):
            t = y / h
            color = (int(18 + 50 * t), int(8 + 16 * t), int(32 + 70 * t), 255)
            for x in range(w):
                if mp[x, y]:
                    gp[x, y] = color
        img = grad
        draw = ImageDraw.Draw(img)
    if kind == "tactical":
        rnd = random.Random(7)
        mp, px = mask.load(), img.load()
        for _ in range(7000):
            x, y = rnd.randrange(w), rnd.randrange(h)
            if mp[x, y]:
                v = rnd.randint(12, 58)
                px[x, y] = (v, v, v + 2, 255)
    for c in comps:
        role = roles[c["id"]]
        x0, y0, x1, y1 = c["box"]
        cx, cy = c["cx"], c["cy"]
        if role == "hood":
            if kind == "stealth":
                draw_bat(draw, cx, cy + 6, min(c["w"], c["h"]) * 0.34, BLACK, oval=(c["w"] * 0.34, c["h"] * 0.30))
            elif kind == "armor":
                draw_bat(draw, cx, cy, min(c["w"], c["h"]) * 0.42, YELLOW)
            elif kind == "tactical":
                draw_bat(draw, cx, cy, min(c["w"], c["h"]) * 0.46, (12, 12, 12, 255))
            else:
                draw_bat(draw, cx, cy + 4, min(c["w"], c["h"]) * 0.50, (186, 150, 255, 255))
        elif role.startswith("door_"):
            band_h = max(8, int(c["h"] * 0.10))
            yb = y1 - int(c["h"] * 0.16)
            if kind in ("stealth", "armor"):
                draw.rectangle((x0 + 8, yb, x1 - 8, yb + band_h), fill=YELLOW)
            if kind == "armor":
                for k in range(3):
                    nx = x0 + int(c["w"] * (0.55 + k * 0.08))
                    draw.rectangle((nx, yb - 10, nx + 6, yb - 2), fill=YELLOW)
                rnd = random.Random(3 if "L" in role else 4)
                for k in range(8):
                    bx = x0 + 10 + k * int(c["w"] / 9)
                    bh = rnd.randint(6, 18)
                    draw.rectangle((bx, y1 - bh - 4, bx + 6, y1 - 4), fill=(180, 140, 20, 255))
            if kind == "tactical":
                draw.rectangle((x0 + 6, y0 + int(c["h"] * 0.42), x1 - 6, y0 + int(c["h"] * 0.46)), fill=RED)
        elif role.startswith("fender_") and kind == "stealth":
            draw_bat(draw, cx, cy, min(c["w"], c["h"]) * 0.16, YELLOW)
        elif role.startswith("fender_") and kind == "batwing":
            draw_bat(draw, cx, cy, min(c["w"], c["h"]) * 0.18, (186, 150, 255, 220))
        elif role.startswith("quarter_") and kind in ("armor", "stealth"):
            draw_bat(draw, cx, cy, min(c["w"], c["h"]) * 0.28, YELLOW)
        elif role.startswith("quarter_") and kind == "batwing":
            draw_bat(draw, cx, cy, min(c["w"], c["h"]) * 0.26, (186, 150, 255, 255))
        elif role == "liftgate" and kind in ("armor", "stealth"):
            draw_bat(draw, cx, cy, min(c["w"], c["h"]) * 0.55, YELLOW)
        elif role == "front_bumper" and kind == "tactical":
            draw.rectangle((x0 + 20, y0 + int(c["h"] * 0.55), x1 - 20, y0 + int(c["h"] * 0.62)), fill=RED)
        elif role.startswith("roof_") and kind == "armor":
            draw.rectangle((x0, y0, x1, y1), fill=(28, 28, 30, 255))
    img.putalpha(mask)
    return img

def main():
    names = {"stealth": "Gotham_Stealth", "armor": "Dark_Knight", "tactical": "Tactical_Bat", "batwing": "Batwing_Night"}
    files = []
    for trim, path in TEMPLATES.items():
        mask = load_mask(path)
        comps = components(mask)
        for i, c in enumerate(comps):
            c["id"] = i
        roles = classify(comps)
        for kind, stem in names.items():
            img = paint(mask, comps, roles, kind)
            fpath = os.path.join(OUT, f"{stem}_{trim}.png")
            img.save(fpath, "PNG", optimize=True)
            files.append(fpath)
            print("wrote", fpath, os.path.getsize(fpath))
    zpath = os.path.join(ROOT, "dist", "Tesla_Batman_PaintShop.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, "Wraps/" + os.path.basename(f))
    print("zip", zpath)

if __name__ == "__main__":
    main()
