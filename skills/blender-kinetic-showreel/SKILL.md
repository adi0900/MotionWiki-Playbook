---
name: blender-kinetic-showreel
description: End-to-end Blender 4.2+/5.x + Python VFX pipeline to build or import any 3D vehicle/product, light it in a high-contrast dark-metallic pure-white studio, animate multi-angle zero-clipping cameras (4:5 vertical or 16:9 widescreen, 4.5s / 10s / 25s), and composite kinetic editorial motion graphics (CV tracking webs, B&W specular node graphs, Bayer-dithered halftone waves, strobing inverted-contrast typography with pixel-outline lead glyphs, HUD telemetry, and seamless loop glitches). Use whenever someone wants to recreate the MotionViz / Defender / Porsche 911 kinetic 3D studio reveal from scratch.
license: MIT
compatibility: Blender 4.2+ / 5.3+, Python 3.10+ (numpy, pillow), FFmpeg. macOS (Metal), NVIDIA (CUDA/OptiX), AMD (HIP), or CPU.
metadata:
  author: MotionViz
  version: "1.0.0"
---

# Blender Kinetic 3D Studio Showreel (End-to-End)

Recreate a full high-fashion 3D studio reveal + kinetic motion-graphics video (like the **MotionViz × Porsche 911 GT3** and **Land Rover Defender** top-down / multi-angle edits) from start to finish with **zero external paid assets**.

## Prerequisites
- **Blender 4.2+ / 5.3+** (`blender` in `PATH`)
- **Python 3.10+** with `numpy` and `pillow` (or `uv run --with numpy --with pillow python3 ...`)
- **FFmpeg** (`ffmpeg` + `ffprobe` in `PATH`)

## Quick Start (One-Shot Porsche 911 GT3 Example)
```bash
SKILL_DIR="<path-to-this-skill>"
OUT_DIR="./my-911-showreel"
mkdir -p "$OUT_DIR/renders"

# 1) Build the QA-clean 3D Porsche 911 GT3 (or substitute your own .blend!)
blender -b --factory-startup --python-exit-code 1 \
  -P "$SKILL_DIR/scripts/build_porsche911.py" -- --out "$OUT_DIR/hero.blend"

# 2) Add 360° automotive studio softboxes + zero-clipping animated cameras
#    Modes: topdown (4.5s, 4:5) | fast-10s (10s, 16:9) | full-25s (25s, 4:5 or 16:9)
blender -b --factory-startup --python-exit-code 1 \
  -P "$SKILL_DIR/scripts/setup_showreel_cameras.py" -- \
  --blend "$OUT_DIR/hero.blend" \
  --out "$OUT_DIR/scene.blend" \
  --mode fast-10s --aspect 16:9 --samples 14

# 3) Render transparent RGBA PNG frames (GPU auto-detected)
blender -b "$OUT_DIR/scene.blend" -E CYCLES \
  -o "$OUT_DIR/renders/frame_####" -F PNG -a

# 4) Composite pure-white studio + kinetic VFX + inverted-contrast typography -> MP4
uv run --with numpy --with pillow python3 "$SKILL_DIR/scripts/compose_showreel.py" \
  --renders "$OUT_DIR/renders" \
  --out "$OUT_DIR/final_showreel.mp4" \
  --mode fast-10s --aspect 16:9 \
  --brand "MOTIONVIZ" --word1 "MOTION" --word2 "VIZ" --model "911 GT3"
```

---

## Step-by-Step Pipeline Architecture

### Stage 1 — Real 3D Asset & Look-Dev Rules
Use `scripts/build_porsche911.py` as a reference implementation, or bring any clean `.blend` / `.glb` / `.fbx` hero mesh centered at `(0, 0, 0)` resting on `Z = 0` with front pointing `-Y` and rear `+Y`:
- **Never fake 3D with flat cutouts or camera projection**: build real manifold 3D geometry (Subdivision Surface + Bevel, applied scales `(1,1,1)`, outward normals, zero z-fighting, zero floating parts).
- **Dark-metallic automotive paint**: low linear albedo (`0.025–0.038`), `Metallic = 0.82–0.85`, micro-varied `Roughness` (`0.14–0.21` via `ShaderNodeTexNoise`), `Coat Weight = 1.0`, `Coat Roughness = 0.025–0.035`.
- **Single saturated accent color**: e.g. electric cobalt blue `(0.010, 0.032, 0.72)` on stripes, calipers, tow strap, wing endplates, or roll cage — creates instant graphic pop against obsidian paint and pure white studio.
- **Glowing headlights / lamps (critical!)**:
  - Use a **metallic silver/chrome reflector bowl** (`Base Color = (0.78, 0.82, 0.88)`, `Metallic = 0.96`), never matte black.
  - Point emissive LEDs **forward** (`+X` Euler tilt `+45°` when front is `-Y`; negative `-X` tilts them backward into the hood!).
  - Use a **thin transparent lens** (`Alpha = 0.22`, `Transmission = 0.0`, `Coat = 1.0`, `obj.visible_shadow = False`) instead of a solid refractive sphere (which turns black via total internal reflection).

### Stage 2 — 360° Studio Lighting & Zero-Clipping Multi-Angle Cameras (`scripts/setup_showreel_cameras.py`)
- **Pure `#FFFFFF` White Background Without Grey Wash**:
  - Never rely on `World = (1,1,1)` with `AgX` (AgX tone-maps pure white world to ~70% grey).
  - Instead, set **`scene.render.film_transparent = True`** (`RGBA` PNG output) and keep the World environment dark (`Strength = 0.25–0.30`) so dark metallic paint gets high-contrast reflections while the compositor lays `#FFFFFF` cleanly behind the alpha channel!
- **360° Softbox Rig**:
  - 1 sweeping overhead softbox (`Light_Overhead_Sweep`, animated back-and-forth along `Y` for liquid reflection glides across hood/roof/fenders) + left/right long strip softboxes + front strip + rear strip + soft top fill.
- **Dedicated Cameras Bound to `scene.timeline_markers`**:
  - Hard cuts between angles use Blender's `marker.camera = cam_obj` so there is zero camera-whip interpolation between angles.
  - **Mathematical Zero-Clipping Check**: the script projects all 8 world bounding-box corners of the hero asset through `bpy_extras.object_utils.world_to_camera_view` on **every single frame** and automatically scales camera distance until every frame stays inside `[0.10..0.90]` horizontally and vertically — guaranteeing zero clipped wings, noses, or bumpers!
- **Fast High-Res Rendering Tip**:
  - For 16:9 1080p, rendering Blender at `1280×720` (`14 samples + adaptive 0.055 + OIDN RGB_ALBEDO_NORMAL + use_persistent_data = True`) cuts render time by **~2.3×** while `compose_showreel.py` upscales the smooth denoised 3D car via Lanczos and renders all typography, CV webs, HUD, and dithering at **native crisp 1920×1080**!

### Stage 3 — Kinetic VFX & Motion-Graphics Compositor (`scripts/compose_showreel.py`)
Every effect reads the live RGBA frame's **alpha silhouette bounding box** and **luminance**, so it automatically locks onto ANY 3D asset from ANY camera angle:
1. **Electric Accent Paint-Splash & Checkerboard Intro**: real rendered subject underneath vibrant accent pixel blocks + checkerboard dither + HUD.
2. **Animated Pixel-Cursor Blockout & Strobe Blinks**: chunky silhouette blocks with growing white cursor notches and 1-frame black strobe blinks.
3. **Dynamic CV Tracking Web**: inverted pure `#000000` background + high-contrast white luminance/edge cutout + 9 proportionally locked bounding boxes + retargeting spiderweb lines that animate every frame.
4. **Sweeping B&W Specular Node Cutout**: pure `#FFFFFF` background + sweeping luminance threshold + re-routing geometric node graph.
5. **Morphing Bayer-Dithered Halftone Waves**: 4×4 Bayer matrix with animated vertical phase wave and edge glitch sparks.
6. **Inverted-Contrast Kinetic Typography**: difference-blended (`255 - bg`) huge titles (`MOTION` / `VIZ` / `911 GT3` / `MOTIONVIZ`) with a **chunky pixelated-outline leading glyph** — automatically renders jet-black over the pure white backdrop and crisp white over the dark car!
7. **Resolution-Scaled Monospace HUD**: crisp `24px` (on 1080p) / `10–12px` (on 720×900) camera tag, trace counter, frame counter, and frequency readout.
8. **Seamless Loop Outro**: 4-frame `LOST DATA` pixel breakdown into pure dark silhouette.

### Stage 4 — Mandatory Visual QA Before Delivery
1. Inspect the generated `*_contact_sheet.jpg` to verify:
   - Zero clipping on all 4 edges across every camera angle.
   - Bright, readable headlights/taillights and clean metallic reflections.
   - Every title and HUD readout is crisp and legible at phone/feed width.
2. Verify final MP4 with `ffprobe` (exact frame count, 24 fps, `yuv420p`, non-zero size).

## Bundled Scripts
- [scripts/build_porsche911.py](scripts/build_porsche911.py) — Standalone parametric 3D Porsche 911 (992 GT3) builder with bright 4-point LED headlights and QA-clean topology.
- [scripts/setup_showreel_cameras.py](scripts/setup_showreel_cameras.py) — Universal 360° studio lighting + multi-angle camera rig + mathematical zero-clipping guard for any `.blend` asset.
- [scripts/compose_showreel.py](scripts/compose_showreel.py) — Universal dynamic VFX, CV tracking, Bayer dither, inverted-contrast typography, and FFmpeg MP4 compositor.
