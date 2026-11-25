"""
Universal Kinetic 3D Showreel VFX & Motion-Graphics Compositor.
Composites any transparent RGBA Blender render sequence onto pure #FFFFFF white
with dynamic geometry-locked CV tracking webs, B&W specular node graphs,
morphing Bayer-dithered halftone waves, inverted-contrast kinetic typography
with pixel-outline leading glyphs, resolution-scaled HUD telemetry, and FFmpeg MP4 output.

Usage:
  uv run --with numpy --with pillow python3 compose_showreel.py \
    --renders ./renders --out ./final.mp4 --mode fast-10s --aspect 16:9 \
    --brand "MOTIONVIZ" --word1 "MOTION" --word2 "VIZ" --model "911 GT3"
"""
import argparse
import glob
import math
import os
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_SANS = [
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/SFNS.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]
FONT_MONO = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/SFNSMono.ttf",
    "/System/Library/Fonts/Courier.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "C:/Windows/Fonts/consola.ttf",
]

BAYER_4 = np.array([
    [0,  8,  2, 10],
    [12, 4, 14,  6],
    [3, 11,  1,  9],
    [15, 7, 13,  5],
], dtype=np.float32) / 16.0


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--renders", required=True, help="Directory with frame_0001.png ...")
    p.add_argument("--out", required=True, help="Output .mp4 path")
    p.add_argument("--mode", choices=["topdown", "fast-10s", "full-25s"], default="fast-10s")
    p.add_argument("--aspect", choices=["16:9", "4:5"], default="16:9")
    p.add_argument("--brand", default="MOTIONVIZ")
    p.add_argument("--word1", default="MOTION")
    p.add_argument("--word2", default="VIZ")
    p.add_argument("--model", default="911 GT3")
    p.add_argument("--accent-rgb", default="18,42,245", help="R,G,B accent color (0-255)")
    p.add_argument("--fps", type=int, default=24)
    return p.parse_args()


def load_font(candidates, size):
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def composite_on_white(rgba_img, darken=1.0):
    arr = np.asarray(rgba_img, dtype=np.float32) / 255.0
    rgb = np.clip(arr[..., :3] * darken, 0.0, 1.0)
    a = arr[..., 3:4]
    out = rgb * a + 1.0 * (1.0 - a)
    return Image.fromarray((np.clip(out, 0.0, 1.0) * 255.0).astype(np.uint8), "RGB")


def alpha_mask(rgba_img, thresh=0.22):
    return (np.asarray(rgba_img, dtype=np.float32)[..., 3] / 255.0) > thresh


def luminance(rgba_img):
    arr = np.asarray(rgba_img, dtype=np.float32) / 255.0
    return (0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]) * arr[..., 3]


def mask_bbox(mask, W, H):
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return (W // 5, H // 5, W * 4 // 5, H * 4 // 5)
    return (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))


def pixelate_silhouette(mask, W, H, block=20, fg=(0, 0, 0), bg=(255, 255, 255)):
    bh, bw = H // block, W // block
    small = mask[:bh * block, :bw * block].reshape(bh, block, bw, block).mean(axis=(1, 3)) > 0.34
    up = np.repeat(np.repeat(small, block, axis=0), block, axis=1)
    canvas = np.full((H, W, 3), bg, dtype=np.uint8)
    canvas[:up.shape[0], :up.shape[1]][up] = fg
    return Image.fromarray(canvas, "RGB")


def draw_kinetic_title(img, text, W, H, font_size, vertical=False,
                       pixel_first_outline=False, pixel_last=False, invert_contrast=True):
    """
    Inverted-contrast kinetic typography (jet-black over pure white studio, crisp white
    over dark car body) with optional chunky pixelated-outline leading glyph!
    """
    font = load_font(FONT_SANS, font_size)
    tmp_w = max(W, font_size * (len(text) + 2))
    tmp_h = int(font_size * 1.65)
    layer = Image.new("RGBA", (tmp_w, tmp_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    widths = [(draw.textbbox((0, 0), ch, font=font)[2] - draw.textbbox((0, 0), ch, font=font)[0]) + int(font_size * 0.06) for ch in text]
    cur_x = (tmp_w - sum(widths)) // 2
    base_y = (tmp_h - font_size) // 2

    for idx, ch in enumerate(text):
        c_layer = Image.new("RGBA", (tmp_w, tmp_h), (0, 0, 0, 0))
        c_draw = ImageDraw.Draw(c_layer)
        if pixel_first_outline and idx == 0:
            c_draw.text((cur_x, base_y), ch, font=font, fill=(0, 0, 0, 0),
                        stroke_width=max(5, font_size // 18), stroke_fill=(255, 255, 255, 255))
            s = max(4, font_size // 32)
            c_layer = c_layer.resize((tmp_w // s, tmp_h // s), Image.Resampling.NEAREST).resize((tmp_w, tmp_h), Image.Resampling.NEAREST)
        elif pixel_last and idx == len(text) - 1:
            c_draw.text((cur_x, base_y), ch, font=font, fill=(255, 255, 255, 160))
            s = max(4, font_size // 36)
            c_layer = c_layer.resize((tmp_w // s, tmp_h // s), Image.Resampling.NEAREST).resize((tmp_w, tmp_h), Image.Resampling.NEAREST)
        else:
            c_draw.text((cur_x, base_y), ch, font=font, fill=(255, 255, 255, 245))
        layer = Image.alpha_composite(layer, c_layer)
        cur_x += widths[idx]

    if vertical:
        layer = layer.rotate(-90, expand=True)
    bbox = layer.getbbox()
    if bbox:
        layer = layer.crop(bbox)
    px = (W - layer.width) // 2
    py = (H - layer.height) // 2

    if invert_contrast:
        base = np.asarray(img, dtype=np.float32)
        full_txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        full_txt.paste(layer, (px, py))
        t_arr = np.asarray(full_txt, dtype=np.float32)
        ta = (t_arr[..., 3:4] / 255.0) * 0.93
        blended = base * (1.0 - ta) + (255.0 - base) * ta
        return Image.fromarray(np.clip(blended, 0, 255).astype(np.uint8), "RGB")

    out = img.convert("RGBA")
    out.alpha_composite(layer, (px, py))
    return out.convert("RGB")


def draw_hud(img, W, H, frame_idx, total_frames, brand, model, cam_tag, accent_rgb):
    scale = W / 1920.0
    f_big = load_font(FONT_MONO, max(11, int(24 * scale)))
    f_sub = load_font(FONT_MONO, max(10, int(20 * scale)))
    out = img.convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    x, y = int(52 * scale), int(40 * scale)
    step = int(30 * scale)
    v1 = 7678 + (frame_idx * 31) % 900
    freq = 34.84 + math.sin(frame_idx * 0.55) * 0.40
    d.text((x, y),            f"{brand} // {model}", font=f_big, fill=(*accent_rgb, 245))
    d.text((x, y + step),     cam_tag, font=f_sub, fill=(20, 22, 28, 225))
    d.text((x, y + step * 2), f"TRACE {v1}   F:{frame_idx + 1:03d}/{total_frames:03d}   {freq:05.2f}HZ", font=f_sub, fill=(20, 22, 28, 225))
    out.alpha_composite(ov)
    return out.convert("RGB")


def render_accent_glitch(rgba_img, W, H, frame_idx, total_frames, brand, model, cam_tag, accent_rgb):
    base = composite_on_white(rgba_img, darken=1.15)
    arr = np.asarray(base, dtype=np.uint8).copy()
    mask = alpha_mask(rgba_img)
    lum = luminance(rgba_img)
    x0b, y0b, x1b, y1b = mask_bbox(mask, W, H)
    cx_b, hw_b = (x0b + x1b) * 0.5, max(1.0, (x1b - x0b) * 0.5)

    block = max(10, W // 120)
    bh, bw = H // block, W // block
    m_small = mask[:bh * block, :bw * block].reshape(bh, block, bw, block).mean(axis=(1, 3)) > 0.24
    l_small = lum[:bh * block, :bw * block].reshape(bh, block, bw, block).mean(axis=(1, 3))
    rng = np.random.default_rng(7700 + frame_idx * 101)

    for y in range(bh):
        for x in range(bw):
            if not m_small[y, x]:
                continue
            y0, y1, x0, x1 = y * block, (y + 1) * block, x * block, (x + 1) * block
            r_val = rng.random()
            dx_norm = abs((x * block + block * 0.5) - cx_b) / hw_b
            if (dx_norm > 0.52 or (y * block) < y0b + 75 or (y * block) > y1b - 75) and r_val < 0.56:
                arr[y0:y1, x0:x1] = accent_rgb
            elif l_small[y, x] > 0.13 and ((x + y + frame_idx) % 2 == 0) and r_val < 0.72:
                arr[y0:y1, x0:x1] = (255, 255, 255)
            elif r_val < 0.15:
                arr[y0:y1, x0:x1] = (0, 0, 0)

    return draw_hud(Image.fromarray(arr, "RGB"), W, H, frame_idx, total_frames, brand, model, cam_tag, accent_rgb)


def render_cv_web(rgba_img, W, H, frame_idx):
    lum, mask = luminance(rgba_img), alpha_mask(rgba_img)
    x0, y0, x1, y1 = mask_bbox(mask, W, H)
    bw, bh = max(60, x1 - x0), max(60, y1 - y0)
    step = frame_idx % 4
    hi = (lum > [0.095, 0.080, 0.115, 0.088][step]) & mask
    edges = (mask ^ np.roll(mask, 3, axis=0)) | (mask ^ np.roll(mask, 3, axis=1))
    canvas = np.zeros((H, W, 3), dtype=np.uint8)
    canvas[hi | (edges & mask)] = (255, 255, 255)
    img = Image.fromarray(canvas, "RGB")
    d = ImageDraw.Draw(img)
    lw = 2 if W >= 1280 else 1

    jx, jy = [-10, 0, 12, -6][step], [-6, 5, -4, 8][step]
    rel_boxes = [
        (0.04, 0.00, 0.96, 0.24), (0.18, 0.12, 0.82, 0.36), (0.02, 0.28, 0.98, 0.58),
        (0.00, 0.48, 0.24, 0.74), (0.76, 0.48, 1.00, 0.74), (0.08, 0.64, 0.34, 0.94),
        (0.66, 0.64, 0.92, 0.94), (0.28, 0.70, 0.72, 0.95), (0.16, 0.84, 0.84, 1.00),
    ]
    top_n, bot_n = [], []
    for k, (rx0, ry0, rx1, ry1) in enumerate(rel_boxes):
        bx0 = int(x0 + rx0 * bw) + (jx if k % 2 == 0 else -jx)
        by0 = int(y0 + ry0 * bh) + (jy if k % 3 == 0 else 0)
        bx1 = int(x0 + rx1 * bw) + (jx if k % 2 == 0 else -jx)
        by1 = int(y0 + ry1 * bh) + (jy if k % 3 == 0 else 0)
        d.rectangle([bx0, by0, bx1, by1], outline=(255, 255, 255), width=lw)
        cx, cy = (bx0 + bx1) // 2, (by0 + by1) // 2
        (top_n if k < 3 else bot_n).append((cx, cy))
    for tn in top_n:
        for bn in bot_n:
            d.line([tn, bn], fill=(235, 235, 235), width=1)
    for k in range(len(bot_n) - 1):
        d.line([bot_n[k], bot_n[(k + 2 + step) % len(bot_n)]], fill=(250, 250, 250), width=lw)
    return img


def render_bw_nodes(rgba_img, W, H, frame_idx, step=0):
    lum, mask = luminance(rgba_img), alpha_mask(rgba_img)
    x0, y0, x1, y1 = mask_bbox(mask, W, H)
    bw, bh = max(60, x1 - x0), max(60, y1 - y0)
    yy = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None]
    sweep = (y0 + bh * (0.20 + (step % 5) * 0.16)) / H
    thresh = 0.15 - np.exp(-((yy - sweep) / 0.18) ** 2) * 0.08
    canvas = np.full((H, W, 3), 255, dtype=np.uint8)
    canvas[mask & (lum < thresh)] = (0, 0, 0)
    img = Image.fromarray(canvas, "RGB")
    d = ImageDraw.Draw(img)
    lw = 2 if W >= 1280 else 1

    ox = [-14, -6, 0, 8, 14][step % 5]
    rel_pts = [(0.22, 0.18), (0.14, 0.44), (0.86, 0.44), (0.50, 0.56), (0.12, 0.68), (0.88, 0.68), (0.36, 0.82), (0.52, 0.94)]
    centers = []
    for rx, ry in rel_pts:
        px, py = int(x0 + rx * bw) + ox, int(y0 + ry * bh)
        d.rectangle([px - 22, py - 11, px + 22, py + 11], outline=(255, 255, 255), width=lw)
        centers.append((px, py))
    links = [[(0, 1), (1, 2), (1, 3), (2, 3), (1, 4), (4, 6), (6, 7)],
             [(0, 2), (2, 5), (5, 3), (3, 1), (1, 4), (4, 7), (2, 6)],
             [(0, 1), (0, 2), (1, 3), (3, 5), (5, 7), (4, 6), (6, 7)]][step % 3]
    for a, b in links:
        d.line([centers[a], centers[b]], fill=(248, 248, 248), width=lw)
    return img


def render_bayer_wave(rgba_img, W, H, frame_idx, phase=0):
    arr = np.asarray(rgba_img, dtype=np.float32) / 255.0
    lum = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    mask = arr[..., 3] > 0.24
    base_blk = max(8, W // 115)
    block = [base_blk + 4, base_blk + 2, base_blk, base_blk + 2][phase % 4]
    bh, bw = H // block, W // block
    m_small = mask[:bh * block, :bw * block].reshape(bh, block, bw, block).mean(axis=(1, 3)) > 0.28
    l_small = lum[:bh * block, :bw * block].reshape(bh, block, bw, block).mean(axis=(1, 3))
    yy = np.linspace(0.0, 1.0, bh, dtype=np.float32)[:, None]
    l_norm = np.clip((l_small - 0.03) * 4.0 + 0.26 * np.sin(yy * math.pi * 2.0 - phase * 0.9), 0.0, 1.0)
    bayer = np.tile(np.roll(BAYER_4, phase, axis=0), (bh // 4 + 1, bw // 4 + 1))[:bh, :bw]
    is_white = l_norm > bayer
    rng = np.random.default_rng(3000 + frame_idx * 53)
    edge = (m_small ^ np.roll(m_small, 1, axis=1)) | (m_small ^ np.roll(m_small, -1, axis=1))
    m_final = m_small | ((rng.random((bh, bw)) < 0.24) & np.roll(edge, (phase % 3) - 1, axis=0))
    canvas = np.full((H, W, 3), 255, dtype=np.uint8)
    for y in range(bh):
        for x in range(bw):
            if m_final[y, x]:
                canvas[y * block:(y + 1) * block, x * block:(x + 1) * block] = (255, 255, 255) if is_white[y, x] else (0, 0, 0)
    return Image.fromarray(canvas, "RGB")


def main():
    args = parse_args()
    accent_rgb = tuple(int(v.strip()) for v in args.accent_rgb.split(","))
    W, H = (1920, 1080) if args.aspect == "16:9" else (720, 900)
    vertical_type = (args.aspect == "4:5")
    title_sz = 220 if args.aspect == "16:9" else 92

    files = sorted(glob.glob(os.path.join(args.renders, "frame_*.png")))
    assert files, f"No frame_*.png found in {args.renders}"
    total = len(files)

    comp_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "_comp_frames")
    os.makedirs(comp_dir, exist_ok=True)

    # Reference lit frame for early silhouette/intro frames
    hero_rgba = Image.open(files[min(total - 1, int(total * 0.85))]).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS)

    for i, fpath in enumerate(files):
        f = i + 1
        rgba = Image.open(fpath).convert("RGBA")
        if rgba.size != (W, H):
            rgba = rgba.resize((W, H), Image.Resampling.LANCZOS)
        mask = alpha_mask(rgba)
        t = i / max(1, total - 1)  # normalized timeline [0..1]

        # Determine angle label by normalized section
        sec_idx = min(6, int(t * 6) + 1)
        cam_tag = f"CAM-0{sec_idx} // ANGLE_{sec_idx:02d}"

        if f <= 2:
            out = render_accent_glitch(hero_rgba if args.mode == "topdown" else rgba, W, H, i, total, args.brand, args.model, cam_tag, accent_rgb)
        elif f == 3:
            out = pixelate_silhouette(mask, W, H, block=max(16, W // 80))
        elif f == 4:
            out = draw_kinetic_title(composite_on_white(rgba, 0.06), args.word1, W, H, title_sz, vertical=vertical_type, pixel_last=True)
        elif f == 5:
            out = composite_on_white(rgba, 0.05)
        elif f == 6:
            out = draw_kinetic_title(composite_on_white(rgba, 0.06), args.word1, W, H, title_sz, vertical=vertical_type)
        elif f <= 10:
            out = draw_kinetic_title(composite_on_white(rgba, 0.06), args.word2, W, H, int(title_sz * 1.1), vertical=vertical_type)
        elif f <= 14:
            out = render_cv_web(hero_rgba if args.mode == "topdown" else rgba, W, H, i)
        elif f >= total - 4:
            if f <= total - 2:
                out = draw_kinetic_title(render_bayer_wave(rgba, W, H, i, phase=2), "LOST DATA", W, H, int(title_sz * 0.82), vertical=vertical_type)
            elif f == total - 1:
                out = draw_kinetic_title(pixelate_silhouette(mask, W, H, block=max(14, W // 90)), "LOST DATA", W, H, int(title_sz * 0.82), vertical=vertical_type)
            else:
                out = composite_on_white(rgba, 0.04)
        else:
            # Periodic kinetic transitions & hero title reveals across the timeline
            beat = f % 36
            if 0.34 <= t <= 0.40:
                # Strobing model reveal
                sub_idx = int((t - 0.34) / 0.06 * (len(args.model) + 2))
                out = composite_on_white(rgba)
                if sub_idx not in (2, 4):
                    out = draw_kinetic_title(out, args.model[:max(2, min(len(args.model), sub_idx + 1))],
                                             W, H, title_sz, vertical=vertical_type, pixel_first_outline=True)
                out = draw_hud(out, W, H, i, total, args.brand, args.model, cam_tag, accent_rgb)
            elif 0.66 <= t <= 0.72:
                # Strobing brand reveal
                sub_idx = int((t - 0.66) / 0.06 * (len(args.brand) + 2))
                out = composite_on_white(rgba)
                if sub_idx not in (3, 5):
                    out = draw_kinetic_title(out, args.brand[:max(2, min(len(args.brand), sub_idx + 1))],
                                             W, H, int(title_sz * 0.92), vertical=vertical_type, pixel_first_outline=True)
                out = draw_hud(out, W, H, i, total, args.brand, args.model, cam_tag, accent_rgb)
            elif beat in (34, 35, 0) and t < 0.88:
                # Whip-cut transitions between angles (alternating Bayer dither / B&W node / CV web)
                kind = (f // 36) % 3
                if kind == 0:
                    out = render_bayer_wave(rgba, W, H, i, phase=beat)
                elif kind == 1:
                    out = render_bw_nodes(rgba, W, H, i, step=beat)
                else:
                    out = render_cv_web(rgba, W, H, i)
            else:
                out = draw_hud(composite_on_white(rgba), W, H, i, total, args.brand, args.model, cam_tag, accent_rgb)

        out.save(os.path.join(comp_dir, f"comp_{f:04d}.png"))

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-framerate", str(args.fps),
        "-i", os.path.join(comp_dir, "comp_%04d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-movflags", "+faststart",
        args.out,
    ], check=True)

    cs_path = os.path.splitext(args.out)[0] + "_contact_sheet.jpg"
    stride = max(1, total // 30)
    tile_w, tile_h = (320, 180) if args.aspect == "16:9" else (240, 300)
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", args.out,
        "-vf", f"select='not(mod(n,{stride}))',scale={tile_w}:{tile_h},tile=5x6",
        "-fps_mode", "vfr", "-frames:v", "1", cs_path,
    ], check=True)
    print(f"SHOWREEL_MP4_OK: {args.out} ({total} frames @ {args.fps}fps, {W}x{H}) | Sheet: {cs_path}")


if __name__ == "__main__":
    main()
