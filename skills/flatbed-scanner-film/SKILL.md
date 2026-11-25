---
name: flatbed-scanner-film
description: Turn any raw video clip into a 14.5-second 1200 DPI optical flatbed CCD slit-scan specimen film (clinical white lightbox glass + pitch-black RGB X-ray darkroom + dot-matrix HUD + frame-synced mechanical scanner soundtrack) locally for $0 using Apple Vision (macOS) or rembg + NumPy + FFmpeg. Use when the user asks to recreate the flatbed scanner / CCD slit-scan / Df90f4rB60D specimen-plate video effect on any video clip.
---

# Flatbed Scanner Film (`1200 DPI` Optical CCD Slit-Scan Engine)

Recreate the exact **14.5-second (`435` frames @ `30fps`) optical flatbed CCD slit-scan specimen film** locally on your machine for **$0** — no After Effects plugins, no paid VFX packs, and no extra AI video tokens.

## What This Skill Produces
From **1 main subject video** (plus an optional 2nd background/pan clip):
1. **Local Foreground Cutout Masks:** Uses native macOS **Apple Vision** (`VNGenerateForegroundInstanceMaskRequest`, `~8s` for 193 frames, `$0`) with automatic `rembg` fallback on Linux/Windows.
2. **Temporal RGB CCD Slit-Scan Shader (NumPy):**
   - **Ahead of the scanner bar:** moody darkroom-graded source footage.
   - **Behind the scanner bar (Light Plate):** background dissolves into pure clinical off-white flatbed glass (`#eff4ff`) with procedural dust/micro-fibers, leaving only the isolated subject in temporal R/G/B prismatic slit-scan displacement.
   - **Behind the scanner bar (Darkroom Plate):** pure pitch-black (`#020307`) void with luminous electric cyan/blue/magenta X-ray contours and preserved midtone detail.
   - **Dot-Matrix Technical HUD:** crisp `5x7` pixel font (`PLATE 01–03`, `SCAN 01–04`, dashed tracking boxes, mm dimensions, live `%` scan progress, and a 3-specimen finale lockup with custom brand title).
3. **Frame-Synced Mechanical Scanner Soundtrack (`44.1 kHz` Stereo WAV):**
   - Synthesized from scratch in NumPy: carriage ratchet startup (`0.00–0.80s`), servo sweep + light-bar noise whooshes, pulsing acid-saw sub-bass, modular computer-vision glitch arpeggios, punchy shutter impacts locked to every cut timestamp, and a crystalline lock-in chime at `14.08s`.
4. **Broadcast-Ready H.264 MP4 Output (`yuv420p`, `+faststart`, `AAC 192k`):**
   - `9x16` (`1080x1920` vertical reel with centered `1080x608` 16:9 cinema strip on `#000000` black — exact `Df90f4rB60D` framing).
   - `16x9` (`1920x1080` full-bleed widescreen for X / YouTube).
   - `both` (exports both aspect ratios in one run) + a `3x2` review contact sheet.

---

## Prerequisites
- **macOS 14+ (recommended):** Xcode Command Line Tools (`swiftc`), `python3`, `numpy`, `ffmpeg` (`brew install ffmpeg`).
- **Linux / Windows:** `python3`, `numpy`, `ffmpeg`, and `pip install rembg pillow` (used automatically when `swiftc` is unavailable).

---

## Quick Start (One Command)

Run the bundled orchestrator script `scripts/run_pipeline.py` from this skill folder:

```bash
python3 <SKILL_DIR>/scripts/run_pipeline.py \
  --input /path/to/subject_clip.mp4 \
  --out ./scanner_out \
  --aspect both \
  --brand "MOTION VIZ" \
  --subtitle "FLORA x BLENDER" \
  --obj1 "PASSENGER" \
  --obj2 "HEADPHONES" \
  --obj3 "CHARMS"
```

### Optional Flags
| Flag | Default | Purpose |
|---|---|---|
| `--input <mp4>` | *(required)* | Main subject clip (any resolution/aspect ratio; `>= 4s` recommended). |
| `--pan <mp4>` | *(same as `--input`)* | Optional 2nd wide/environment clip for the intro (`0.0–0.8s`) and darkroom laser sweep (`4.0–5.6s`). |
| `--out <dir>` | `./scanner_out` | Output directory for masks, audio, final MP4(s), and review sheet. |
| `--aspect` | `9x16` | `9x16` (`1080x1920` cinema strip), `16x9` (`1920x1080`), or `both`. |
| `--brand` | `"MOTION VIZ"` | 1–2 word dot-matrix lockup shown in the `SCAN 04` finale box (spaces split lines). |
| `--subtitle` | `"1200 DPI SCAN"` | Caption line beneath the finale brand box. |
| `--obj1` / `--obj2` / `--obj3` | `"SUBJECT"` / `"UPPER"` / `"DETAIL"` | Labels for the 3 dashed tracking boxes (`full`, `upper`, `detail` crops). |
| `--mask-video <mp4>` | *(auto-generated)* | Reuse an existing grayscale mask MP4 to skip mask extraction on re-renders. |
| `--test` | `false` | Fast 2-second 6-frame `3x2` contact sheet (`test_sheet.jpg`) to verify crops & labels before rendering video. |

---

## Exact 14.50-Second Beat Sheet (435 Frames @ 30fps)
Every cut in `render_scanner_video.py` is frame-locked to `build_audio_scan.py`:

| Time | Frames | Visual Sequence | Synced Audio Event |
|---|---|---|---|
| `0.00–0.80s` | `0–23` | Darkroom intro + scanner lamp warming in from left | Mechanical carriage ratchet clicks |
| `0.80–2.80s` | `24–83` | **SCAN 01:** Horizontal white CCD sweep isolating upper subject | Servo sweep `220→760 Hz` + bass entry |
| `2.80–4.00s` | `84–119` | **PLATE 01:** 3 razor-sharp `0.4s` beat cuts on clinical white glass | Modular CV glitch arpeggio + 3 shutter hits |
| `4.00–5.60s` | `120–167` | Live darkroom wide pan + diagonal blue-white laser beam | Sub-bass lift (`C2`) |
| `5.60–7.60s` | `168–227` | **SCAN 02:** Vertical electric blue/cyan sweep into black X-ray void | Downward servo sweep `700→240 Hz` |
| `7.60–9.20s` | `228–275` | **PLATE 02:** Darkroom RGB → stark white flash → Darkroom RGB | Glitch arpeggio + 3 cut impacts |
| `9.20–10.60s` | `276–317` | Moody live darkroom gaze + horizontal white flash bar | Bass drop (`A1`) + mid-bar hit |
| `10.60–12.20s` | `318–365` | **SCAN 03:** Horizontal white-plate sweep isolating detail zone | Servo sweep `260→840 Hz` |
| `12.20–13.10s` | `366–392` | **Strobe Climax:** 4 rapid `0.23s` alternating dark/light flashes | Fast climax arpeggio + 4 tight kicks |
| `13.10–14.50s` | `393–434` | **SCAN 04 Finale:** 3 floating RGB specimens + brand dot-matrix lock | Final sweep `250→980 Hz` + chime (`14.08s`) |

---

## Agent Execution Workflow (Start to End)
When a user invokes this skill with a video file:
1. **Verify dependencies** (`ffmpeg`, `python3 -c "import numpy"`, and `swiftc` on macOS).
2. **Run `--test` first** on the user's clip (`python3 <SKILL_DIR>/scripts/run_pipeline.py --input <clip> --out <out> --test ...`) to generate `<out>/test_sheet.jpg` in seconds.
3. **Inspect `<out>/test_sheet.jpg`** visually: confirm the foreground mask cleanly isolates the subject (no stray background bleed), the upper/detail crops frame the right regions, and all custom HUD labels fit cleanly inside the frame.
4. **Render the final video(s)** without `--test` (`--aspect 9x16`, `16x9`, or `both`), then inspect `<out>/final_review_sheet_14s.jpg` and confirm `ffprobe` reports `h264`, `yuv420p`, `30fps`, `aac`, `14.5s`.
5. **Deliver** the final MP4 path(s) and review sheet to the user.

---

## Troubleshooting
- **Blank or noisy foreground masks:** Make sure the subject has clear separation from the background. On macOS, Apple Vision's `VNGenerateForegroundInstanceMaskRequest` requires macOS 14+ (Sonoma or newer). On older macOS or Linux, install `rembg` (`pip install rembg pillow`) and re-run.
- **Subject cropped off-center in `UPPER` or `DETAIL` views:** Adjust `--upper-y` (default `0.06`, fraction of height from top) and `--detail-y` (default `0.36`, fraction of height from top) on `run_pipeline.py` and re-check with `--test`.
- **Browser won't play output MP4:** This skill always encodes `libx264 -profile:v high -pix_fmt yuv420p -movflags +faststart` + `aac` so it plays natively in Chrome, Safari, X, and Instagram.
