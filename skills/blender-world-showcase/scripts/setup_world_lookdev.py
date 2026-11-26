#!/usr/bin/env python3
"""Universal Blender 4.2+/5.3+ EEVEE Look-Dev & Dynamic Camera Engine.
Applies physics-safe lighting, sky, dielectric surfaces, and bounded atmosphere across
5 versatile world mood presets:
  - arcane_zaun     : Deep cobalt night sky slit + molten amber pools + jade canyon mist
  - cyberpunk_neon  : Midnight indigo sky slit + magenta/cyan neon pools + subtle street mist
  - golden_hour     : Warm sunset sun + rich sky + bounded local golden mist cube (zero black-sky bug!)
  - moonlit_fog     : Silver-blue moonlight + foggy lantern pools + cool atmospheric depth
  - sunlit_sky      : Crisp azure daylight sky + angled directional sun + soft sky bounce fill
"""
import argparse
import math
import os
import sys
import bpy
import bmesh
from mathutils import Vector, Quaternion


def ease_in_out(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def aim_cam(cam_obj, loc, target, lens=24.0, roll_deg=0.0):
    cam_obj.location = Vector(loc)
    cam_obj.data.lens = lens
    q = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y")
    if abs(roll_deg) > 1e-4:
        q = q @ Quaternion((0.0, 0.0, 1.0), math.radians(roll_deg))
    cam_obj.rotation_euler = q.to_euler()


def ensure_local_mist_box(color, density=0.0045):
    """Create a bounded local mist cube for bright-sky worlds (prevents infinite World
    VolumeScatter from absorbing sky rays to black in Blender 5.3 EEVEE!)."""
    old = bpy.data.objects.get("_LocalMistBox")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(18.0, 56.0, 14.0), verts=bm.verts)
    me = bpy.data.meshes.new("_LocalMistMesh")
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new("_LocalMistBox", me)
    obj.location = (0.0, 22.0, 6.5)
    mat = bpy.data.materials.new("_Mat_LocalMist")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumeScatter")
    vol.inputs["Color"].default_value = color
    vol.inputs["Density"].default_value = density
    vol.inputs["Anisotropy"].default_value = 0.62
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    obj.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def apply_mood_lookdev(mood="arcane_zaun", samples=20):
    scene = bpy.context.scene
    world = scene.world or bpy.data.worlds.new("World_Lookdev")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")

    # Clear previous ENV_Lighting & local mist
    lcol = bpy.data.collections.get("ENV_Lighting")
    if lcol:
        for o in list(lcol.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    else:
        lcol = bpy.data.collections.new("ENV_Lighting")
        scene.collection.children.link(lcol)
    old_mist = bpy.data.objects.get("_LocalMistBox")
    if old_mist:
        bpy.data.objects.remove(old_mist, do_unlink=True)

    for obj in bpy.data.objects:
        if obj.type == "LIGHT":
            obj.data.use_shadow = False
            if hasattr(obj.data, "specular_factor"):
                obj.data.specular_factor = 0.0

    def add_sun(name, rot_deg, energy, color, angle_deg=3.5):
        ld = bpy.data.lights.new(name, type="SUN")
        ld.energy, ld.color, ld.angle = energy, color, math.radians(angle_deg)
        lo = bpy.data.objects.new(name, ld)
        lo.rotation_euler = tuple(math.radians(a) for a in rot_deg)
        lcol.objects.link(lo)

    def add_point(name, loc, energy, color, radius=0.45, vol_fac=0.04):
        ld = bpy.data.lights.new(name, type="POINT")
        ld.energy, ld.color, ld.shadow_soft_size, ld.use_shadow = energy, color, radius, False
        if hasattr(ld, "specular_factor"):
            ld.specular_factor = 0.0
        if hasattr(ld, "volume_factor"):
            ld.volume_factor = vol_fac
        lo = bpy.data.objects.new(name, ld)
        lo.location = loc
        lcol.objects.link(lo)

    def add_spot(name, loc, rot_deg, energy, color, spot_deg=72.0, vol_fac=0.14):
        ld = bpy.data.lights.new(name, type="SPOT")
        ld.energy, ld.color = energy, color
        ld.spot_size, ld.spot_blend, ld.shadow_soft_size, ld.use_shadow = math.radians(spot_deg), 0.72, 0.28, True
        if hasattr(ld, "specular_factor"):
            ld.specular_factor = 0.0
        if hasattr(ld, "volume_factor"):
            ld.volume_factor = vol_fac
        lo = bpy.data.objects.new(name, ld)
        lo.location = loc
        lo.rotation_euler = tuple(math.radians(a) for a in rot_deg)
        lcol.objects.link(lo)

    if mood in ("golden_hour", "sunlit_sky"):
        # Bright sky (NEVER infinite world VolumeScatter -> keeps sky vivid!)
        bg = nt.nodes.new("ShaderNodeBackground")
        if mood == "golden_hour":
            bg.inputs["Color"].default_value = (0.95, 0.48, 0.22, 1.0)
            bg.inputs["Strength"].default_value = 0.95
            add_sun("Sun_Golden", (68, 12, -38), 5.2, (1.0, 0.68, 0.36), angle_deg=4.5)
            add_sun("Sky_Fill", (35, -18, 145), 0.85, (0.48, 0.64, 0.95), angle_deg=30.0)
            ensure_local_mist_box((1.0, 0.76, 0.50, 1.0), density=0.0038)
            scene.view_settings.exposure = -0.42
        else:
            bg.inputs["Color"].default_value = (0.28, 0.58, 0.98, 1.0)
            bg.inputs["Strength"].default_value = 1.15
            add_sun("Sun_Day", (46, 16, -28), 5.8, (1.0, 0.96, 0.90), angle_deg=2.2)
            add_sun("Sky_Bounce", (55, -20, 150), 0.90, (0.62, 0.80, 1.0), angle_deg=35.0)
            scene.view_settings.exposure = -0.50
        nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    else:
        # Night sky slit (Light Path -> Is Camera Ray) + subtle atmospheric scatter
        lp = nt.nodes.new("ShaderNodeLightPath")
        bg_sky = nt.nodes.new("ShaderNodeBackground")
        bg_dark = nt.nodes.new("ShaderNodeBackground")
        sky_colors = {
            "arcane_zaun":    ((0.045, 0.115, 0.295, 1.0), (0.004, 0.010, 0.009, 1.0), (0.38, 0.58, 0.54, 1.0)),
            "cyberpunk_neon": ((0.035, 0.055, 0.195, 1.0), (0.006, 0.008, 0.016, 1.0), (0.42, 0.56, 0.78, 1.0)),
            "moonlit_fog":    ((0.065, 0.110, 0.220, 1.0), (0.010, 0.014, 0.024, 1.0), (0.55, 0.68, 0.85, 1.0)),
        }
        c_sky, c_dark, c_vol = sky_colors[mood]
        bg_sky.inputs["Color"].default_value = c_sky
        bg_sky.inputs["Strength"].default_value = 0.55
        bg_dark.inputs["Color"].default_value = c_dark
        bg_dark.inputs["Strength"].default_value = 0.05
        mix_sh = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(lp.outputs["Is Camera Ray"], mix_sh.inputs["Fac"])
        nt.links.new(bg_dark.outputs["Background"], mix_sh.inputs[1])
        nt.links.new(bg_sky.outputs["Background"], mix_sh.inputs[2])
        nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])

        vol = nt.nodes.new("ShaderNodeVolumeScatter")
        vol.inputs["Color"].default_value = c_vol
        vol.inputs["Density"].default_value = 0.0055 if mood != "moonlit_fog" else 0.0085
        vol.inputs["Anisotropy"].default_value = 0.55
        nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])

        # Boost existing emissive accents slightly for crisp night reflections
        for mat in bpy.data.materials:
            if not mat.use_nodes:
                continue
            for n in mat.node_tree.nodes:
                if n.type == "EMISSION" and n.inputs["Strength"].default_value >= 1.0:
                    n.inputs["Strength"].default_value = min(n.inputs["Strength"].default_value * 1.5, 26.0)
                elif n.type == "BSDF_PRINCIPLED" and "Emission Strength" in n.inputs and n.inputs["Emission Strength"].default_value >= 0.8:
                    n.inputs["Emission Strength"].default_value = min(n.inputs["Emission Strength"].default_value * 1.5, 24.0)

        if mood == "arcane_zaun":
            c_a, c_b = (1.00, 0.48, 0.12), (0.28, 0.88, 0.64)
        elif mood == "cyberpunk_neon":
            c_a, c_b = (1.00, 0.20, 0.60), (0.06, 0.88, 1.00)
        else:
            c_a, c_b = (1.00, 0.72, 0.36), (0.52, 0.74, 1.00)
            add_sun("Moon_Key", (54, 15, -35), 0.75, (0.62, 0.78, 1.0), angle_deg=6.0)

        for nm, loc, rot, eng, col, deg, vf in [
            ("Spot_Fore", (0.0, 3.0, 6.2), (0, 0, 0), 1450.0, (0.95, 0.84, 0.72), 78.0, 0.10),
            ("Spot_Hero", (-1.15, 6.2, 6.8), (6, -14, 0), 1750.0, c_a, 68.0, 0.12),
            ("Spot_Mid1", (1.05, 14.5, 7.8), (0, 10, 0), 1250.0, c_b, 74.0, 0.12),
            ("Spot_Mid2", (-1.00, 23.5, 7.6), (0, -10, 0), 1400.0, c_a, 70.0, 0.12),
            ("Spot_Far",  (0.00, 36.0, 9.2), (0, 0, 0), 1500.0, c_b, 78.0, 0.16),
        ]:
            add_spot(nm, loc, rot, eng, col, spot_deg=deg, vol_fac=vf)
        for nm, loc, eng, col in [
            ("Pool_Fore_A", (-1.55, 6.2, 2.2), 380.0, c_a),
            ("Pool_Fore_B", (1.50, 7.2, 2.4), 190.0, c_b),
            ("Pool_Mid_A",  (-1.55, 12.0, 2.4), 240.0, c_a),
            ("Pool_Mid_B",  (1.45, 18.0, 4.8), 240.0, c_b),
            ("Pool_Back_A", (-1.50, 25.5, 2.8), 260.0, c_a),
            ("Pool_Horizon",(0.00, 42.0, 1.8), 520.0, c_b),
        ]:
            add_point(nm, loc, eng, col, vol_fac=0.04)
        scene.view_settings.exposure = -0.05

    # Guarantee dielectric ground material never turns Vantablack metallic
    for mat_name in ("Mat_World_Ground", "Mat_Wet_Cyber_Asphalt"):
        m = bpy.data.materials.get(mat_name)
        if m and m.use_nodes:
            bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if bsdf and bsdf.inputs["Metallic"].default_value < 0.5:
                bsdf.inputs["Metallic"].default_value = 0.0

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 94
    if hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = samples
    if hasattr(scene.eevee, "use_raytracing"):
        scene.eevee.use_raytracing = True
    if hasattr(scene.eevee, "ray_tracing_options"):
        rto = scene.eevee.ray_tracing_options
        if hasattr(rto, "screen_trace_quality"):
            rto.screen_trace_quality = 1.0
        if hasattr(rto, "trace_max_roughness"):
            rto.trace_max_roughness = 0.55
    scene.view_settings.view_transform = "AgX"
    try:
        scene.view_settings.look = "AgX - Punchy"
    except Exception:
        pass


def seg1_camera_pose(f, n_frames=165):
    t = f / (n_frames - 1)
    y = -0.60 + 11.55 * (0.35 * t + 0.65 * ease_in_out(t))
    if t < 0.36:
        u = ease_in_out(t / 0.36)
        return (-0.45 + 0.72 * u, y, 0.56 + 0.42 * u), (0.32 * math.sin(u * math.pi), y + 18.0, 1.65 + 1.85 * u), 22.0, -1.8 * math.sin(u * math.pi)
    elif t < 0.76:
        u = ease_in_out((t - 0.36) / 0.40)
        return (0.27 - 0.72 * u, y, 0.98 + 2.45 * math.sin(u * math.pi * 0.62)), (-0.25 * math.sin(u * math.pi), y + 18.0, 3.50 + 1.25 * math.sin(u * math.pi)), 22.0 + 2.5 * u, 1.6 * math.sin(u * math.pi)
    u = ease_in_out((t - 0.76) / 0.24)
    z0 = 0.98 + 2.45 * math.sin(math.pi * 0.62)
    return (-0.45 * (1.0 - u) - 0.08 * u, y, z0 * (1.0 - u) + 1.54 * u), (0.0, y + 18.0, 3.50 * (1.0 - u) + 2.25 * u), 24.5 * (1.0 - u) + 28.0 * u, 0.0


def seg7_camera_pose(f, n_frames=180):
    if f < 24:
        t = f / 24.0
        return Vector((-0.20, -6.6 + 0.6 * t, 23.3 - 0.5 * t)), Vector((0.0, 22.5, 2.0)), 34.0, 0.0
    elif f < 102:
        u = ease_in_out((f - 24) / 78.0)
        p0, p1 = Vector((-0.20, -6.0, 22.8)), Vector((-0.38, 10.5, 0.88))
        loc = p0.lerp(p1, u)
        loc.x += 1.05 * math.sin(u * math.pi)
        loc.z = p0.z * ((1.0 - u) ** 1.85) + p1.z * (1.0 - (1.0 - u) ** 1.85)
        return loc, Vector((0.0, 22.5, 2.0)).lerp(Vector((0.15, 28.5, 2.5)), u), 34.0 - 12.0 * u, -4.2 * math.sin(u * math.pi)
    u = ease_in_out((f - 102) / 77.0)
    y = 10.5 + 19.5 * u
    return Vector((-0.38 + 0.78 * math.sin(u * math.pi * 1.15), y, 0.88 + 0.35 * math.sin(u * math.pi * 0.5) + 1.85 * (u ** 2.2))), Vector((-0.20 * math.sin(u * math.pi), y + 18.0, 2.30 + 3.40 * (u ** 1.6))), 22.0, 2.2 * math.sin(u * math.pi)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(description="Apply 5-mood Blender 5.3 EEVEE look-dev & render hero dolly / banked dive.")
    p.add_argument("--project-dir", required=True)
    p.add_argument("--mode", required=True, choices=["seg1_hero_dolly", "seg7_dive", "save-only"])
    p.add_argument("--blend", default=None)
    p.add_argument("--mood", default="arcane_zaun", choices=["arcane_zaun", "cyberpunk_neon", "golden_hour", "moonlit_fog", "sunlit_sky"])
    p.add_argument("--samples", type=int, default=20)
    p.add_argument("--single-frame", type=int, default=None)
    p.add_argument("--out-dir", default=None)
    args = p.parse_args(argv)

    proj = os.path.abspath(args.project_dir)
    master = os.path.abspath(args.blend) if args.blend else os.path.join(proj, "world_master.blend")
    if not os.path.exists(master):
        for alt in ("alley_master.blend", "cyberpunk_alley_master.blend"):
            cand = os.path.join(proj, alt)
            if os.path.exists(cand):
                master = cand
                break

    bpy.ops.wm.open_mainfile(filepath=master)
    apply_mood_lookdev(mood=args.mood, samples=args.samples)

    if args.mode == "save-only":
        out_b = os.path.join(proj, f"world_master_{args.mood}.blend")
        bpy.ops.wm.save_as_mainfile(filepath=out_b)
        print(f"[SAVED LOOKDEV] {out_b}")
        return

    scene = bpy.context.scene
    cam = scene.camera
    n_frames = 165 if args.mode == "seg1_hero_dolly" else 180
    pose_fn = seg1_camera_pose if args.mode == "seg1_hero_dolly" else seg7_camera_pose
    out_dir = os.path.abspath(args.out_dir) if args.out_dir else os.path.join(proj, "video_parts", args.mode)
    os.makedirs(out_dir, exist_ok=True)

    for f in ([args.single_frame] if args.single_frame is not None else range(n_frames)):
        loc, tgt, lens, roll = pose_fn(f, n_frames)
        aim_cam(cam, loc, tgt, lens=lens, roll_deg=roll)
        scene.render.filepath = os.path.join(out_dir, f"f_{f:04d}.jpg")
        bpy.ops.render.render(write_still=True)
    print(f"[DONE LOOKDEV {args.mood}] {args.mode} -> {out_dir}")


if __name__ == "__main__":
    main()
