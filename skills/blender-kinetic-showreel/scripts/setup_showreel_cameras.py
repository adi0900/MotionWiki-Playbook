"""
Universal 360° Automotive Studio Lighting + Zero-Clipping Multi-Angle Camera Rig
for any Blender 4.2+/5.x hero asset (.blend).

Usage:
  blender -b --factory-startup --python-exit-code 1 -P setup_showreel_cameras.py -- \
    --blend hero.blend --out scene.blend --mode fast-10s --aspect 16:9 --samples 14

Modes:
  topdown  : 109 frames (4.54s @ 24fps), overhead telephoto push-in + dramatic dark-to-lit ramp
  fast-10s : 240 frames (10.0s @ 24fps), 6 fast-cut angles (Low Front, Left, Rear, Right 3/4, Rear-Left 3/4, High Orbit)
  full-25s : 600 frames (25.0s @ 24fps), 7 extended angles (Top-Down opener + all 6 angles)
"""
import argparse
import math
import os
import sys
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--blend", required=True, help="Input .blend containing hero mesh objects")
    p.add_argument("--out", required=True, help="Output .blend ready for Cycles animation render")
    p.add_argument("--mode", choices=["topdown", "fast-10s", "full-25s"], default="fast-10s")
    p.add_argument("--aspect", choices=["16:9", "4:5"], default="16:9")
    p.add_argument("--samples", type=int, default=14)
    p.add_argument("--res-scale", type=float, default=None,
                   help="Optional render scale (default: 0.667 for 16:9 fast 720p->1080p comp, 1.0 for 4:5)")
    return p.parse_args(argv)


def configure_cycles_gpu(scene, samples):
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    picked = False
    for backend in ("OPTIX", "CUDA", "METAL", "HIP", "ONEAPI"):
        try:
            prefs.compute_device_type = backend
            prefs.get_devices()
            devs = [d for d in prefs.devices if d.type == backend]
            if devs:
                for d in prefs.devices:
                    d.use = (d.type == backend)
                scene.cycles.device = "GPU"
                picked = True
                print(f"GPU_BACKEND: {backend} ({len(devs)} device(s))")
                break
        except Exception:
            continue
    if not picked:
        scene.cycles.device = "CPU"
        print("GPU_BACKEND: CPU fallback")

    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.055 if samples <= 18 else 0.03
    scene.cycles.use_denoising = True
    scene.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    scene.cycles.max_bounces = 6
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 3
    scene.cycles.transmission_bounces = 5
    scene.cycles.sample_clamp_indirect = 8.0
    scene.render.use_persistent_data = True


def compute_asset_bounds():
    """Compute world-space bounding box of all MESH objects in the scene."""
    pts = []
    for obj in bpy.data.objects:
        if obj.type == "MESH" and not obj.hide_render:
            for c in obj.bound_box:
                pts.append(obj.matrix_world @ Vector(c))
    if not pts:
        return Vector((0, 0, 0.6)), Vector((1.0, 2.3, 0.65)), [Vector((x, y, z)) for x in (-1, 1) for y in (-2.3, 2.3) for z in (0, 1.3)]
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    zs = [p.z for p in pts]
    bmin = Vector((min(xs), min(ys), min(zs)))
    bmax = Vector((max(xs), max(ys), max(zs)))
    center = (bmin + bmax) * 0.5
    half = (bmax - bmin) * 0.5
    # Add 5% safety pad around bounding box
    pad = half * 1.05
    corners = [
        Vector((center.x + sx * pad.x, center.y + sy * pad.y, center.z + sz * pad.z))
        for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)
    ]
    return center, half, corners


def make_tracked_cam(name, lens, target, col):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = 36.0
    cd.sensor_fit = "HORIZONTAL"
    cd.clip_start = 0.2
    cd.clip_end = 200.0
    co = bpy.data.objects.new(name, cd)
    col.objects.link(co)
    c = co.constraints.new("TRACK_TO")
    c.target = target
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    return co


def key_loc(obj, frame, loc):
    obj.location = loc
    obj.keyframe_insert("location", frame=frame)


def ensure_zero_clipping(scene, corners, total_frames, margin=0.08):
    """
    Mathematically verify all 8 bounding-box corners stay within [margin, 1-margin]
    on every frame. Automatically widens camera lens if any frame exceeds safe margins.
    """
    for attempt in range(8):
        min_u, max_u, min_v, max_v = 1.0, 0.0, 1.0, 0.0
        offending_cams = set()
        for f in range(1, total_frames + 1):
            scene.frame_set(f)
            cam = scene.camera
            for pt in corners:
                co = world_to_camera_view(scene, cam, pt)
                min_u = min(min_u, co.x); max_u = max(max_u, co.x)
                min_v = min(min_v, co.y); max_v = max(max_v, co.y)
                if co.x < margin or co.x > 1.0 - margin or co.y < margin or co.y > 1.0 - margin:
                    offending_cams.add(cam)
        if not offending_cams:
            print(f"FRAMING_VERIFIED: u=[{min_u:.3f}, {max_u:.3f}] v=[{min_v:.3f}, {max_v:.3f}] (0 clipping)")
            return
        for cam in offending_cams:
            cam.data.lens *= 0.88
    print(f"FRAMING_FINAL: u=[{min_u:.3f}, {max_u:.3f}] v=[{min_v:.3f}, {max_v:.3f}]")


def main():
    args = parse_args()
    bpy.ops.wm.open_mainfile(filepath=args.blend)
    scene = bpy.context.scene

    # Remove previous Studio_Rig lights/cameras
    old_rig = bpy.data.collections.get("Studio_Rig")
    if old_rig is not None:
        for o in list(old_rig.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    rig_col = bpy.data.collections.get("Studio_Rig") or bpy.data.collections.new("Studio_Rig")
    if rig_col.name not in scene.collection.children:
        scene.collection.children.link(rig_col)
    scene.timeline_markers.clear()

    center, half, corners = compute_asset_bounds()
    # Normalize camera distances to the hero asset's bounding radius (Porsche 911 ref radius ~2.55m)
    scale = max(0.5, half.length / 2.55)

    configure_cycles_gpu(scene, args.samples)

    if args.aspect == "16:9":
        res_scale = args.res_scale if args.res_scale is not None else 0.6667
        scene.render.resolution_x = int(round(1920 * res_scale))
        scene.render.resolution_y = int(round(1080 * res_scale))
    else:
        res_scale = args.res_scale if args.res_scale is not None else 1.0
        scene.render.resolution_x = int(round(720 * res_scale))
        scene.render.resolution_y = int(round(900 * res_scale))

    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"

    scene.view_settings.view_transform = "AgX"
    try:
        scene.view_settings.look = "AgX - Punchy"
    except TypeError:
        pass
    scene.view_settings.exposure = -0.20

    # Dark reflective world (pure white background is added cleanly in compositor via RGBA alpha!)
    world = scene.world or bpy.data.worlds.new("Studio_World")
    scene.world = world
    wnt = world.node_tree
    wnt.nodes.clear()
    w_out = wnt.nodes.new("ShaderNodeOutputWorld")
    w_bg = wnt.nodes.new("ShaderNodeBackground")
    w_bg.inputs["Color"].default_value = (0.025, 0.030, 0.040, 1.0)
    w_bg.inputs["Strength"].default_value = 0.30
    wnt.links.new(w_bg.outputs["Background"], w_out.inputs["Surface"])

    # 360° Studio Softbox Rig scaled to asset
    def add_area(name, rel_loc, rot_deg, sx, sy, energy, color=(1.0, 1.0, 1.0)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.shape = "RECTANGLE"
        ld.size = sx * scale
        ld.size_y = sy * scale
        ld.energy = energy * (scale ** 2)
        ld.color = color
        lo = bpy.data.objects.new(name, ld)
        lo.location = center + Vector(rel_loc) * scale
        lo.rotation_euler = tuple(math.radians(a) for a in rot_deg)
        rig_col.objects.link(lo)
        return lo, ld

    key_o, key_d = add_area("Light_Overhead_Sweep", (0.0, 2.8, 4.4), (16.0, 0.0, 0.0), 3.6, 2.4, 960.0, (0.98, 0.99, 1.0))
    sl_o, sl_d = add_area("Light_Side_Left",  (-4.2, 0.0, 1.8), (0.0, -64.0, 0.0), 1.5, 6.8, 760.0, (0.90, 0.95, 1.0))
    sr_o, sr_d = add_area("Light_Side_Right", ( 4.2, 0.0, 1.8), (0.0,  64.0, 0.0), 1.5, 6.8, 760.0, (0.90, 0.95, 1.0))
    fr_o, fr_d = add_area("Light_Front_Strip", (0.0, -4.6, 1.6), (-62.0, 0.0, 0.0), 3.8, 1.5, 680.0)
    rr_o, rr_d = add_area("Light_Rear_Strip",  (0.0,  4.6, 2.0), ( 58.0, 0.0, 0.0), 3.8, 1.6, 720.0, (0.94, 0.96, 1.0))
    tp_o, tp_d = add_area("Light_Top_Soft",    (0.0,  0.0, 6.2), (  0.0, 0.0, 0.0), 4.2, 5.6, 280.0, (0.96, 0.98, 1.0))

    target = bpy.data.objects.new("Cam_Target", None)
    target.location = center
    rig_col.objects.link(target)

    def rel(x, y, z):
        return (center.x + x * scale, center.y + y * scale, center.z + z * scale)

    if args.mode == "topdown":
        total_frames = 109
        cd = bpy.data.cameras.new("Cam_01_TopDown")
        cd.lens = 150.0 if args.aspect == "4:5" else 85.0
        cd.sensor_width = 36.0
        cd.sensor_fit = "HORIZONTAL"
        cam1 = bpy.data.objects.new("Cam_01_TopDown", cd)
        rig_col.objects.link(cam1)
        for f, loc, rx in [
            (1,   rel(0.0,  0.40, 17.6), math.radians(-1.3)),
            (55,  rel(0.0,  0.05, 16.9), math.radians(0.2)),
            (109, rel(0.0, -0.40, 16.2), math.radians(2.2)),
        ]:
            cam1.location = loc
            cam1.rotation_euler = (rx, 0.0, 0.0)
            cam1.keyframe_insert("location", frame=f)
            cam1.keyframe_insert("rotation_euler", frame=f)
        # Dramatic dark-to-lit ramp
        for f, mult, ky in [(1, 0.01, 3.2), (28, 0.02, 3.0), (45, 0.35, 1.4), (72, 0.78, -0.8), (109, 1.15, -2.8)]:
            for ld, base_e in [(key_d, 960), (sl_d, 760), (sr_d, 760), (fr_d, 680), (rr_d, 720), (tp_d, 280)]:
                ld.energy = base_e * mult * (scale ** 2)
                ld.keyframe_insert("energy", frame=f)
            key_o.location.y = center.y + ky * scale
            key_o.keyframe_insert("location", index=1, frame=f)
        scene.camera = cam1

    elif args.mode == "fast-10s":
        total_frames = 240
        lens_main = 45.0 if args.aspect == "16:9" else 56.0
        cam1 = make_tracked_cam("Cam_01_LowFront", lens_main, target, rig_col)
        key_loc(cam1, 1,  rel(-2.3, -8.4, 0.25))
        key_loc(cam1, 18, rel( 0.0, -8.0, 0.18))
        key_loc(cam1, 36, rel( 2.3, -8.2, 0.30))

        cam2 = make_tracked_cam("Cam_02_LeftSide", lens_main, target, rig_col)
        key_loc(cam2, 37, rel(-10.4, -0.9, 0.45))
        key_loc(cam2, 72, rel(-10.2,  0.9, 0.55))

        cam3 = make_tracked_cam("Cam_03_Rear", lens_main, target, rig_col)
        key_loc(cam3, 73,  rel(-0.9, 8.4, 0.35))
        key_loc(cam3, 108, rel( 0.9, 8.2, 1.55))

        cam4 = make_tracked_cam("Cam_04_RightOrbit", lens_main, target, rig_col)
        for f, deg, r, z in [(109, 82, 10.4, 0.6), (126, 52, 9.8, 1.1), (144, 24, 9.2, 1.5)]:
            rad = math.radians(deg)
            key_loc(cam4, f, rel(math.sin(rad) * r, -math.cos(rad) * r, z))

        cam5 = make_tracked_cam("Cam_05_RearLeft3Q", lens_main, target, rig_col)
        for f, deg, r, z in [(145, 132, 10.4, 2.7), (162, 146, 10.0, 1.45), (180, 162, 9.4, 0.75)]:
            rad = math.radians(deg)
            key_loc(cam5, f, rel(-math.sin(rad) * r, -math.cos(rad) * r, z))

        cam6 = make_tracked_cam("Cam_06_HighOrbit", 42.0 if args.aspect == "16:9" else 52.0, target, rig_col)
        for f, pt in [(181, (8.2, -6.6, 8.2)), (205, (7.4, -2.8, 10.4)), (225, (5.0, 0.0, 12.0)), (240, (2.6, 0.0, 12.8))]:
            key_loc(cam6, f, rel(*pt))

        for f, mname, cam in [
            (1, "M_01_LowFront", cam1), (37, "M_02_LeftSide", cam2), (73, "M_03_Rear", cam3),
            (109, "M_04_RightOrbit", cam4), (145, "M_05_RearLeft3Q", cam5), (181, "M_06_HighOrbit", cam6),
        ]:
            m = scene.timeline_markers.new(mname, frame=f)
            m.camera = cam

        for f, sy in [(1, 3.0), (60, -2.6), (120, 2.8), (180, -2.6), (240, 2.6)]:
            key_o.location.y = center.y + sy * scale
            key_o.keyframe_insert("location", index=1, frame=f)
        scene.camera = cam1

    else:  # full-25s (600 frames, 7 angles)
        total_frames = 600
        lens_main = 45.0 if args.aspect == "16:9" else 58.0
        cd1 = bpy.data.cameras.new("Cam_01_TopDown")
        cd1.lens = 150.0 if args.aspect == "4:5" else 85.0
        cd1.sensor_width = 36.0
        cd1.sensor_fit = "HORIZONTAL"
        cam1 = bpy.data.objects.new("Cam_01_TopDown", cd1)
        rig_col.objects.link(cam1)
        for f, loc, rx in [(1, rel(0, 0.4, 17.6), math.radians(-1.3)), (88, rel(0, -0.35, 16.4), math.radians(2.0))]:
            cam1.location = loc; cam1.rotation_euler = (rx, 0, 0)
            cam1.keyframe_insert("location", frame=f); cam1.keyframe_insert("rotation_euler", frame=f)

        cam2 = make_tracked_cam("Cam_02_LeftSide", lens_main, target, rig_col)
        key_loc(cam2, 89, rel(-10.4, -1.2, 0.45)); key_loc(cam2, 172, rel(-10.2, 1.2, 0.55))

        cam3 = make_tracked_cam("Cam_03_Rear", lens_main, target, rig_col)
        key_loc(cam3, 173, rel(-0.9, 8.4, 0.35)); key_loc(cam3, 256, rel(0.9, 8.2, 1.55))

        cam4 = make_tracked_cam("Cam_04_LowFront", lens_main, target, rig_col)
        key_loc(cam4, 257, rel(-2.3, -8.4, 0.25)); key_loc(cam4, 340, rel(2.3, -8.2, 0.35))

        cam5 = make_tracked_cam("Cam_05_RightOrbit", lens_main, target, rig_col)
        for f, deg, r, z in [(341, 88, 10.6, 0.55), (384, 54, 9.8, 1.15), (424, 22, 9.0, 1.55)]:
            rad = math.radians(deg)
            key_loc(cam5, f, rel(math.sin(rad) * r, -math.cos(rad) * r, z))

        cam6 = make_tracked_cam("Cam_06_RearLeft3Q", lens_main, target, rig_col)
        for f, deg, r, z in [(425, 134, 10.4, 2.7), (466, 148, 9.8, 1.45), (508, 164, 9.2, 0.75)]:
            rad = math.radians(deg)
            key_loc(cam6, f, rel(-math.sin(rad) * r, -math.cos(rad) * r, z))

        cam7 = make_tracked_cam("Cam_07_HighOrbit", 42.0 if args.aspect == "16:9" else 65.0, target, rig_col)
        for f, pt in [(509, (7.6, -6.2, 7.6)), (555, (4.8, -2.0, 11.2)), (600, (2.2, 0.0, 12.8))]:
            key_loc(cam7, f, rel(*pt))

        for f, mname, cam in [
            (1, "M_01_TopDown", cam1), (89, "M_02_LeftSide", cam2), (173, "M_03_Rear", cam3),
            (257, "M_04_LowFront", cam4), (341, "M_05_RightOrbit", cam5),
            (425, "M_06_RearLeft3Q", cam6), (509, "M_07_HighOrbit", cam7),
        ]:
            m = scene.timeline_markers.new(mname, frame=f)
            m.camera = cam

        for f, mult in [(1, 0.01), (28, 0.02), (52, 0.55), (78, 1.0), (600, 1.05)]:
            for ld, base_e in [(key_d, 960), (sl_d, 760), (sr_d, 760), (fr_d, 680), (rr_d, 720), (tp_d, 280)]:
                ld.energy = base_e * mult * (scale ** 2)
                ld.keyframe_insert("energy", frame=f)
        for f, sy in [(1, 3.2), (88, -2.6), (172, 2.8), (256, -2.6), (340, 2.8), (424, -2.6), (508, 2.8), (600, -2.8)]:
            key_o.location.y = center.y + sy * scale
            key_o.keyframe_insert("location", index=1, frame=f)
        scene.camera = cam1

    scene.frame_start = 1
    scene.frame_end = total_frames
    ensure_zero_clipping(scene, corners, total_frames, margin=0.08)

    scene.frame_set(1)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=args.out)
    print(f"SHOWREEL_SCENE_OK: {args.out} ({total_frames} frames, {args.aspect}, {args.mode})")


if __name__ == "__main__":
    main()
