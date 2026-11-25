#!/usr/bin/env python3
"""
Portable Optical Flatbed Scanner / Specimen Plate Video Engine (1200 DPI CCD Slit-Scan).
Works on ANY input video clip + foreground mask video:
  - Ahead of scanner bar: moody darkroom-graded source video
  - Behind scanner bar: pure clinical off-white flatbed glass (#eff4ff) + procedural dust/fibers
    OR pure pitch-black (#020307) darkroom void with luminous temporal RGB CCD slit-scan!
  - Finale (SCAN 04): 3 isolated floating RGB specimens + crisp dot-matrix brand frame.

Supports 9x16 (1080x1920 centered 1080x608 cinema strip), 16x9 (1920x1080 full-bleed), or both.
"""
import argparse, json, math, os, subprocess, sys
import numpy as np

W, H = 1080, 608
FULL_W, FULL_H = 1080, 1920
Y_OFF = (FULL_H - H) // 2
FPS = 30
TOTAL_FRAMES = 435  # 14.50s @ 30fps


def probe_video(path: str):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "json", path,
    ])
    st = json.loads(out)["streams"][0]
    return int(st["width"]), int(st["height"])


def load_video_rgb(path, vf, ew=W, eh=H):
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.check_output(cmd)
    n = len(raw) // (ew * eh * 3)
    return np.frombuffer(raw, dtype=np.uint8).reshape((n, eh, ew, 3))


def load_video_gray(path, vf, ew=W, eh=H):
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-vf", vf, "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    raw = subprocess.check_output(cmd)
    n = len(raw) // (ew * eh)
    return np.frombuffer(raw, dtype=np.uint8).reshape((n, eh, ew))


# ── Crisp 5x7 Dot-Matrix & Technical HUD Font ───────────────────────────────
FONT_5X7 = {
    'A': ["01110","10001","10001","11111","10001","10001","10001"],
    'B': ["11110","10001","10001","11110","10001","10001","11110"],
    'C': ["01111","10000","10000","10000","10000","10000","01111"],
    'D': ["11110","10001","10001","10001","10001","10001","11110"],
    'E': ["11111","10000","10000","11110","10000","10000","11111"],
    'F': ["11111","10000","10000","11110","10000","10000","10000"],
    'G': ["01111","10000","10000","10111","10001","10001","01110"],
    'H': ["10001","10001","10001","11111","10001","10001","10001"],
    'I': ["01110","00100","00100","00100","00100","00100","01110"],
    'J': ["00111","00010","00010","00010","10010","10010","01100"],
    'K': ["10001","10010","10100","11000","10100","10010","10001"],
    'L': ["10000","10000","10000","10000","10000","10000","11111"],
    'M': ["10001","11011","10101","10101","10001","10001","10001"],
    'N': ["10001","11001","10101","10011","10001","10001","10001"],
    'O': ["01110","10001","10001","10001","10001","10001","01110"],
    'P': ["11110","10001","10001","11110","10000","10000","10000"],
    'Q': ["01110","10001","10001","10001","10101","10010","01101"],
    'R': ["11110","10001","10001","11110","10100","10010","10001"],
    'S': ["01111","10000","10000","01110","00001","00001","11110"],
    'T': ["11111","00100","00100","00100","00100","00100","00100"],
    'U': ["10001","10001","10001","10001","10001","10001","01110"],
    'V': ["10001","10001","10001","01010","01010","00100","00100"],
    'W': ["10001","10001","10001","10101","10101","11011","10001"],
    'X': ["10001","10001","01010","00100","01010","10001","10001"],
    'Y': ["10001","10001","01010","00100","00100","00100","00100"],
    'Z': ["11111","00001","00010","00100","01000","10000","11111"],
    '0': ["01110","10011","10101","10101","11001","10001","01110"],
    '1': ["00100","01100","00100","00100","00100","00100","01110"],
    '2': ["01110","10001","00001","00110","01000","10000","11111"],
    '3': ["11110","00001","00001","01110","00001","00001","11110"],
    '4': ["00010","00110","01010","10010","11111","00010","00010"],
    '5': ["11111","10000","11110","00001","00001","10001","01110"],
    '6': ["01110","10000","11110","10001","10001","10001","01110"],
    '7': ["11111","00001","00010","00100","01000","01000","01000"],
    '8': ["01110","10001","10001","01110","10001","10001","01110"],
    '9': ["01110","10001","10001","01111","00001","00001","01110"],
    '?': ["01110","10001","00001","00110","00100","00000","00100"],
    '%': ["11001","11010","00100","00100","01011","10011","00000"],
    '.': ["00000","00000","00000","00000","00000","01100","01100"],
    'x': ["00000","00000","10001","01010","00100","01010","10001"],
    '_': ["00000","00000","00000","00000","00000","00000","11111"],
    '-': ["00000","00000","00000","11111","00000","00000","00000"],
    '+': ["00000","00100","00100","11111","00100","00100","00000"],
    ' ': ["00000","00000","00000","00000","00000","00000","00000"],
}


def draw_text(img, text, x, y, color, scale=2, dot_matrix=False):
    ih, iw = img.shape[:2]
    cx = int(x)
    for ch in text:
        glyph = FONT_5X7.get(ch.upper() if ch != 'x' else 'x', FONT_5X7[' '])
        for ry, row in enumerate(glyph):
            for rx, bit in enumerate(row):
                if bit == '1':
                    px = cx + rx * scale
                    py = int(y) + ry * scale
                    w_d = max(1, scale - 1) if (dot_matrix and scale >= 4) else scale
                    if 0 <= py and py + w_d <= ih and 0 <= px and px + w_d <= iw:
                        img[py:py + w_d, px:px + w_d] = color
        cx += 6 * scale + (scale if dot_matrix else 0)


def draw_dashed_box(img, x0, y0, x1, y1, color, label1="", label2="", dash=6, gap=4):
    ih, iw = img.shape[:2]
    x0, y0 = max(2, int(x0)), max(2, int(y0))
    x1, y1 = min(iw - 3, int(x1)), min(ih - 3, int(y1))
    for x in range(x0, x1, dash + gap):
        xe = min(x1, x + dash)
        img[y0:y0 + 2, x:xe] = color
        img[y1 - 1:y1 + 1, x:xe] = color
    for y in range(y0, y1, dash + gap):
        ye = min(ih, min(y1, y + dash))
        img[y:ye, x0:x0 + 2] = color
        img[y:ye, x1 - 1:x1 + 1] = color
    for cx, cy in [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]:
        img[max(0, cy - 2):min(ih, cy + 3), max(0, cx - 2):min(iw, cx + 3)] = color
    if label1:
        ly = y1 + 8 if y1 + 36 < ih else max(8, y0 - 34)
        if np.mean(color) > 0.5:
            bw = min(iw - x0, len(label1) * 12 + 10)
            img[max(0, ly - 3):min(ih, ly + 28), max(0, x0):min(iw, x0 + bw)] *= 0.25
        draw_text(img, label1, x0 + 2, ly, color, scale=2)
    if label2:
        ly2 = (y1 + 26) if y1 + 36 < ih else max(24, y0 - 16)
        dim = color * 0.72 if np.mean(color) > 0.5 else color * 0.65 + 0.25
        draw_text(img, label2, x0 + 2, ly2, dim, scale=1)


def build_dust_layer():
    rng = np.random.default_rng(777)
    dust = np.zeros((H, W), dtype=np.float32)
    for _ in range(130):
        px = int(rng.integers(10, W - 10))
        py = int(rng.integers(10, H - 10))
        r = int(rng.integers(1, 3))
        dust[py:py + r, px:px + r] = rng.uniform(0.18, 0.38)
    for _ in range(14):
        sx = float(rng.integers(40, W - 40))
        sy = float(rng.integers(30, H - 30))
        ang = rng.uniform(0, 2 * math.pi)
        curv = rng.uniform(-0.045, 0.045)
        steps = int(rng.integers(22, 58))
        for _ in range(steps):
            ang += curv + rng.uniform(-0.07, 0.07)
            sx += math.cos(ang) * 1.1
            sy += math.sin(ang) * 1.1
            ix, iy = int(sx), int(sy)
            if 1 <= ix < W - 1 and 1 <= iy < H - 1:
                dust[iy, ix] = max(dust[iy, ix], 0.32)
    return dust[..., None]


DUST_LAYER = build_dust_layer()
PAPER_WHITE = np.array([0.935, 0.958, 1.000], dtype=np.float32)
DARK_VOID   = np.array([0.008, 0.010, 0.022], dtype=np.float32)
DARK_INK    = np.array([0.08, 0.10, 0.22], dtype=np.float32)
LIGHT_INK   = np.array([0.95, 0.97, 1.00], dtype=np.float32)


def sample_rgb(clip, idx):
    return clip[int(np.clip(idx, 0, len(clip) - 1))].astype(np.float32) / 255.0


def sample_msk(mclip, idx):
    m = mclip[int(np.clip(idx, 0, len(mclip) - 1))].astype(np.float32) / 255.0
    return np.clip((m - 0.12) * 1.35, 0.0, 1.0)


def dark_live_grade(frame):
    f = np.power(np.clip(frame, 0.0, 1.0), 1.45)
    f[..., 0] *= 0.80
    f[..., 1] *= 0.74
    f[..., 2] *= 0.94
    return np.clip((f - 0.03) * 1.10, 0.0, 1.0)


def shift_zero(arr, dy=0, dx=0, fill=0.0):
    out = np.full_like(arr, fill)
    h, w = arr.shape[0], arr.shape[1]
    sy0 = max(0, -dy); sy1 = min(h, h - dy)
    dy0 = max(0,  dy); dy1 = min(h, h + dy)
    sx0 = max(0, -dx); sx1 = min(w, w - dx)
    dx0 = max(0,  dx); dx1 = min(w, w + dx)
    if sy1 > sy0 and sx1 > sx0:
        out[dy0:dy1, dx0:dx1] = arr[sy0:sy1, sx0:sx1]
    return out


def isolated_light_plate(rgb_clip, msk_clip, idx, axis="x", spread=9, band_px=16, add_dust=True):
    ih, iw = rgb_clip.shape[1], rgb_clip.shape[2]
    r_rgb = sample_rgb(rgb_clip, idx - spread)
    g_rgb = sample_rgb(rgb_clip, idx)
    b_rgb = sample_rgb(rgb_clip, idx + spread)

    r_m = sample_msk(msk_clip, idx - spread)
    g_m = sample_msk(msk_clip, idx)
    b_m = sample_msk(msk_clip, idx + spread)

    sh = 13
    if axis == "x":
        r_rgb = shift_zero(r_rgb, 0, -sh); r_m = shift_zero(r_m, 0, -sh)
        b_rgb = shift_zero(b_rgb, 0,  sh); b_m = shift_zero(b_m, 0,  sh)
    else:
        r_rgb = shift_zero(r_rgb, -sh, 0); r_m = shift_zero(r_m, -sh, 0)
        b_rgb = shift_zero(b_rgb,  sh, 0); b_m = shift_zero(b_m,  sh, 0)

    paper = np.broadcast_to(PAPER_WHITE, (ih, iw, 3)).copy()

    def to_ink(rgb):
        luma = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
        out = np.empty_like(rgb)
        out[..., 0] = np.clip(rgb[..., 0] * 0.92 + (1.0 - luma) * 0.12, 0.0, 1.0)
        out[..., 1] = np.clip(rgb[..., 1] * 0.72 + rgb[..., 2] * 0.18, 0.0, 1.0)
        out[..., 2] = np.clip(rgb[..., 2] * 1.18 + (1.0 - rgb[..., 0]) * 0.35, 0.0, 1.0)
        return np.power(out, 1.18)

    comp = np.empty((ih, iw, 3), dtype=np.float32)
    comp[..., 0] = paper[..., 0] * (1.0 - r_m) + to_ink(r_rgb)[..., 0] * r_m
    comp[..., 1] = paper[..., 1] * (1.0 - g_m) + to_ink(g_rgb)[..., 1] * g_m
    comp[..., 2] = paper[..., 2] * (1.0 - b_m) + to_ink(b_rgb)[..., 2] * b_m

    union_m = np.maximum(np.maximum(r_m, g_m), b_m)[..., None]
    if axis == "x":
        smear = (shift_zero(comp, -18, 0, 0.95) + shift_zero(comp, -9, 0, 0.95) + comp + shift_zero(comp, 9, 0, 0.95) + shift_zero(comp, 18, 0, 0.95)) * 0.2
        cols = np.arange(iw) // band_px
        band_w = (0.16 + 0.32 * (0.5 + 0.5 * np.sin(cols * 2.3)))[None, :, None]
        comp = comp * (1.0 - union_m * band_w) + smear * (union_m * band_w)
    else:
        smear = (shift_zero(comp, 0, -20, 0.95) + shift_zero(comp, 0, -10, 0.95) + comp + shift_zero(comp, 0, 10, 0.95) + shift_zero(comp, 0, 20, 0.95)) * 0.2
        rows = np.arange(ih) // band_px
        band_w = (0.16 + 0.32 * (0.5 + 0.5 * np.sin(rows * 2.3)))[:, None, None]
        comp = comp * (1.0 - union_m * band_w) + smear * (union_m * band_w)

    if add_dust and ih == H and iw == W:
        comp = np.clip(comp - DUST_LAYER * 0.60, 0.0, 1.0)
    return np.clip(comp, 0.0, 1.0)


def isolated_dark_rgb_plate(rgb_clip, msk_clip, idx, axis="y", spread=10, band_px=12):
    ih, iw = rgb_clip.shape[1], rgb_clip.shape[2]
    r_rgb = sample_rgb(rgb_clip, idx - spread)
    g_rgb = sample_rgb(rgb_clip, idx)
    b_rgb = sample_rgb(rgb_clip, idx + spread)

    r_m = sample_msk(msk_clip, idx - spread)
    g_m = sample_msk(msk_clip, idx)
    b_m = sample_msk(msk_clip, idx + spread)

    sh = 14
    if axis == "x":
        r_rgb = shift_zero(r_rgb, 0, -sh); r_m = shift_zero(r_m, 0, -sh)
        b_rgb = shift_zero(b_rgb, 0,  sh); b_m = shift_zero(b_m, 0,  sh)
    else:
        r_rgb = shift_zero(r_rgb, -sh, 0); r_m = shift_zero(r_m, -sh, 0)
        b_rgb = shift_zero(b_rgb,  sh, 0); b_m = shift_zero(b_m,  sh, 0)

    def chan_energy(rgb, msk):
        l = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]) * msk
        gx = np.abs(l - shift_zero(l, 0, 2))
        gy = np.abs(l - shift_zero(l, 2, 0))
        edge = np.clip((gx + gy) * 4.8, 0.0, 1.0)
        return np.clip(np.power(l, 1.65) * 0.56 + edge * 0.74, 0.0, 1.0)

    er = chan_energy(r_rgb, r_m)
    eg = chan_energy(g_rgb, g_m)
    eb = chan_energy(b_rgb, b_m)

    out = np.empty((ih, iw, 3), dtype=np.float32)
    out[..., 0] = np.clip(er * 0.96, 0.0, 1.0)
    out[..., 1] = np.clip(eg * 0.98 + eb * 0.14, 0.0, 1.0)
    out[..., 2] = np.clip(eb * 1.18 + eg * 0.22, 0.0, 1.0)

    if axis == "x":
        smear = (shift_zero(out, -18, 0) + shift_zero(out, -9, 0) + out + shift_zero(out, 9, 0) + shift_zero(out, 18, 0)) * 0.2
        cols = np.arange(iw) // band_px
        bw = (0.18 + 0.34 * (0.5 + 0.5 * np.sin(cols * 2.1)))[None, :, None]
        out = out * (1.0 - bw) + smear * bw
    else:
        smear = (shift_zero(out, 0, -22) + shift_zero(out, 0, -11) + out + shift_zero(out, 0, 11) + shift_zero(out, 0, 22)) * 0.2
        rows = np.arange(ih) // band_px
        bw = (0.18 + 0.34 * (0.5 + 0.5 * np.sin(rows * 2.1)))[:, None, None]
        out = out * (1.0 - bw) + smear * bw

    return np.maximum(DARK_VOID, np.clip(out, 0.0, 1.0))


def apply_scanner_bar(base_img, scanned_img, pos_norm, axis="x", style="white", scan_label="SCAN 01"):
    pct = int(np.clip(pos_norm * 100, 0, 99))
    if axis == "x":
        bar_x = int(pos_norm * W)
        x_c = np.arange(W, dtype=np.float32)[None, :, None]
        mask = np.clip((bar_x - x_c + 4.0) / 8.0, 0.0, 1.0)
        out = base_img * (1.0 - mask) + scanned_img * mask
        dist = x_c - bar_x
        if style == "white":
            glow_w = np.exp(-((dist / 18.0) ** 2)) * 1.15
            glow_c = np.exp(-(((dist + 12.0) / 24.0) ** 2)) * 0.25
            out = np.clip(out + glow_w + glow_c * np.array([0.75, 0.88, 1.0], dtype=np.float32), 0.0, 1.0)
            lx = min(W - 148, max(16, bar_x + 16))
            draw_text(out, f"{scan_label}  {pct:02d}%", lx, 22, LIGHT_INK * 0.85, scale=2)
        else:
            blue_b  = np.exp(-(((dist + 26.0) / 9.0) ** 2))
            cyan_b  = np.exp(-(((dist + 10.0) / 8.0) ** 2))
            white_b = np.exp(-(((dist - 6.0)  / 14.0) ** 2))
            out = np.clip(
                out
                + blue_b  * np.array([0.04, 0.14, 1.40], dtype=np.float32)
                + cyan_b  * np.array([0.04, 1.20, 1.30], dtype=np.float32)
                + white_b * np.array([1.15, 1.18, 1.25], dtype=np.float32),
                0.0, 1.0,
            )
            lx = (bar_x - 180) if bar_x > W - 190 else max(16, bar_x + 26)
            draw_text(out, f"{scan_label}  {pct:02d}%", lx, 22, LIGHT_INK, scale=2)
    else:
        bar_y = int(pos_norm * H)
        y_c = np.arange(H, dtype=np.float32)[:, None, None]
        mask = np.clip((bar_y - y_c + 4.0) / 8.0, 0.0, 1.0)
        out = base_img * (1.0 - mask) + scanned_img * mask
        dist = y_c - bar_y
        blue_b  = np.exp(-(((dist + 22.0) / 8.0) ** 2))
        cyan_b  = np.exp(-(((dist + 7.0)  / 8.0) ** 2))
        white_b = np.exp(-(((dist - 10.0) / 15.0) ** 2))
        out = np.clip(
            out
            + blue_b  * np.array([0.04, 0.12, 1.40], dtype=np.float32)
            + cyan_b  * np.array([0.04, 1.20, 1.30], dtype=np.float32)
            + white_b * np.array([1.15, 1.18, 1.25], dtype=np.float32),
            0.0, 1.0,
        )
        ly = min(H - 36, max(14, bar_y + 26))
        draw_text(out, f"{scan_label}   {pct:02d}%", 34, ly, LIGHT_INK * 0.92, scale=2)
    return out


def add_plate_hud(img, plate_title, sub_line, right_status, dark_bg=False):
    col = LIGHT_INK if dark_bg else DARK_INK
    sub_col = col * 0.78 if dark_bg else col * 0.75 + 0.10
    draw_text(img, plate_title, 28, 24, col, scale=5, dot_matrix=True)
    draw_text(img, sub_line,    30, 72, sub_col, scale=2)
    rx = W - (len(right_status) * 12) - 28
    draw_text(img, right_status, max(20, rx), H - 28, col * 0.88, scale=2)


def make_16x9_crop_vf(iw: int, ih: int, y_frac: float) -> str:
    """Compute a safe 16:9 crop filter for any input aspect ratio (portrait, square, or landscape)."""
    target_ar = W / H
    if (iw / ih) < target_ar:
        cw = iw
        ch = max(2, int(round(iw / target_ar)) // 2 * 2)
        cx = 0
        cy = int(np.clip(round(ih * y_frac), 0, max(0, ih - ch)))
    else:
        ch = ih
        cw = max(2, int(round(ih * target_ar)) // 2 * 2)
        cx = max(0, (iw - cw) // 2)
        cy = 0
    return f"crop={cw}:{ch}:{cx}:{cy},scale={W}:{H}:flags=lanczos"


def make_fit_vf(iw: int, ih: int, tw: int, th: int) -> str:
    return f"scale={tw}:{th}:force_original_aspect_ratio=decrease:flags=lanczos,pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2:color=black"


def make_box_crop_vf(iw: int, ih: int, x0f, y0f, wf, hf, tw, th) -> str:
    cw = max(2, int(round(iw * wf)) // 2 * 2)
    ch = max(2, int(round(ih * hf)) // 2 * 2)
    cx = int(np.clip(round(iw * x0f), 0, max(0, iw - cw)))
    cy = int(np.clip(round(ih * y0f), 0, max(0, ih - ch)))
    return f"crop={cw}:{ch}:{cx}:{cy},scale={tw}:{th}:flags=lanczos"


def idx_at(n_frames: int, t0: float, t1: float, u: float) -> int:
    """Map normalized progress u in [0,1] into clip frame range [t0, t1] safely for any clip length."""
    f0 = int(t0 * max(1, n_frames - 1))
    f1 = int(t1 * max(1, n_frames - 1))
    return int(np.clip(f0 + u * (f1 - f0), 0, max(0, n_frames - 1)))


def main():
    ap = argparse.ArgumentParser(description="Render 14.5s 1200 DPI flatbed scanner slit-scan film")
    ap.add_argument("--input", required=True)
    ap.add_argument("--mask", required=True)
    ap.add_argument("--pan", default="")
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--aspect", choices=["9x16", "16x9", "both"], default="9x16")
    ap.add_argument("--brand", default="MOTION VIZ")
    ap.add_argument("--subtitle", default="1200 DPI SCAN")
    ap.add_argument("--obj1", default="SUBJECT")
    ap.add_argument("--obj2", default="UPPER")
    ap.add_argument("--obj3", default="DETAIL")
    ap.add_argument("--upper-y", type=float, default=0.05)
    ap.add_argument("--detail-y", type=float, default=0.30)
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()

    pan_path = args.pan if args.pan and os.path.exists(args.pan) else args.input
    iw, ih = probe_video(args.input)
    pw, ph = probe_video(pan_path)
    print(f"[Load] Input {iw}x{ih}, Pan {pw}x{ph} -> decoding clips & masks...", flush=True)

    vf_upper  = make_16x9_crop_vf(iw, ih, args.upper_y)
    vf_detail = make_16x9_crop_vf(iw, ih, args.detail_y)
    vf_full   = make_fit_vf(iw, ih, W, H)
    vf_pan    = make_16x9_crop_vf(pw, ph, 0.22)

    subj_upper  = load_video_rgb(args.input, vf_upper)
    mask_upper  = load_video_gray(args.mask, vf_upper)
    subj_detail = load_video_rgb(args.input, vf_detail)
    mask_detail = load_video_gray(args.mask, vf_detail)
    subj_full   = load_video_rgb(args.input, vf_full)
    mask_full   = load_video_gray(args.mask, vf_full)
    pan_wide    = load_video_rgb(pan_path,   vf_pan)

    vf_sh = make_box_crop_vf(iw, ih, 0.12, 0.06, 0.65, 0.42, 370, 300)
    vf_sd = make_box_crop_vf(iw, ih, 0.16, 0.32, 0.68, 0.38, 370, 258)
    vf_sf = make_fit_vf(iw, ih, 412, 550)

    spec_head_rgb = load_video_rgb(args.input, vf_sh, 370, 300)
    spec_head_msk = load_video_gray(args.mask, vf_sh, 370, 300)
    spec_det_rgb  = load_video_rgb(args.input, vf_sd, 370, 258)
    spec_det_msk  = load_video_gray(args.mask, vf_sd, 370, 258)
    spec_full_rgb = load_video_rgb(args.input, vf_sf, 412, 550)
    spec_full_msk = load_video_gray(args.mask, vf_sf, 412, 550)

    nf = len(subj_full)
    npf = len(pan_wide)
    o1, o2, o3 = args.obj1.upper()[:12], args.obj2.upper()[:12], args.obj3.upper()[:12]
    brand_words = args.brand.upper().split()
    b_line1 = brand_words[0][:9] if brand_words else "SCAN"
    b_line2 = " ".join(brand_words[1:])[:9] if len(brand_words) > 1 else ""
    sub_cap = args.subtitle.upper()[:18]
    print(f"[Load] Ready ({nf} subject frames, {npf} pan frames).", flush=True)

    def render_frame(f):
        if f < 24:
            u = f / 23.0
            img = dark_live_grade(sample_rgb(pan_wide, idx_at(npf, 0.0, 0.25, u)))
            if u > 0.25:
                bar_w = int((u - 0.25) / 0.75 * 44)
                x_c = np.arange(W, dtype=np.float32)[None, :, None]
                glow = np.exp(-((np.maximum(0.0, x_c - bar_w) / 14.0) ** 2))
                img = np.clip(img + glow * 0.98, 0.0, 1.0)
            draw_text(img, "SCANNER READY", 22, H - 24, LIGHT_INK * 0.55, scale=1)
            return img

        elif f < 84:
            u = (f - 24) / 59.0
            idx = idx_at(nf, 0.24, 0.52, u)
            live = dark_live_grade(sample_rgb(subj_upper, idx))
            plate = isolated_light_plate(subj_upper, mask_upper, idx, axis="x", spread=10, band_px=14)
            img = apply_scanner_bar(live, plate, u, axis="x", style="white", scan_label="SCAN 01")
            if u > 0.40:
                conf = 68 + int(11 * math.sin(f * 0.42))
                draw_dashed_box(img, 240, 72, 700, 545, DARK_INK, f"OBJ 01   {o2}?   {conf}%", "48.2 x 42.1 MM")
            return img

        elif f < 120:
            sub = f - 84
            if sub < 12:
                idx = idx_at(nf, 0.40, 0.46, sub / 11.0)
                img = isolated_light_plate(subj_full, mask_full, idx, axis="x", spread=10, band_px=14)
                add_plate_hud(img, "PLATE 01", "RGB   1200 DPI   x 1.4", "1 OBJECTS    NONE HELD STILL", dark_bg=False)
                draw_dashed_box(img, 365, 36, 705, 560, DARK_INK, f"OBJ 01   {o1}   79%", "165.0 x 54.3 MM")
            elif sub < 24:
                idx = idx_at(nf, 0.42, 0.49, (sub - 12) / 11.0)
                img = isolated_light_plate(subj_upper, mask_upper, idx, axis="x", spread=11, band_px=12)
                add_plate_hud(img, "PLATE 01", "RGB   1200 DPI   x 2.3", "1 OBJECTS    NONE HELD STILL", dark_bg=False)
                draw_dashed_box(img, 248, 56, 708, 542, DARK_INK, f"OBJ 01   {o2}   47%", "48.2 x 42.1 MM")
            else:
                idx = idx_at(nf, 0.60, 0.66, (sub - 24) / 11.0)
                img = isolated_light_plate(subj_detail, mask_detail, idx, axis="x", spread=11, band_px=12)
                add_plate_hud(img, "PLATE 01", "RGB   1200 DPI   x 2.8", "3 OBJECTS    NONE HELD STILL", dark_bg=False)
                draw_dashed_box(img, 285, 72, 785, 535, DARK_INK, f"OBJ 01   {o3}   64%", "32.4 x 28.9 MM")
            return img

        elif f < 168:
            u = (f - 120) / 47.0
            img = dark_live_grade(sample_rgb(pan_wide, idx_at(npf, 0.18, 0.94, u)))
            img[..., 2] = np.clip(img[..., 2] * 1.22 + 0.03, 0.0, 1.0)
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            beam_pos = (u * 1.5 - 0.25) * W
            diag_d = (xx - 0.55 * yy) - beam_pos
            beam = np.exp(-((diag_d / 26.0) ** 2))
            img = np.clip(img + beam[..., None] * np.array([0.85, 0.90, 1.15], dtype=np.float32) * 0.95, 0.0, 1.0)
            return img

        elif f < 228:
            u = (f - 168) / 59.0
            idx = idx_at(nf, 0.27, 0.62, u)
            live = dark_live_grade(sample_rgb(subj_full, idx))
            dark_rgb = isolated_dark_rgb_plate(subj_full, mask_full, idx, axis="y", spread=11, band_px=12)
            img = apply_scanner_bar(live, dark_rgb, u, axis="y", style="blue_cyan", scan_label="SCAN 02")
            if u > 0.34:
                draw_dashed_box(img, 380, 32, 650, 278, LIGHT_INK, f"OBJ 01   {o2}?   {64 + (f % 9)}%", "48.2 x 42.1 MM")
            if u > 0.64:
                draw_dashed_box(img, 365, 290, 695, 535, LIGHT_INK, f"OBJ 02   {o3}?   {71 + (f % 7)}%", "32.4 x 28.9 MM")
            return img

        elif f < 276:
            sub = f - 228
            idx = idx_at(nf, 0.36, 0.62, sub / 47.0)
            if sub < 18:
                img = isolated_dark_rgb_plate(subj_detail, mask_detail, idx, axis="y", spread=12, band_px=12)
                add_plate_hud(img, "PLATE 02", "RGB   1200 DPI   x 2.8", "3 OBJECTS    NONE HELD STILL", dark_bg=True)
                draw_dashed_box(img, 240, 64, 830, 536, LIGHT_INK, f"OBJ 01   {o3}   40%", "32.4 x 28.9 MM")
            elif sub < 30:
                img = isolated_light_plate(subj_detail, mask_detail, idx, axis="y", spread=12, band_px=12)
                add_plate_hud(img, "PLATE 02", "NEGATIVE   1200 DPI   x 2.8", "3 OBJECTS    NONE HELD STILL", dark_bg=False)
                draw_dashed_box(img, 240, 64, 830, 536, DARK_INK, f"OBJ 01   {o3}   88%", "32.4 x 28.9 MM")
            else:
                img = isolated_dark_rgb_plate(subj_upper, mask_upper, idx, axis="x", spread=11, band_px=12)
                add_plate_hud(img, "PLATE 02", "NEGATIVE   1200 DPI   x 2.1", "1 OBJECTS    NONE HELD STILL", dark_bg=True)
                draw_dashed_box(img, 248, 62, 705, 535, LIGHT_INK, f"OBJ 01   {o1}   66%", "48.2 x 42.1 MM")
            return img

        elif f < 318:
            u = (f - 276) / 41.0
            img = dark_live_grade(sample_rgb(subj_upper, idx_at(nf, 0.0, 0.28, u)))
            img[..., 2] = np.clip(img[..., 2] * 1.15, 0.0, 1.0)
            if 0.34 <= u <= 0.64:
                fu = (u - 0.34) / 0.30
                bx = int((1.0 - fu) * W)
                x_c = np.arange(W, dtype=np.float32)[None, :, None]
                bar = np.exp(-(((x_c - bx) / 52.0) ** 2))
                img = np.clip(img + bar * 1.15, 0.0, 1.0)
            return img

        elif f < 366:
            u = (f - 318) / 47.0
            idx = idx_at(nf, 0.58, 0.92, u)
            live = dark_live_grade(sample_rgb(subj_detail, idx))
            plate = isolated_light_plate(subj_detail, mask_detail, idx, axis="x", spread=11, band_px=12)
            img = apply_scanner_bar(live, plate, u, axis="x", style="white", scan_label="SCAN 03")
            if u > 0.66:
                add_plate_hud(img, "PLATE 03", "RGB   1200 DPI   x 3.1", "3 OBJECTS    NONE HELD STILL", dark_bg=False)
                draw_dashed_box(img, 265, 74, 795, 528, DARK_INK, f"OBJ 03   {o3}   77%", "38.2 x 22.1 MM")
            return img

        elif f < 393:
            sub = f - 366
            if sub < 7:
                img = isolated_dark_rgb_plate(subj_full, mask_full, idx_at(nf, 0.37, 0.42, sub / 6.0), axis="x", spread=11, band_px=12)
                add_plate_hud(img, "PLATE 01", "NEGATIVE   1200 DPI   x 1.3", "1 OBJECTS    NONE HELD STILL", dark_bg=True)
                draw_dashed_box(img, 365, 36, 705, 560, LIGHT_INK, f"OBJ 01   {o1}   66%", "165.0 x 54.3 MM")
            elif sub < 14:
                img = isolated_light_plate(subj_upper, mask_upper, idx_at(nf, 0.42, 0.48, (sub - 7) / 6.0), axis="x", spread=11, band_px=12)
                add_plate_hud(img, "PLATE 02", "RGB   1200 DPI   x 2.4", "1 OBJECTS    NONE HELD STILL", dark_bg=False)
                draw_dashed_box(img, 248, 56, 708, 542, DARK_INK, f"OBJ 01   {o2}   84%", "48.2 x 42.1 MM")
            elif sub < 21:
                img = isolated_dark_rgb_plate(subj_detail, mask_detail, idx_at(nf, 0.66, 0.72, (sub - 14) / 6.0), axis="y", spread=12, band_px=12)
                add_plate_hud(img, "PLATE 03", "NEGATIVE   1200 DPI   x 2.8", "3 OBJECTS    NONE HELD STILL", dark_bg=True)
                draw_dashed_box(img, 240, 64, 830, 536, LIGHT_INK, f"OBJ 03   {o3}   72%", "32.4 x 28.9 MM")
            else:
                img = isolated_light_plate(subj_full, mask_full, idx_at(nf, 0.78, 0.84, (sub - 21) / 5.0), axis="x", spread=10, band_px=14)
                add_plate_hud(img, "PLATE 01", "RGB   1200 DPI   x 1.4", "1 OBJECTS    NONE HELD STILL", dark_bg=False)
                draw_dashed_box(img, 365, 36, 705, 560, DARK_INK, f"OBJ 01   {o1}   91%", "165.0 x 54.3 MM")
            return img

        else:
            u = min(1.0, (f - 393) / 31.0)
            idx = idx_at(nf, 0.35, 0.60, u)
            idx2 = idx_at(nf, 0.58, 0.85, u)
            live = np.broadcast_to(DARK_VOID, (H, W, 3)).copy()
            live_full = dark_live_grade(sample_rgb(spec_full_rgb, idx)) * sample_msk(spec_full_msk, idx)[..., None]
            live[24:574, 420:832] = np.maximum(live[24:574, 420:832], live_full)
            live_head = dark_live_grade(sample_rgb(spec_head_rgb, idx)) * sample_msk(spec_head_msk, idx)[..., None]
            live[18:318, 28:398] = np.maximum(live[18:318, 28:398], live_head)
            live_ch = dark_live_grade(sample_rgb(spec_det_rgb, idx2)) * sample_msk(spec_det_msk, idx2)[..., None]
            live[330:588, 28:398] = np.maximum(live[330:588, 28:398], live_ch)

            scanned = np.broadcast_to(DARK_VOID, (H, W, 3)).copy()
            scanned[18:318,  28:398]  = np.maximum(scanned[18:318,  28:398],  isolated_dark_rgb_plate(spec_head_rgb, spec_head_msk, idx,  axis="x", spread=10, band_px=10))
            scanned[330:588, 28:398]  = np.maximum(scanned[330:588, 28:398],  isolated_dark_rgb_plate(spec_det_rgb,  spec_det_msk,  idx2, axis="y", spread=11, band_px=10))
            scanned[24:574,  420:832] = np.maximum(scanned[24:574,  420:832], isolated_dark_rgb_plate(spec_full_rgb, spec_full_msk, idx,  axis="x", spread=10, band_px=12))

            img = apply_scanner_bar(live, scanned, min(0.95, u * 0.95), axis="x", style="blue_cyan", scan_label="SCAN 04")
            if u > 0.34:
                draw_dashed_box(img, 24,  14, 392, 278, LIGHT_INK, f"OBJ 01   {o2}?   88%", "48.2 x 42.1 MM")
                draw_dashed_box(img, 24, 326, 392, 558, LIGHT_INK, f"OBJ 02   {o3}?   76%", "32.4 x 28.9 MM")
            if u > 0.65:
                draw_dashed_box(img, 438, 20, 772, 558, LIGHT_INK, f"OBJ 03   {o1}   91%", "165.0 x 54.3 MM")
            if u > 0.80:
                draw_dashed_box(img, 796, 210, 1020, 382, LIGHT_INK, sub_cap, "1200 DPI   3 OBJECTS")
                draw_text(img, b_line1, 822, 250 if b_line2 else 278, LIGHT_INK, scale=4, dot_matrix=True)
                if b_line2:
                    draw_text(img, b_line2, 848, 304, LIGHT_INK, scale=4, dot_matrix=True)
            return img

    os.makedirs(args.out_dir, exist_ok=True)
    if args.test:
        test_fs = [60, 102, 200, 240, 370, 426]
        tdir = os.path.join(args.out_dir, "_test_frames")
        os.makedirs(tdir, exist_ok=True)
        for tf in test_fs:
            strip = np.clip(render_frame(tf) * 255.0, 0, 255).astype(np.uint8)
            out_p = os.path.join(tdir, f"test_{tf:04d}.png")
            p = subprocess.Popen(
                ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-i", "-", out_p],
                stdin=subprocess.PIPE,
            )
            p.communicate(strip.tobytes())
        sheet = os.path.join(args.out_dir, "test_sheet.jpg")
        subprocess.check_call([
            "ffmpeg", "-y", "-v", "error", "-pattern_type", "glob", "-i", os.path.join(tdir, "test_*.png"),
            "-vf", "scale=540:304,tile=3x2:padding=6:color=#111111", sheet,
        ])
        print(f"[Test] Wrote contact sheet -> {sheet}")
        return

    out_9x16 = os.path.join(args.out_dir, "scanner_plate_14s_9x16.mp4")
    out_16x9 = os.path.join(args.out_dir, "scanner_plate_14s_16x9.mp4")

    # Render clean 1080x608 master strip or pipe directly into requested output(s)
    vf_9x16 = f"pad={FULL_W}:{FULL_H}:0:{Y_OFF}:color=black,setsar=1"
    vf_16x9 = "scale=1920:1080:flags=lanczos,setsar=1"

    primary_out = out_16x9 if args.aspect == "16x9" else out_9x16
    primary_vf = vf_16x9 if args.aspect == "16x9" else vf_9x16

    print(f"[Render] Streaming {TOTAL_FRAMES} frames ({W}x{H} @ {FPS}fps) -> {primary_out}...", flush=True)
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", args.audio,
        "-vf", primary_vf,
        "-map", "0:v:0", "-map", "1:a:0", "-shortest",
        "-c:v", "libx264", "-profile:v", "high", "-level", "4.1", "-crf", "15",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "192k",
        primary_out,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(TOTAL_FRAMES):
        strip = np.clip(render_frame(f) * 255.0, 0, 255).astype(np.uint8)
        proc.stdin.write(strip.tobytes())
        if (f + 1) % 60 == 0 or f == TOTAL_FRAMES - 1:
            print(f"[Render] Frame {f + 1}/{TOTAL_FRAMES}", flush=True)
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("FFmpeg render failed")

    if args.aspect == "both":
        print(f"[Render] Deriving true 16:9 1920x1080 -> {out_16x9}...", flush=True)
        subprocess.check_call([
            "ffmpeg", "-y", "-v", "error", "-i", out_9x16,
            "-vf", f"crop={W}:{H}:0:{Y_OFF},scale=1920:1080:flags=lanczos,setsar=1",
            "-c:v", "libx264", "-profile:v", "high", "-level", "4.1", "-crf", "15",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-c:a", "copy", out_16x9,
        ])

    sheet = os.path.join(args.out_dir, "final_review_sheet_14s.jpg")
    scale_expr = "scale=540:304" if args.aspect == "16x9" else "scale=360:640"
    subprocess.check_call([
        "ffmpeg", "-y", "-v", "error", "-i", primary_out,
        "-vf", f"select='eq(n,60)+eq(n,102)+eq(n,200)+eq(n,240)+eq(n,370)+eq(n,426)',{scale_expr},tile=3x2:padding=6:color=#111111",
        "-fps_mode", "vfr", sheet,
    ])
    print(f"[Done] Primary render: {primary_out}")
    if args.aspect == "both":
        print(f"[Done] Widescreen 16:9: {out_16x9}")
    print(f"[Done] Review sheet: {sheet}")


if __name__ == "__main__":
    main()
