---
name: blender-world-showcase
description: End-to-end Blender 4.2+/5.3+ multi-agent 3D world-building and cinematic breakdown pipeline for ANY environment theme — sci-fi alleys, fantasy canals, sunlit Mediterranean streets, solarpunk plazas, medieval markets, or steampunk corridors. Build 12–24 modular 3D assets in parallel with build_stage (1–4) tags, assemble them into a full street/corridor world via JSON manifest or zero-config auto-layout, apply physics-safe Blender 5.3 EEVEE lighting & wet/dry dielectric look-dev across 5 mood presets, render a 6-segment breakdown film (hero dolly, Blender Solid Clay + 3D floor grid crane pull-up, orange pop-in assembly timelapse, two right-framed 4-stage hero build turntables with top-left concept insets, and Clay-to-Final diagonal wipe into a banked dive), run optional linear-light painterly/cinematic VFX, and composite 1080p, 4K, and README GIF masters locally for $0.
license: MIT
compatibility: Blender 4.2+ / 5.3+, Python 3.10+ (numpy, opencv-python, pillow), FFmpeg. macOS (Apple Silicon Metal), NVIDIA (CUDA/OptiX), AMD (HIP), or CPU.
metadata:
  author: MotionViz
  version: "1.0.0"
---

# Blender Multi-Agent 3D World Builder & Breakdown Showcase

Turn **any original 3D world concept** (sci-fi corridor, sunlit Venetian canal, fantasy market street, solarpunk terrace, steampunk undercity, or desert bazaar) into a complete **33-second, 6-segment studio breakdown film** locally for **$0** — zero stock models, zero paid 3D marketplaces, zero After Effects.

### What the 6-Segment Breakdown Film Shows
1. **Hero World Dolly (`0:00–5.5s`)**: Dynamic 22mm low-to-high sweep showcasing lighting, reflections, and depth.
2. **Final -> Blender Clay Pull-Up (`5.5s–9.5s`)**: Seamless dissolve into authentic Blender Solid Viewport Clay on a real 3D floor grid with Red X / Green Y axes, craning out to isometric overview.
3. **Orange Pop-In Assembly Timelapse (`9.5s–17.5s`)**: Ordered `POP_*` collection build-out down the full corridor, freshly spawned assets flashing Blender Selection Orange (`#F07A24`) before settling into matte clay, overhead details snapping in last.
4. **Hero #1 4-Stage Construction Turntable (`17.5s–22.5s`)**: Isolated studio turntable (auto-framed right-of-center) animating `build_stage 1 -> 2 -> 3 -> 4` -> full AgX shaded reveal, with the native-resolution concept reference pinned cleanly in the top-left corner.
5. **Hero #2 4-Stage Construction Turntable (`22.5s–27.5s`)**: Second hero asset turntable with top-left concept reference inset.
6. **Clay Overview -> Final Diagonal Wipe + Banked Dive (`27.5s–33.5s`)**: 1.0s hold on the completed clay overview, `diagtl` diagonal wipe directly into the lit overhead world, then a swooping banked crane dive back into the street.

---

## Prerequisites
- **Blender 4.2+ / 5.3+** (`blender` in `PATH`)
- **Python 3.10+** with `numpy`, `opencv-python`, and `pillow` (or run via `uv run --with numpy --with opencv-python --with pillow python3 ...`)
- **FFmpeg** (`ffmpeg` + `ffprobe` in `PATH`)

---

## Universal Project Layout

Every script accepts `--project-dir <DIR>` (or env var `WORLD_PROJECT_DIR`):

```text
<PROJECT_DIR>/
├── manifest.json          # Optional world blueprint (theme, surface, mood, asset placements)
├── references/            # Concept/asset reference PNGs (e.g. hero1.png, hero2.png)
├── textures/              # Procedural banners, signs, decals from scripts/generate_signage.py
├── assets/                # 12–24 modular packed .blend files, each containing ASSET_<id>
├── previews/              # Isolated 640x640 studio QA PNGs auto-rendered per asset
├── renders/               # Master street + overhead verification stills
├── video_parts/           # Rendered JPEG sequences (seg1_hero_dolly .. seg7_dive)
├── video_parts_vfx/       # Linear-light VFX graded frames
├── world_master.blend     # Assembled master scene with _ASSET_LIBRARY + ordered POP_* collections
└── soundtrack.m4a         # Optional audio track (.m4a / .mp3 / .wav)
```

---

## Quick Start (Build Any Custom 3D World End-to-End)

```bash
SKILL_DIR="<path-to-this-skill>"
PROJ="./my-custom-world"
mkdir -p "$PROJ"/{references,textures,assets,previews,renders,video_parts}

# 1) (Optional) Generate procedural signs, banners & decals for your theme
#    Starter presets: cyberpunk | fantasy | scifi | market  (or pass --spec custom_signs.json)
uv run --with pillow python3 "$SKILL_DIR/scripts/generate_signage.py" \
  --out-dir "$PROJ/textures" --preset market

# 2) Build 12–24 modular 3D assets in parallel (see Stage 1 Asset Contract below).
#    Each builder script imports $SKILL_DIR/scripts/world_utils.py, creates collection
#    ASSET_<id>, tags every mesh with build_stage=1..4, and calls save_asset_and_preview().

# 3) Assemble the master world from manifest.json (or omit --manifest for zero-config auto-layout!)
blender -b --factory-startup --python-exit-code 1 \
  -P "$SKILL_DIR/scripts/assemble_world.py" -- \
  --project-dir "$PROJ" \
  --manifest "$PROJ/manifest.json"

# 4) Render Blender Clay pull-up, Orange Assembly Timelapse, and 2 Hero 4-Stage Turntables
for MODE in seg2_3_clay seg4_assembly seg5_hero1 seg6_hero2; do
  blender -b --factory-startup --python-exit-code 1 \
    -P "$SKILL_DIR/scripts/render_breakdown.py" -- \
    --project-dir "$PROJ" --mode "$MODE" \
    --hero1 "<hero1_asset_id>" --hero2 "<hero2_asset_id>"
done

# 5) Apply Blender 5.3 EEVEE look-dev preset & render dynamic hero dolly + banked dive
#    Mood presets: arcane_zaun | cyberpunk_neon | golden_hour | moonlit_fog | sunlit_sky
for MODE in seg1_hero_dolly seg7_dive; do
  blender -b --factory-startup --python-exit-code 1 \
    -P "$SKILL_DIR/scripts/setup_world_lookdev.py" -- \
    --project-dir "$PROJ" --mode "$MODE" --mood golden_hour --samples 20
done

# 6) Run parallel linear-light VFX grade
#    Styles: painterly (Arcane brushwork + ink edges) | cinematic (bloom + ACES) | clean
uv run --with numpy --with opencv-python python3 "$SKILL_DIR/scripts/grade_world_vfx.py" \
  --project-dir "$PROJ" --style cinematic --haze --no-rain

# 7) Composite 1080p (+ optional 4K UHD + optional README demo GIF)
python3 "$SKILL_DIR/scripts/composite_breakdown.py" \
  --project-dir "$PROJ" \
  --hero1-ref "$PROJ/references/<hero1_asset_id>.png" \
  --hero2-ref "$PROJ/references/<hero2_asset_id>.png" \
  --audio "$PROJ/soundtrack.m4a" \
  --gif "$PROJ/world_demo.gif"
```

---

## Stage-by-Stage World-Building Guide (For Any Theme)

### Stage 0 — Design Your World Blueprint (`manifest.json`)
Start by designing **your own original world** rather than copying an existing one. Copy [`examples/manifest.example.json`](./examples/manifest.example.json) and customize:
- **`world.surface`**:
  - `wet_asphalt`: Rain-soaked dark dielectric street with procedural mirror puddles & curbs.
  - `stone_canal`: Venetian / fantasy stone canal with reflective dielectric water strip + quayside promenades.
  - `cobblestone`: Damp European / medieval / steampunk stone street with curbs & iron drains.
  - `sand_plaza`: Warm sunlit sandstone / desert bazaar promenade.
  - `metal_deck`: Industrial orbital / sci-fi steel walkway with safety trim.
- **`world.corridor_width` & `world.corridor_length`**: Defaults to `4.2m` street width × `46m` length (dramatic deep perspective canyon), adjustable for wider boulevards (`6–10m`) or tighter lanes (`3m`).
- **`world.overhead_style`**: `cables` (sagging utility lines), `festoon` (strung festival lantern/banner ropes), or `none` (open sky).
- **4-Tier Asset Catalog (12–24 custom assets)**:
  1. **Tier 1 — Hero Architecture (3–5 assets)**: Iconic foreground facades (`~4m` wide, `6–12m` tall, front facing `-Y`, resting on `Z=0`).
  2. **Tier 2 — Midground Infill / Towers (3–5 assets)**: Taller framing structures (`8–20m` tall) that form the skyline silhouette.
  3. **Tier 3 — Hero Centerpieces / Vehicles / Statues (2–4 assets)**: Street-level silhouettes (boats, hoverbikes, carts, fountains, kiosks, mechs, shrines).
  4. **Tier 4 — Modular Props, Signs & Wall Dressing (4–10 assets)**: Crates, tables, banners, planters, lamps, awnings, vents, totems.

> **Zero-Config Mode:** If you skip `--manifest`, `assemble_world.py` automatically discovers every `*.blend` file in `<PROJECT_DIR>/assets/`, classifies tall structures vs street props by bounding box, and populates a balanced 46m corridor automatically!

### Stage 1 — Multi-Agent Parallel Asset Contract (`scripts/world_utils.py`)
Spawn 3–8 parallel agents (2–4 assets each) so all assets build concurrently. Every asset builder script MUST follow 5 rules:
1. Import `world_utils` from `$SKILL_DIR/scripts/` and call `wu.configure_project(project_dir)` then `wu.reset_scene()`.
2. Put all objects inside one collection named `ASSET_<asset_id>`.
3. Center the asset at `(0, 0)` horizontally, resting cleanly on `Z = 0`, with its **front facade/nose facing `-Y`** (the assembler rotates left-side structures `+90°` and right-side structures `-90°`).
4. **Tag every object with `build_stage` (`1`..`4`)** via `wu.link_obj(obj, col, build_stage=N)`:
   - `1`: Structural shell, foundation, walls, chassis, hull.
   - `2`: Recesses, arches, roofs, trim, doors, shutters, framing.
   - `3`: Pipes, awnings, rigging, railings, mechanical assemblies, greenery.
   - `4`: Signage, glowing accents, lanterns, decals, micro-clutter.
5. End with `wu.save_asset_and_preview(asset_id, col)` — packs all textures, saves clean `assets/<asset_id>.blend` before adding temporary studio lights, then renders a `640×640` verification PNG to `previews/<asset_id>.png`.

### Stage 2 — Master Assembly (`scripts/assemble_world.py`)
- Appends each `ASSET_<id>` once into an **unlinked** `_ASSET_LIBRARY` collection so template originals never appear at world origin.
- Instantiates assets using shared mesh data (keeps RAM low even with 20,000+ objects) into sorted `POP_001_*` .. `POP_999_*` collections interleaved down the corridor so the assembly timelapse cascades naturally into depth.
- Automatically disables shadow casting on tiny instanced interior asset lights so Blender 5.3 EEVEE's shadow tile buffer never overflows.

### Stage 3 — Physics-Safe Blender 5.3 EEVEE Look-Dev (`scripts/setup_world_lookdev.py`)
Automates five critical Blender 5.3 EEVEE fixes across all 5 mood presets (`arcane_zaun`, `cyberpunk_neon`, `golden_hour`, `moonlit_fog`, `sunlit_sky`):
1. **No Black Sky Bug in Daylight/Sunset**: Never attach infinite World `VolumeScatter` to bright sky worlds (`golden_hour`, `sunlit_sky`) — infinite volume absorbs sky rays to pure black in EEVEE! Instead, `setup_world_lookdev.py` creates a **bounded local mist cube** (`_LocalMistBox`, auto-hidden in Clay mode) while keeping Nishita / gradient skies vibrant.
2. **Night Sky Slit (`Light Path -> Is Camera Ray`)**: For night moods (`arcane_zaun`, `cyberpunk_neon`, `moonlit_fog`), the camera sees a deep tinted night sky slit between rooftops while diffuse ambient stays near-black for dramatic chiaroscuro silhouettes.
3. **True Dielectric Wet Surfaces (NEVER Metallic)**: Wet asphalt, wet cobblestones, and canal water always use `Metallic = 0.0`, readable `Base Color`, `IOR 1.33–1.75`, and `Coat Weight 0.65–0.85` with roughness puddle ramps (`0.02` mirror puddles vs `0.38` damp grit). Metallic ground turns pitch-black in EEVEE raytracing!
4. **Zero Fake Specular Blobs**: Sets `light.specular_factor = 0.0` on corridor fill lights so reflective streets/canals reflect real architecture, skies, and emissive fixtures instead of giant round white dots.
5. **Zero Glowing Fog-Ball Spheres**: Caps `light.volume_factor = 0.04` on Point fill lights while letting directional Spotlights (`0.12–0.18`) or sun beams sculpt clean volumetric cones.

### Stage 4 — Breakdown Rendering (`scripts/render_breakdown.py`)
- Uses `seg1_hero_dolly` -> `seg2_3_clay` seamless camera handoff at `(-0.08, 10.95, 1.54)` @ `28mm`.
- Renders authentic Blender Solid Viewport Clay (AO cavity shader + `#3D3E40` backdrop + real 3D floor grid with Red X & Green Y axes).
- Automatically computes world bounding boxes for `seg5_hero1` and `seg6_hero2` and offsets the camera target left by `0.19 * half_w` so ANY hero asset sits cleanly in the right-center with zero overlap against the top-left concept reference inset.

### Stage 5 — Linear-Light VFX & Final Composite (`scripts/grade_world_vfx.py` + `scripts/composite_breakdown.py`)
- **`--style painterly`**: Edge-preserving bilateral brushwork + subtle Sobel ink contours (emissive-protected) + 4-tier linear-light optical Fog Glow + ACES filmic grade.
- **`--style cinematic`**: Crisp un-softened 3D geometry + linear-light optical bloom + anamorphic hotspot streaks + optional drifting canyon haze & light-reactive rain + ACES filmic grade.
- **`--style clean`**: Minimal exposure-preserving ACES polish + subtle vignette.
- **`composite_breakdown.py`** outputs 1080p, optional 4K UHD (`3840×2160` Lanczos + subtle unsharp), and an optional GitHub-ready `600×338` 2-pass palette GIF (`--gif`).

---

## Mandatory Visual QA Checklist
1. **Single-frame smoke check first**: Pass `--single-frame 0` or `--single-frame 120` to `render_breakdown.py` and `setup_world_lookdev.py` before launching full sequences.
2. **Downscale QA strips before inspecting**: Combine 4–6 frames into one `<=960px` JPEG contact sheet so vision inspection stays fast and reliable.
3. **Check for zero camera clipping & clean reflections**: Confirm foreground props don't block frame 0, wet/water surfaces reflect light cleanly (no black metallic floor, no white specular blobs), and top-left hero insets don't cover the 3D hero.
4. **Verify final MP4/GIF with `ffprobe`**: Confirm exact resolution, `30fps` (`12fps` for GIF), `yuv420p`, and audio sync.

---

## Bundled Portable Scripts & Templates
- [`examples/manifest.example.json`](./examples/manifest.example.json) — Annotated starter blueprint for defining any custom 3D world.
- [`scripts/world_utils.py`](./scripts/world_utils.py) — Universal Blender 5.3 modeling, `bmesh` UV, PBR/emissive material, `build_stage` tagging, and `.blend` + preview SDK.
- [`scripts/generate_signage.py`](./scripts/generate_signage.py) — Theme-agnostic JSON/preset procedural banner, sign, and decal generator.
- [`scripts/assemble_world.py`](./scripts/assemble_world.py) — Manifest-driven (or zero-config auto-layout) master world assembler supporting 5 surface types & `POP_*` timelapse collections.
- [`scripts/setup_world_lookdev.py`](./scripts/setup_world_lookdev.py) — 5-mood Blender 5.3 EEVEE look-dev, dielectric wet/water physics, sky/mist guard, and dynamic camera choreography.
- [`scripts/render_breakdown.py`](./scripts/render_breakdown.py) — 6-segment breakdown renderer (dolly, clay + 3D grid pull-up, orange pop-in assembly, 2 auto-framed hero 4-stage turntables, dive).
- [`scripts/grade_world_vfx.py`](./scripts/grade_world_vfx.py) — Multi-threaded linear-light VFX grader (`painterly | cinematic | clean`, optional haze & rain).
- [`scripts/composite_breakdown.py`](./scripts/composite_breakdown.py) — FFmpeg 1080p, 4K UHD, and README demo GIF compositor with top-left concept insets and Clay-to-Final diagonal wipe.
