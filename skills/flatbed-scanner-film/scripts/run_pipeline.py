#!/usr/bin/env python3
"""
One-command orchestrator for the Flatbed Scanner Film skill:
  1. Extracts foreground masks via native macOS Apple Vision (or rembg fallback on Linux/Windows)
  2. Synthesizes the frame-synced 14.50s flatbed-scanner soundtrack
  3. Renders the 1200 DPI CCD slit-scan film (9x16, 16x9, or both) + 3x2 review sheet
"""
import argparse, os, platform, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def find_numpy_cmd() -> list:
    """Return a command prefix that can import numpy (current python, system/Blender python, or uv)."""
    candidates = [
        [sys.executable],
        ["python3.13"],
        ["python3.12"],
        ["python3.11"],
        ["/usr/bin/python3"],
        ["/Applications/Blender.app/Contents/Resources/5.3/python/bin/python3.13"],
    ]
    for c in candidates:
        exe = shutil.which(c[0]) if not os.path.isabs(c[0]) else (c[0] if os.path.exists(c[0]) else None)
        if not exe:
            continue
        r = subprocess.run([exe, "-c", "import numpy"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if r.returncode == 0:
            return [exe]
    if shutil.which("uv"):
        return ["uv", "run", "--with", "numpy", "python"]
    sys.exit("ERROR: numpy is required. Install with `pip install numpy` or install `uv`.")


def extract_masks(input_mp4: str, work_dir: str) -> str:
    mask_mp4 = os.path.join(work_dir, "subject_mask.mp4")
    frames_in = os.path.join(work_dir, "_frames_in")
    frames_msk = os.path.join(work_dir, "_frames_mask")
    os.makedirs(frames_in, exist_ok=True)
    os.makedirs(frames_msk, exist_ok=True)

    print("[1/3] Extracting source frames for foreground masking...", flush=True)
    subprocess.check_call([
        "ffmpeg", "-y", "-v", "error", "-i", input_mp4,
        os.path.join(frames_in, "f_%05d.png"),
    ])

    if platform.system() == "Darwin" and shutil.which("swiftc"):
        bin_path = os.path.join(work_dir, "extract_masks_bin")
        swift_src = os.path.join(HERE, "extract_masks.swift")
        if not os.path.exists(bin_path):
            print("[1/3] Compiling native Apple Vision mask extractor (swiftc -O)...", flush=True)
            subprocess.check_call(["swiftc", "-O", swift_src, "-o", bin_path])
        print("[1/3] Running Apple Vision VNGenerateForegroundInstanceMaskRequest...", flush=True)
        subprocess.check_call([bin_path, frames_in, frames_msk])
    else:
        print("[1/3] macOS swiftc unavailable; trying rembg fallback...", flush=True)
        try:
            from rembg import remove
            from PIL import Image
        except ImportError:
            sys.exit("ERROR: Non-macOS requires rembg (`pip install rembg pillow`) or pass --mask-video <path>.")
        files = sorted(f for f in os.listdir(frames_in) if f.endswith(".png"))
        for idx, fn in enumerate(files, 1):
            im = Image.open(os.path.join(frames_in, fn)).convert("RGBA")
            out = remove(im, only_mask=True)
            out.save(os.path.join(frames_msk, fn))
            if idx % 40 == 0 or idx == len(files):
                print(f"Masked {idx}/{len(files)}", flush=True)

    # Probe source FPS so mask video stays 1:1 frame-synced
    fps = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate", "-of", "default=nw=1:nk=1", input_mp4,
    ]).decode().strip() or "24"

    subprocess.check_call([
        "ffmpeg", "-y", "-v", "error", "-framerate", fps,
        "-i", os.path.join(frames_msk, "f_%05d.png"),
        "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", mask_mp4,
    ])
    shutil.rmtree(frames_in, ignore_errors=True)
    shutil.rmtree(frames_msk, ignore_errors=True)
    print(f"[1/3] Saved mask video -> {mask_mp4}", flush=True)
    return mask_mp4


def main():
    ap = argparse.ArgumentParser(description="End-to-end 1200 DPI Flatbed Scanner Film pipeline")
    ap.add_argument("--input", required=True, help="Main subject video (MP4/MOV)")
    ap.add_argument("--pan", default="", help="Optional 2nd wide/environment clip")
    ap.add_argument("--out", default="./scanner_out", help="Output directory")
    ap.add_argument("--aspect", choices=["9x16", "16x9", "both"], default="9x16")
    ap.add_argument("--brand", default="MOTION VIZ")
    ap.add_argument("--subtitle", default="1200 DPI SCAN")
    ap.add_argument("--obj1", default="SUBJECT")
    ap.add_argument("--obj2", default="UPPER")
    ap.add_argument("--obj3", default="DETAIL")
    ap.add_argument("--upper-y", type=float, default=0.05)
    ap.add_argument("--detail-y", type=float, default=0.30)
    ap.add_argument("--mask-video", default="", help="Reuse an existing grayscale mask MP4")
    ap.add_argument("--test", action="store_true", help="Render fast 6-frame 3x2 contact sheet only")
    args = ap.parse_args()

    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)

    py_cmd = find_numpy_cmd()
    mask_mp4 = args.mask_video if args.mask_video and os.path.exists(args.mask_video) else extract_masks(args.input, out_dir)

    audio_wav = os.path.join(out_dir, "scanner_soundtrack_14s.wav")
    if not args.test:
        print("[2/3] Synthesizing 14.5s flatbed scanner soundtrack...", flush=True)
        subprocess.check_call(py_cmd + [os.path.join(HERE, "build_audio_scan.py"), "--out", audio_wav])

    print("[3/3] Rendering optical flatbed CCD slit-scan...", flush=True)
    cmd = py_cmd + [
        os.path.join(HERE, "render_scanner_video.py"),
        "--input", args.input,
        "--mask", mask_mp4,
        "--audio", audio_wav,
        "--out-dir", out_dir,
        "--aspect", args.aspect,
        "--brand", args.brand,
        "--subtitle", args.subtitle,
        "--obj1", args.obj1,
        "--obj2", args.obj2,
        "--obj3", args.obj3,
        "--upper-y", str(args.upper_y),
        "--detail-y", str(args.detail_y),
    ]
    if args.pan:
        cmd += ["--pan", args.pan]
    if args.test:
        cmd += ["--test"]
    subprocess.check_call(cmd)


if __name__ == "__main__":
    main()
