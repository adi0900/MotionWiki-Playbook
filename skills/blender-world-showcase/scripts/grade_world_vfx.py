#!/usr/bin/env python3
"""Universal Linear-Light Python VFX Grader for 3D World Breakdowns.
Styles:
  - painterly : Edge-preserving bilateral brushwork + subtle Sobel ink contours + 4-tier optical bloom + ACES
  - cinematic : Crisp 3D geometry + 4-tier optical Fog Glow + horizontal anamorphic streak + ACES
  - clean     : Exposure-preserving ACES polish + subtle framing vignette
Optional toggles: --haze/--no-haze (drifting 2-octave volumetric canyon mist), --rain/--no-rain.
Preserves clay build frames (<108) untouched on Hero turntables."""
import argparse
import concurrent.futures
import glob
import os
import cv2
import numpy as np


def make_vignette(h, w, strength=0.34):
    y, x = np.ogrid[:h, :w]
    r2 = ((x - w * 0.5) / (w * 0.5)) ** 2 + ((y - h * 0.5) / (h * 0.5)) ** 2
    return np.clip(1.0 - strength * (r2 ** 1.3), 0.34, 1.0).astype(np.float32)[:, :, None]


def aces_filmic(x):
    return np.clip((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0)


def _build_haze_grids():
    rng = np.random.default_rng(9099)

    def wrap(h, w, sigma):
        raw = rng.uniform(0.0, 1.0, (h, w)).astype(np.float32)
        b = cv2.GaussianBlur(np.tile(raw, (3, 3)), (0, 0), sigma)
        return b[h:2 * h, w:2 * w].copy()

    return wrap(24, 42, 2.2), wrap(48, 84, 2.4)


_HAZE = _build_haze_grids()


def drifting_haze(h, w, idx):
    n1, n2 = _HAZE
    qw, qh = w // 4, h // 4

    def sample(grid, dx, dy):
        gh, gw = grid.shape
        xs = (np.linspace(0, gw, qw, endpoint=False, dtype=np.float32) - dx) % gw
        ys = (np.linspace(0, gh, qh, endpoint=False, dtype=np.float32) - dy) % gh
        mx, my = np.meshgrid(xs, ys)
        return cv2.remap(grid, mx, my, interpolation=cv2.INTER_CUBIC, borderMode=cv2.BORDER_WRAP)

    mist = np.clip((0.62 * sample(n1, idx * 0.085, -idx * 0.045) + 0.38 * sample(n2, -idx * 0.11, -idx * 0.095) - 0.28) * 1.95, 0.0, 1.0)
    yq = np.linspace(0.0, 1.0, qh, dtype=np.float32)[:, None]
    xq = np.linspace(-1.0, 1.0, qw, dtype=np.float32)[None, :]
    mask = np.exp(-(xq * xq) / 0.72) * (0.48 + 0.52 * np.exp(-((yq - 0.54) ** 2) / 0.16))
    return cv2.resize(((0.35 + 0.65 * mist) * mask).astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)[:, :, None]


def rain_layer(h, w, idx, seed=2099):
    rain = np.zeros((h, w), dtype=np.float32)
    for layer, (cnt, ln0, sy, dx, inten) in enumerate([(220, 24, 56.0, 4.0, 0.28), (90, 44, 88.0, 7.0, 0.42)]):
        rng = np.random.default_rng(seed + layer * 1009)
        xs = (rng.uniform(0, w, cnt) + idx * dx) % w
        ys = (rng.uniform(0, h, cnt) + idx * sy) % h
        lns = rng.uniform(ln0 * 0.7, ln0 * 1.35, cnt)
        for x, y, ln in zip(xs, ys, lns):
            cv2.line(rain, (int(x), int(y)), (int(x + ln * 0.08), int(y + ln)), inten, 1, cv2.LINE_AA)
    return cv2.GaussianBlur(rain, (0, 0), 0.75)[:, :, None]


def painterly_pass(bgr):
    h, w = bgr.shape[:2]
    sm = cv2.resize(bgr, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
    sm = cv2.bilateralFilter(cv2.bilateralFilter(sm, 7, 42, 9), 5, 32, 7)
    paint = cv2.resize(sm, (w, h), interpolation=cv2.INTER_LINEAR)
    orig_f, paint_f = bgr.astype(np.float32) / 255.0, paint.astype(np.float32) / 255.0
    lum = 0.2126 * orig_f[:, :, 2] + 0.7152 * orig_f[:, :, 1] + 0.0722 * orig_f[:, :, 0]
    keep = np.clip((lum - 0.42) * 2.5, 0.0, 1.0)[:, :, None]
    blended = paint_f * (0.55 * (1.0 - keep)) + orig_f * (1.0 - 0.55 * (1.0 - keep))
    gray = cv2.cvtColor(paint, cv2.COLOR_BGR2GRAY)
    mag = np.sqrt(cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3) ** 2 + cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3) ** 2) / 255.0
    ink = cv2.GaussianBlur(np.clip((mag - 0.18) * 1.45, 0.0, 0.52) * (1.0 - keep[:, :, 0]), (0, 0), 0.6)[:, :, None]
    return np.clip(blended * (1.0 - ink * 0.62) * 255.0, 0, 255).astype(np.uint8)


def grade_frame(bgr, idx, mode, style, use_haze, use_rain):
    if mode == "hero" and idx < 108:
        return bgr
    h, w = bgr.shape[:2]
    src_bgr = painterly_pass(bgr) if style == "painterly" else bgr
    rgb = cv2.cvtColor(src_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    lin = np.power(np.clip(rgb, 0.0, 1.0), 2.2)

    if style == "clean":
        srgb = np.power(aces_filmic(lin * 1.05), 1.0 / 2.2) * make_vignette(h, w, 0.22)
        return cv2.cvtColor((np.clip(srgb, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR)

    mx, mn = np.max(lin, axis=2), np.min(lin, axis=2)
    sat = (mx - mn) / (mx + 1e-5)
    is_over = (mode == "dive")

    if mode == "hero":
        glow = np.maximum(lin - 0.28, 0.0) * (1.0 + 1.15 * sat)[:, :, None] * 1.25
        g1 = cv2.GaussianBlur(glow, (0, 0), 5.0)
        g2 = cv2.resize(cv2.GaussianBlur(cv2.resize(glow, (w // 2, h // 2), interpolation=cv2.INTER_AREA), (0, 0), 11.0), (w, h), interpolation=cv2.INTER_LINEAR)
        g3 = cv2.resize(cv2.GaussianBlur(cv2.resize(glow, (w // 4, h // 4), interpolation=cv2.INTER_AREA), (0, 0), 18.0), (w, h), interpolation=cv2.INTER_LINEAR)
        flash = max(0.0, 1.0 - (idx - 108) / 10.0)
        comp = lin * (1.06 + 0.12 * flash) + (g1 * 0.52 + g2 * 0.38 + g3 * 0.22) * (1.0 + 0.80 * (flash ** 2))
        srgb = np.power(aces_filmic(comp * 1.12), 1.0 / 2.2)
        return cv2.cvtColor((srgb * 255.0 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR)

    em_mask = cv2.GaussianBlur(np.clip((mx - 0.12) * 2.5 + sat * np.clip(mx * 2.2, 0.0, 1.0) * 0.90, 0.0, 1.0), (0, 0), 3.0)[:, :, None]
    gamma = (1.22 - 0.10 * min(1.0, max(0.0, (idx - 25) / 140.0))) if is_over else 1.12
    gain = (0.88 + 0.06 * min(1.0, max(0.0, (idx - 25) / 140.0))) if is_over else 0.94
    base = (np.power(np.clip(lin, 0.0, 1.0), gamma) * gain) * (1.0 - em_mask * 0.78) + (lin * 1.20) * (em_mask * 0.78)

    glow = np.maximum(lin - 0.30, 0.0) * (1.0 + 1.15 * sat)[:, :, None] * 1.15
    g1 = cv2.GaussianBlur(glow, (0, 0), 5.0)
    g2 = cv2.resize(cv2.GaussianBlur(cv2.resize(glow, (w // 2, h // 2), interpolation=cv2.INTER_AREA), (0, 0), 11.0), (w, h), interpolation=cv2.INTER_LINEAR)
    qtr = cv2.resize(glow, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    g3 = cv2.resize(cv2.GaussianBlur(qtr, (0, 0), 19.0), (w, h), interpolation=cv2.INTER_LINEAR)
    g4 = cv2.resize(cv2.GaussianBlur(qtr, (0, 0), 42.0), (w, h), interpolation=cv2.INTER_LINEAR)
    peak = np.maximum(lin - 0.62, 0.0) * (1.0 + 1.15 * sat)[:, :, None]
    streak = cv2.resize(cv2.GaussianBlur(cv2.resize(peak, (w // 2, h // 2), interpolation=cv2.INTER_AREA), (0, 0), sigmaX=24.0, sigmaY=1.2), (w, h), interpolation=cv2.INTER_LINEAR)
    comp = base + g1 * 0.46 + g2 * 0.34 + g3 * 0.20 + g4 * 0.10 + streak * 0.14

    light_map = cv2.resize(cv2.GaussianBlur(qtr, (0, 0), 18.0), (w, h), interpolation=cv2.INTER_LINEAR)
    if use_haze:
        hs = 0.16 if not is_over else (0.08 + 0.09 * min(1.0, max(0.0, (idx - 35) / 110.0)))
        comp = comp + drifting_haze(h, w, idx) * (light_map * 0.65 + np.array([[[0.022, 0.030, 0.030]]], dtype=np.float32)) * hs
    if use_rain:
        rs = 0.24 if not is_over else (0.08 + 0.18 * min(1.0, max(0.0, (idx - 35) / 120.0)))
        comp = comp + rain_layer(h, w, idx, seed=2099 if not is_over else 4099) * (light_map * 2.2 + np.array([[[0.05, 0.08, 0.07]]], dtype=np.float32)) * rs

    comp = aces_filmic(comp * 1.16)
    _, x_g = np.ogrid[:h, :w]
    em = np.clip(((x_g - w * 0.5) / (w * 0.5)) ** 2, 0.0, 1.0).astype(np.float32)
    comp[:, :, 0] = comp[:, :, 0] * (1.0 - 0.42 * em) + np.roll(comp[:, :, 0], 2, axis=1) * (0.42 * em)
    comp[:, :, 2] = comp[:, :, 2] * (1.0 - 0.42 * em) + np.roll(comp[:, :, 2], -2, axis=1) * (0.42 * em)

    srgb = np.power(np.clip(comp, 0.0, 1.0), 1.0 / 2.2) * make_vignette(h, w, 0.38 if is_over else 0.32)
    grain = np.random.default_rng(7000 + idx).normal(0.0, 0.008, (h, w, 1)).astype(np.float32)
    return cv2.cvtColor((np.clip(srgb + grain, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR)


def _worker(task):
    src, dst, mode, idx, style, use_haze, use_rain = task
    img = cv2.imread(src)
    if img is None:
        raise RuntimeError(f"Failed to read {src}")
    cv2.imwrite(dst, grade_frame(img, idx, mode, style, use_haze, use_rain), [cv2.IMWRITE_JPEG_QUALITY, 95])


def main():
    p = argparse.ArgumentParser(description="Linear-light VFX grader for any 3D world breakdown.")
    p.add_argument("--project-dir", required=True)
    p.add_argument("--style", default="painterly", choices=["painterly", "cinematic", "clean"])
    p.add_argument("--haze", dest="haze", action="store_true", default=True)
    p.add_argument("--no-haze", dest="haze", action="store_false")
    p.add_argument("--rain", dest="rain", action="store_true", default=False)
    p.add_argument("--no-rain", dest="rain", action="store_false")
    p.add_argument("--segments", default="seg1_hero_dolly,seg1_night,seg7_dive,seg5_hero1,seg6_hero2")
    p.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 4))
    args = p.parse_args()

    proj = os.path.abspath(args.project_dir)
    parts, vfx = os.path.join(proj, "video_parts"), os.path.join(proj, "video_parts_vfx")
    mode_map = {"seg1_hero_dolly": "dolly", "seg1_night": "dolly", "seg7_dive": "dive", "seg5_hero1": "hero", "seg6_hero2": "hero"}

    tasks = []
    for seg in [s.strip() for s in args.segments.split(",") if s.strip()]:
        sd = os.path.join(parts, seg)
        if not os.path.isdir(sd):
            continue
        dd = os.path.join(vfx, seg)
        os.makedirs(dd, exist_ok=True)
        for idx, src in enumerate(sorted(glob.glob(os.path.join(sd, "f_*.jpg")))):
            tasks.append((src, os.path.join(dd, os.path.basename(src)), mode_map.get(seg, "dolly"), idx, args.style, args.haze, args.rain))

    print(f"[VFX] Grading {len(tasks)} frames (style={args.style}, haze={args.haze}, rain={args.rain})...", flush=True)
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for _ in ex.map(_worker, tasks):
            done += 1
            if done % 50 == 0 or done == len(tasks):
                print(f"[VFX] {done}/{len(tasks)} done", flush=True)
    print("[VFX ALL DONE]", flush=True)


if __name__ == "__main__":
    main()
