#!/usr/bin/env python3
"""Universal FFmpeg Master Compositor for 6-Segment 3D World Breakdowns:
  - Prefers VFX-graded frames from video_parts_vfx/, falling back to video_parts/
  - Pins optional Hero #1 & Hero #2 native-resolution concept insets in top-left corner
  - Holds final Clay Overview frame (1.00s) before a 0.70s diagonal wipe (diagtl) into Final Dive
  - Exports 1080p MP4, optional 4K UHD MP4, and optional GitHub-ready 600x338 demo GIF (--gif)."""
import argparse
import glob
import os
import subprocess


def run(cmd):
    print("[CMD]", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def pick_seg(parts_dir, vfx_dir, candidates):
    for name in candidates:
        vfx = os.path.join(vfx_dir, name)
        if os.path.isdir(vfx) and os.path.exists(os.path.join(vfx, "f_0000.jpg")):
            return vfx
        raw = os.path.join(parts_dir, name)
        if os.path.isdir(raw) and os.path.exists(os.path.join(raw, "f_0000.jpg")):
            return raw
    raise FileNotFoundError(f"Missing segment directory (tried {candidates}) in {parts_dir}")


def encode_seq(src_dir, out_mp4, width=1920, height=1080, sharpen=False, crf=16):
    filters = []
    if width != 1920 or height != 1080:
        filters.append(f"scale={width}:{height}:flags=lanczos+accurate_rnd+full_chroma_int")
        if sharpen:
            filters.append("unsharp=5:5:0.40:3:3:0.0")
    filters.extend(["fps=30", "format=yuv420p"])
    run(["ffmpeg", "-y", "-framerate", "30", "-i", os.path.join(src_dir, "f_%04d.jpg"),
         "-vf", ",".join(filters), "-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-pix_fmt", "yuv420p", out_mp4])


def encode_still_hold(still_jpg, duration_s, out_mp4, width=1920, height=1080, sharpen=False, crf=16):
    filters = []
    if width != 1920 or height != 1080:
        filters.append(f"scale={width}:{height}:flags=lanczos+accurate_rnd+full_chroma_int")
        if sharpen:
            filters.append("unsharp=5:5:0.40:3:3:0.0")
    filters.extend(["fps=30", "format=yuv420p"])
    run(["ffmpeg", "-y", "-loop", "1", "-framerate", "30", "-i", still_jpg, "-t", f"{duration_s:.3f}",
         "-vf", ",".join(filters), "-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-pix_fmt", "yuv420p", out_mp4])


def encode_hero_inset(src_dir, ref_png, out_mp4, width=1920, height=1080, sharpen=False, crf=16):
    if not ref_png or not os.path.exists(ref_png):
        encode_seq(src_dir, out_mp4, width, height, sharpen=sharpen, crf=crf)
        return
    sf = width / 1920.0
    sz, bd = int(round(390 * sf)), int(round(4 * sf))
    pad, ox, oy = sz + 2 * bd, int(round(72 * sf)), int(round(68 * sf))
    bg_chain = []
    if width != 1920 or height != 1080:
        bg_chain.append(f"scale={width}:{height}:flags=lanczos+accurate_rnd+full_chroma_int")
        if sharpen:
            bg_chain.append("unsharp=5:5:0.40:3:3:0.0")
    bg_f = f"[0:v]{','.join(bg_chain)}[bg];" if bg_chain else "[0:v]null[bg];"
    run([
        "ffmpeg", "-y", "-framerate", "30", "-i", os.path.join(src_dir, "f_%04d.jpg"), "-loop", "1", "-i", ref_png,
        "-filter_complex",
        f"{bg_f}[1:v]scale={sz}:{sz}:flags=lanczos,pad={pad}:{pad}:{bd}:{bd}:color=0x1e2026[ref];"
        f"[bg][ref]overlay={ox}:{oy}:shortest=1,fps=30,format=yuv420p[out]",
        "-map", "[out]", "-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-pix_fmt", "yuv420p", out_mp4,
    ])


def export_readme_gif(src_mp4, out_gif):
    pal = out_gif + ".palette.png"
    flt = (
        "[0:v]trim=start=0.2:end=2.5,setpts=PTS-STARTPTS[v0];"
        "[0:v]trim=start=5.2:end=7.0,setpts=PTS-STARTPTS[v1];"
        "[0:v]trim=start=10.0:end=12.4,setpts=PTS-STARTPTS[v2];"
        "[0:v]trim=start=18.6:end=21.4,setpts=PTS-STARTPTS[v3];"
        "[0:v]trim=start=26.5:end=30.3,setpts=PTS-STARTPTS[v4];"
        "[v0][v1][v2][v3][v4]concat=n=5:v=1:a=0,fps=10,scale=600:338:flags=lanczos"
    )
    run(["ffmpeg", "-y", "-i", src_mp4, "-filter_complex", f"{flt},palettegen=max_colors=128:stats_mode=diff", "-update", "1", pal])
    run(["ffmpeg", "-y", "-i", src_mp4, "-i", pal, "-filter_complex", f"{flt}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle", out_gif])
    if os.path.exists(pal):
        os.remove(pal)


def assemble_master(parts_dir, vfx_dir, hero1_ref, hero2_ref, audio_path, tag, width, height, out_mp4, sharpen=False, crf=15, audio_bitrate="256k"):
    tmps = [os.path.join(parts_dir, f"_tmp_{k}_{tag}.mp4") for k in ("c1", "c23", "c4", "c5", "c6", "c6b", "c7")]
    c1, c23, c4, c5, c6, c6b, c7 = tmps

    encode_seq(pick_seg(parts_dir, vfx_dir, ["seg1_hero_dolly", "seg1_night"]), c1, width, height, sharpen=sharpen, crf=crf)
    encode_seq(pick_seg(parts_dir, vfx_dir, ["seg2_3_clay"]), c23, width, height, sharpen=sharpen, crf=crf)
    encode_seq(pick_seg(parts_dir, vfx_dir, ["seg4_assembly"]), c4, width, height, sharpen=sharpen, crf=crf)
    encode_hero_inset(pick_seg(parts_dir, vfx_dir, ["seg5_hero1"]), hero1_ref, c5, width, height, sharpen=sharpen, crf=crf)
    encode_hero_inset(pick_seg(parts_dir, vfx_dir, ["seg6_hero2"]), hero2_ref, c6, width, height, sharpen=sharpen, crf=crf)

    seg4_frames = sorted(glob.glob(os.path.join(parts_dir, "seg4_assembly", "f_*.jpg")))
    encode_still_hold(seg4_frames[-1], 1.00, c6b, width, height, sharpen=sharpen, crf=crf)
    encode_seq(pick_seg(parts_dir, vfx_dir, ["seg7_dive"]), c7, width, height, sharpen=sharpen, crf=crf)

    fc = (
        "[0:v][1:v]xfade=transition=fade:duration=0.55:offset=4.95[v01];"
        "[v01][2:v]xfade=transition=fade:duration=0.15:offset=8.80[v012];"
        "[v012][3:v]xfade=transition=fade:duration=0.15:offset=16.65[v0123];"
        "[v0123][4:v]xfade=transition=fade:duration=0.15:offset=21.50[v01234];"
        "[v01234][5:v]xfade=transition=fade:duration=0.15:offset=26.35[v012345];"
        "[v012345][6:v]xfade=transition=diagtl:duration=0.70:offset=26.65,format=yuv420p[vout]"
    )
    cmd = ["ffmpeg", "-y", "-i", c1, "-i", c23, "-i", c4, "-i", c5, "-i", c6, "-i", c6b, "-i", c7]
    if audio_path and os.path.exists(audio_path):
        cmd += ["-i", audio_path, "-filter_complex", fc, "-map", "[vout]", "-map", "7:a", "-shortest",
                "-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", audio_bitrate, "-movflags", "+faststart", out_mp4]
    else:
        cmd += ["-filter_complex", fc, "-map", "[vout]",
                "-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", out_mp4]
    run(cmd)
    for t in tmps:
        if os.path.exists(t):
            os.remove(t)


def main():
    p = argparse.ArgumentParser(description="Composite 6-segment 3D world breakdown into 1080p, 4K & README GIF.")
    p.add_argument("--project-dir", required=True)
    p.add_argument("--hero1-ref", default=None)
    p.add_argument("--hero2-ref", default=None)
    p.add_argument("--audio", default=None)
    p.add_argument("--out-1080", default=None)
    p.add_argument("--out-4k", default=None)
    p.add_argument("--skip-4k", action="store_true")
    p.add_argument("--gif", default=None, help="Optional output path for 600x338 GitHub README demo GIF")
    args = p.parse_args()

    proj = os.path.abspath(args.project_dir)
    parts, vfx = os.path.join(proj, "video_parts"), os.path.join(proj, "video_parts_vfx")
    audio = os.path.abspath(args.audio) if args.audio else os.path.join(proj, "soundtrack.m4a")
    out_1080 = os.path.abspath(args.out_1080) if args.out_1080 else os.path.join(proj, "world_showcase_1080p.mp4")

    assemble_master(parts, vfx, args.hero1_ref, args.hero2_ref, audio, "1080p", 1920, 1080, out_1080, sharpen=False, crf=16, audio_bitrate="192k")
    print("[1080P READY]", out_1080, flush=True)

    if not args.skip_4k:
        out_4k = os.path.abspath(args.out_4k) if args.out_4k else os.path.join(proj, "world_showcase_4k.mp4")
        assemble_master(parts, vfx, args.hero1_ref, args.hero2_ref, audio, "4k", 3840, 2160, out_4k, sharpen=True, crf=15, audio_bitrate="256k")
        print("[4K READY]", out_4k, flush=True)

    if args.gif:
        out_gif = os.path.abspath(args.gif)
        export_readme_gif(out_1080, out_gif)
        print("[GIF READY]", out_gif, flush=True)


if __name__ == "__main__":
    main()
