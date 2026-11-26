#!/usr/bin/env python3
"""Theme-agnostic procedural banner, shop sign, billboard, and decal texture generator.
Supports 4 built-in theme starter presets (cyberpunk, fantasy, scifi, market) OR any
custom JSON spec file (--spec signs.json) with cross-platform font auto-discovery."""
import argparse
import json
import os
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

FONT_CANDIDATES = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/yugothb.ttc",
]

PRESETS = {
    "cyberpunk": [
        {"file": "sign_hero_main.png", "size": [1024, 512], "bg": [10, 12, 24], "border": [255, 32, 148], "fg": [0, 245, 255], "title": "NOODLE LAB", "sub": "OPEN 24H // SECTOR 09", "glow": True},
        {"file": "sign_clinic.png",    "size": [1024, 512], "bg": [8, 20, 28],  "border": [0, 245, 220],  "fg": [210, 255, 250], "title": "BIOMED LAB", "sub": "AUGMENTATION // 2F", "glow": True},
        {"file": "sign_vertical_1.png","size": [384, 1024], "bg": [6, 20, 34],  "border": [0, 245, 255],  "fg": [180, 255, 255], "title": "SYNTH",      "sub": "DISTRICT 09", "vertical": True, "glow": True},
        {"file": "sign_vertical_2.png","size": [384, 1024], "bg": [30, 6, 26],  "border": [255, 30, 148], "fg": [255, 195, 232], "title": "ARCADE",     "sub": "LEVEL 02",    "vertical": True, "glow": True},
        {"file": "sign_blade_1.png",   "size": [512, 320],  "bg": [32, 24, 4],  "border": [255, 204, 18], "fg": [255, 248, 200], "title": "HARDWARE",   "sub": "PARTS & CORES", "glow": True},
    ],
    "fantasy": [
        {"file": "sign_hero_main.png", "size": [1024, 512], "bg": [44, 28, 18], "border": [212, 168, 86], "fg": [248, 232, 196], "title": "THE GILDED OAR", "sub": "TAVERN & INN", "glow": False},
        {"file": "sign_guild.png",     "size": [1024, 512], "bg": [24, 34, 48], "border": [196, 158, 78], "fg": [242, 234, 214], "title": "GUILD HALL",     "sub": "CHARTERS & MAPS", "glow": False},
        {"file": "banner_vertical_1.png","size": [384, 1024],"bg": [112, 26, 28],"border": [216, 174, 88],"fg": [248, 234, 198], "title": "MARKET",         "sub": "NORTH QUAY", "vertical": True, "glow": False},
        {"file": "banner_vertical_2.png","size": [384, 1024],"bg": [22, 54, 46], "border": [216, 174, 88],"fg": [240, 236, 212], "title": "ALCHEMY",        "sub": "TONICS",     "vertical": True, "glow": False},
    ],
    "scifi": [
        {"file": "sign_hero_main.png", "size": [1024, 512], "bg": [16, 22, 30], "border": [68, 196, 255], "fg": [232, 246, 255], "title": "BAY 04 // DOCK", "sub": "ORBITAL TRANSIT", "glow": True},
        {"file": "sign_cargo.png",     "size": [1024, 512], "bg": [28, 24, 16], "border": [255, 168, 32], "fg": [255, 238, 200], "title": "CARGO LOCK",     "sub": "PRESSURIZED DECK", "glow": True},
        {"file": "sign_vertical_1.png","size": [384, 1024], "bg": [14, 20, 28], "border": [68, 196, 255], "fg": [210, 242, 255], "title": "HANGAR",         "sub": "DECK 04", "vertical": True, "glow": True},
    ],
    "market": [
        {"file": "sign_hero_main.png", "size": [1024, 512], "bg": [242, 232, 214],"border": [176, 74, 44], "fg": [42, 32, 26],   "title": "ARTISAN ROAST",  "sub": "FRESH BAKERY & CAFE", "glow": False},
        {"file": "sign_spices.png",    "size": [1024, 512], "bg": [36, 56, 68],   "border": [226, 176, 84],"fg": [250, 242, 226],"title": "SPICE HOUSE",    "sub": "GRAND BAZAAR", "glow": False},
        {"file": "banner_vertical_1.png","size": [384, 1024],"bg": [178, 72, 46], "border": [242, 218, 174],"fg": [252, 244, 230],"title": "BAZAAR",       "sub": "EST. 1894", "vertical": True, "glow": False},
    ],
}


def find_font(custom_font=None):
    if custom_font and os.path.exists(custom_font):
        return custom_font
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def load_font(fp, size):
    if fp:
        try:
            return ImageFont.truetype(fp, size)
        except Exception:
            pass
    return ImageFont.load_default()


def apply_glow(img):
    w, h = img.size
    out = ImageChops.lighter(img, img.filter(ImageFilter.GaussianBlur(radius=5)))
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for y in range(0, h, 4):
        d.line((0, y, w, y), fill=(0, 0, 0, 24), width=1)
    return Image.alpha_composite(out.convert("RGBA"), overlay).convert("RGB")


def render_sign(spec, out_dir, fp):
    w, h = spec.get("size", [1024, 512])
    bg = tuple(spec.get("bg", [18, 22, 30]))
    border = tuple(spec.get("border", [235, 175, 65]))
    fg = tuple(spec.get("fg", [245, 245, 245]))
    title = spec.get("title", "WORLD SIGN")
    sub = spec.get("sub", "")
    vertical = bool(spec.get("vertical", h > w))

    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    pad = max(12, min(w, h) // 24)
    d.rounded_rectangle((pad, pad, w - pad, h - pad), radius=pad, outline=border, width=max(6, pad // 2))

    if vertical:
        chars = list(title)
        fsize = max(48, min(128, int((h - 240) / max(1, len(chars)) * 0.85)))
        f = load_font(fp, fsize)
        step = int((h - 220) / max(1, len(chars)))
        y = 80
        for ch in chars:
            b = d.textbbox((0, 0), ch, font=f)
            d.text(((w - (b[2] - b[0])) / 2 - b[0], y - b[1]), ch, font=f, fill=fg)
            y += step
        if sub:
            fs = load_font(fp, max(24, w // 10))
            bs = d.textbbox((0, 0), sub, font=fs)
            d.text(((w - (bs[2] - bs[0])) / 2 - bs[0], h - pad - 68), sub, font=fs, fill=border)
    else:
        f1 = load_font(fp, max(54, min(124, int(w / max(6, len(title)) * 1.25))))
        b1 = d.textbbox((0, 0), title, font=f1)
        d.text(((w - (b1[2] - b1[0])) / 2 - b1[0], h * 0.30 - (b1[3] - b1[1]) * 0.5 - b1[1]), title, font=f1, fill=fg)
        if sub:
            f2 = load_font(fp, max(28, h // 10))
            b2 = d.textbbox((0, 0), sub, font=f2)
            d.text(((w - (b2[2] - b2[0])) / 2 - b2[0], h * 0.68 - (b2[3] - b2[1]) * 0.5 - b2[1]), sub, font=f2, fill=border)

    if spec.get("glow", False):
        img = apply_glow(img)
    out_path = os.path.join(out_dir, spec["file"])
    img.save(out_path)
    return out_path


def main():
    p = argparse.ArgumentParser(description="Generate procedural signage/banner textures for any 3D world theme.")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--preset", default="market", choices=sorted(PRESETS.keys()))
    p.add_argument("--spec", default=None, help="Optional custom JSON list of sign definitions")
    p.add_argument("--font", default=None, help="Optional custom TTF/TTC font path")
    args = p.parse_args()

    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    fp = find_font(args.font)
    specs = json.load(open(args.spec, "r", encoding="utf-8")) if args.spec else PRESETS[args.preset]
    for spec in specs:
        render_sign(spec, out_dir, fp)
    print(f"[SIGNAGE OK] Generated {len(specs)} textures in {out_dir} (font={fp or 'default'})")


if __name__ == "__main__":
    main()
