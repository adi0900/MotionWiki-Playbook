<p align="center">
  <img src="./assets/logo.png" alt="MotionViz" width="120" />
</p>

<h1 align="center">MotionViz Playbook &amp; Agent Skills</h1>

<p align="center">
  <strong>Turn any raw clip or 3D concept into studio-grade optical scans, kinetic Blender showreels, full multi-agent 3D worlds, and agency-grade brand &amp; web systems — locally for $0.</strong>
</p>

<p align="center">
  <a href="https://github.com/adi0900/MotionWiki-Playbook"><img src="https://img.shields.io/badge/Agent_Skills-6_Skills-111827?style=for-the-badge" alt="Agent Skills" /></a>
  <a href="https://x.com/Motion_Viz"><img src="https://img.shields.io/badge/@Motion__Viz-X-000000?style=for-the-badge&logo=x&logoColor=white" alt="X" /></a>
  <a href="https://linktr.ee/motionviz"><img src="https://img.shields.io/badge/Links-MotionViz-ff4f6d?style=for-the-badge" alt="MotionViz" /></a>
</p>

---

## Install All 6 Skills in One Command

Works with **Claude Code**, **Codex**, **Gemini / Antigravity**, and any Agent Skills-compatible client:

```bash
npx skills add https://github.com/adi0900/MotionWiki-Playbook.git
```

---

## Live Video Skill Showcases

### 1. `blender-world-showcase` — Multi-Agent 3D World Builder & Breakdown Film

<p align="center">
  <img src="./assets/blender-world-showcase-demo.gif" alt="Blender 3D World Showcase Demo" width="760" />
</p>

Build **any original 3D world** (sci-fi alley, sunlit Venetian canal, fantasy market street, solarpunk terrace, medieval lane, or steampunk corridor) with parallel agents in **Blender 4.2+/5.3+**, and render a complete **6-segment studio breakdown film** locally for **$0** — zero stock models, zero paid 3D assets.

- **Versatile for any theme:** Define your own world in `manifest.json` (or drop any `.blend` assets into `assets/` for zero-config auto-layout) across **5 surfaces** (`wet_asphalt`, `stone_canal`, `cobblestone`, `sand_plaza`, `metal_deck`) and **5 EEVEE look-dev moods** (`arcane_zaun`, `cyberpunk_neon`, `golden_hour`, `moonlit_fog`, `sunlit_sky`).
- **Complete 6-segment breakdown:** Dynamic hero dolly → Blender Solid Clay + real 3D floor grid crane pull-up → orange-to-clay `POP_*` pop-in assembly timelapse → two right-framed 4-stage hero build turntables with top-left concept insets → Clay-to-Final diagonal wipe into a banked canyon dive.
- **Physics-safe Blender 5.3 EEVEE + Python VFX:** Automated sky-slit / bounded local mist cube (no black skies), true dielectric wet surfaces, zero specular blobs, optional painterly/cinematic linear-light optical bloom, drifting haze, and rain.
- **One-command masters:** Outputs `1080p`, `4K UHD`, and a GitHub-ready `600×338` README demo GIF via [`skills/blender-world-showcase/SKILL.md`](./skills/blender-world-showcase/SKILL.md).

---

### 2. `flatbed-scanner-film` — 1200 DPI Optical Flatbed CCD Slit-Scan

<p align="center">
  <img src="./assets/flatbed-scanner-demo.gif" alt="Flatbed Scanner Film Demo" width="760" />
</p>

Drop in **any raw video clip** and turn it into a frame-synced **14.5-second 1200 DPI optical flatbed scanner film** locally on your machine for **$0** — zero After Effects plugins, zero paid VFX packs, zero extra AI tokens.

- **Local foreground cutouts:** Native macOS **Apple Vision** (`VNGenerateForegroundInstanceMaskRequest`, `~8s` for 193 frames) with automatic `rembg` fallback on Linux/Windows.
- **Temporal RGB CCD slit-scan:** Clinical off-white flatbed lightbox glass with procedural dust/micro-fibers + pitch-black RGB X-ray darkroom void.
- **Dot-matrix technical HUD:** Custom `--brand`, `--subtitle`, and `--obj1..3` specimen labels.
- **Frame-synced procedural soundtrack:** Mechanical carriage ratchet, servo light-bar sweeps, sub-bass, glitch arpeggios, and cut impacts synthesized in NumPy.
- **Exports:** `9:16` (`1080×1920` cinema strip), `16:9` (`1920×1080`), or `both` in browser-safe H.264 + AAC.

```bash
python3 skills/flatbed-scanner-film/scripts/run_pipeline.py \
  --input /path/to/your_clip.mp4 \
  --out ./scanner_out \
  --aspect both \
  --brand "YOUR BRAND" \
  --subtitle "1200 DPI SCAN"
```

---

### 3. `blender-kinetic-showreel` — Procedural 3D Studio + Kinetic Editorial VFX

<p align="center">
  <img src="./assets/blender-kinetic-demo.gif" alt="Blender Kinetic Showreel Demo" width="760" />
</p>

End-to-end **Blender 4.2+/5.x + Python VFX pipeline** to build or import any 3D vehicle or product, light it in a high-contrast dark-metallic pure-white studio, animate multi-angle zero-clipping cameras (`4:5` vertical or `16:9` widescreen), and composite kinetic editorial motion graphics.

- **Zero-clipping studio cameras:** Automated orbit, low-angle hero, wheel/detail, and rear-quarter shots.
- **Kinetic editorial VFX layer:** Computer-vision tracking webs, B&W specular node graphs, Bayer-dithered halftone waves, strobing inverted-contrast typography, HUD telemetry, and seamless loop glitches.
- **Fully scripted:** Reproducible Blender Python + FFmpeg pipeline in [`skills/blender-kinetic-showreel/SKILL.md`](./skills/blender-kinetic-showreel/SKILL.md).

---

## All 6 Skills

| Skill | Category | What It Does |
|---|---|---|
| [`blender-world-showcase`](./skills/blender-world-showcase/SKILL.md) | 3D / Multi-Agent Worlds | Build any original 3D world with parallel agents + 6-segment Clay/Assembly/Hero/Dive breakdown film (`$0` local) |
| [`flatbed-scanner-film`](./skills/flatbed-scanner-film/SKILL.md) | Video / Local VFX | 1200 DPI optical flatbed CCD slit-scan + Apple Vision cutouts + procedural synth audio (`$0` local) |
| [`blender-kinetic-showreel`](./skills/blender-kinetic-showreel/SKILL.md) | 3D / Blender 5.x | Procedural 3D studio lighting, multi-angle cameras, and kinetic editorial VFX compositing |
| [`visual-identity`](./skills/visual-identity/SKILL.md) | Branding | Identity boards, symbol logic, typography direction, palette systems, and guidelines |
| [`website-design`](./skills/website-design/SKILL.md) | Web Design | Engineered, anti-slop landing pages and flagship product-site architecture |
| [`cro-audit`](./skills/cro-audit/SKILL.md) | Growth / CRO | Consultant-grade conversion diagnostics, revenue leak analysis, and prioritized fix plans |

---

## Repository Structure

```text
MotionWiki-Playbook/
├── README.md
├── assets/
│   ├── logo.png
│   ├── blender-world-showcase-demo.gif
│   ├── flatbed-scanner-demo.gif
│   └── blender-kinetic-demo.gif
└── skills/
    ├── blender-world-showcase/
    │   ├── SKILL.md
    │   ├── examples/
    │   └── scripts/
    ├── flatbed-scanner-film/
    │   ├── SKILL.md
    │   └── scripts/
    ├── blender-kinetic-showreel/
    │   ├── SKILL.md
    │   └── scripts/
    ├── visual-identity/
    │   └── SKILL.md
    ├── website-design/
    │   └── SKILL.md
    └── cro-audit/
        └── SKILL.md
```

---

## Links & Support

- **Follow updates & new drops:** [@Motion_Viz on X](https://x.com/Motion_Viz)
- **All links:** [linktr.ee/motionviz](https://linktr.ee/motionviz)
- **Support MotionViz:** [Whop](https://whop.com/checkout/plan_wmAQHOcSQVt0G)
