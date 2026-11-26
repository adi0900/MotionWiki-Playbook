#!/usr/bin/env python3
"""Universal 6-Segment Blender 4.2+/5.3+ Breakdown Film Renderer:
  --mode seg1_hero_dolly : 165f Lit world street dolly
  --mode seg2_3_clay     : 120f Final->Clay dissolve + crane pull-up on real 3D Blender grid
  --mode seg4_assembly   : 240f Orange-to-Clay POP_* collection pop-in assembly timelapse
  --mode seg5_hero1      : 150f Hero #1 right-framed 4-stage build + AgX shaded reveal
  --mode seg6_hero2      : 150f Hero #2 right-framed 4-stage build + AgX shaded reveal
  --mode seg7_dive       : 180f Overhead hold (matches clay wipe) + crane dive into street
"""
import argparse
import glob
import math
import os
import sys
import bpy
import bmesh
from mathutils import Vector


def ease_in_out(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def ease_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def aim_cam(cam_obj, loc, target, lens=28.0):
    cam_obj.location = Vector(loc)
    cam_obj.data.lens = lens
    cam_obj.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


def make_clay_mat(name="Mat_Viewport_Clay", color=(0.52, 0.53, 0.55, 1.0)):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.68
    bsdf.inputs["Metallic"].default_value = 0.0
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.9
    ao.inputs["Color"].default_value = color
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 0.55
    mix.inputs[6].default_value = color
    nt.links.new(ao.outputs["AO"], mix.inputs[7])
    nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_orange_mat(name="Mat_Viewport_Orange"):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.94, 0.48, 0.14, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.55
    bsdf.inputs["Emission Color"].default_value = (0.98, 0.48, 0.10, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 0.25
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def setup_clay_viewport(add_grid=True):
    scene = bpy.context.scene
    scene.use_nodes = False
    for nm in ("ENV_Lighting",):
        c = bpy.data.collections.get(nm)
        if c:
            c.hide_render = True
    for nm in ("_LocalMistBox", "Backdrop_Tower_L", "Backdrop_Tower_R", "Backdrop_Bridge", "Backdrop_Glow_L", "Backdrop_Glow_R"):
        o = bpy.data.objects.get(nm)
        if o:
            o.hide_render = True

    world = bpy.data.worlds.new("_ClayWorld")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.048, 0.050, 0.054, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    vcol = bpy.data.collections.new("_ClayLights")
    scene.collection.children.link(vcol)
    for nm, rot, eng, col in [
        ("_SunKey",  (42, 18, -32), 2.8, (1.0, 0.99, 0.98)),
        ("_SunFill", (65, -20, 145), 1.1, (0.88, 0.92, 1.0)),
        ("_SunRim",  (30, 0, 180),  0.7, (0.95, 0.96, 1.0)),
    ]:
        ld = bpy.data.lights.new(nm, type="SUN")
        ld.energy, ld.color, ld.angle = eng, col, math.radians(12.0)
        lo = bpy.data.objects.new(nm, ld)
        lo.rotation_euler = tuple(math.radians(a) for a in rot)
        vcol.objects.link(lo)

    if add_grid:
        gcol = bpy.data.collections.new("_ViewportGrid")
        scene.collection.children.link(gcol)

        def unlit(nm, rgba):
            m = bpy.data.materials.new(nm)
            m.use_nodes = True
            ntu = m.node_tree
            ntu.nodes.clear()
            o = ntu.nodes.new("ShaderNodeOutputMaterial")
            e = ntu.nodes.new("ShaderNodeEmission")
            e.inputs["Color"].default_value = rgba
            e.inputs["Strength"].default_value = 1.0
            ntu.links.new(e.outputs["Emission"], o.inputs["Surface"])
            return m

        m_grid, m_x, m_y = unlit("_MatGrid", (0.12, 0.125, 0.132, 1.0)), unlit("_MatAxisX", (0.68, 0.16, 0.18, 1.0)), unlit("_MatAxisY", (0.24, 0.58, 0.18, 1.0))
        bm = bmesh.new()
        span, step, w, z = 70.0, 4.0, 0.032, -0.19
        for i in range(-18, 22):
            v = i * step
            if abs(v) < 0.01:
                continue
            bm.faces.new([bm.verts.new((v - w, -20, z)), bm.verts.new((v + w, -20, z)), bm.verts.new((v + w, 90, z)), bm.verts.new((v - w, 90, z))])
            bm.faces.new([bm.verts.new((-span, v - w, z)), bm.verts.new((span, v - w, z)), bm.verts.new((span, v + w, z)), bm.verts.new((-span, v + w, z))])
        me = bpy.data.meshes.new("_GridMesh")
        bm.to_mesh(me)
        bm.free()
        gobj = bpy.data.objects.new("_ViewportGridLines", me)
        gobj.data.materials.append(m_grid)
        gcol.objects.link(gobj)

        for nm, pts, mat in [
            ("_AxisX", [(-span, -0.04, z + 0.004), (span, -0.04, z + 0.004), (span, 0.04, z + 0.004), (-span, 0.04, z + 0.004)], m_x),
            ("_AxisY", [(-0.04, -20, z + 0.004), (0.04, -20, z + 0.004), (0.04, 90, z + 0.004), (-0.04, 90, z + 0.004)], m_y),
        ]:
            b = bmesh.new()
            b.faces.new([b.verts.new(p) for p in pts])
            m = bpy.data.meshes.new(nm)
            b.to_mesh(m)
            b.free()
            o = bpy.data.objects.new(nm, m)
            o.data.materials.append(mat)
            gcol.objects.link(o)

    mat_clay = make_clay_mat()
    for obj in bpy.data.objects:
        if obj.type in ("MESH", "CURVE") and not obj.name.startswith("_"):
            obj.data = obj.data.copy()
            obj.data.materials.clear()
            obj.data.materials.append(mat_clay)

    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = 0.0
    if hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 16
    if hasattr(scene.eevee, "use_raytracing"):
        scene.eevee.use_raytracing = False
    return mat_clay


def configure_eevee(samples=24, raytrace=True):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 94
    if hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = samples
    if hasattr(scene.eevee, "use_raytracing"):
        scene.eevee.use_raytracing = raytrace


def render_hero_timelapse(assets_dir, asset_id, out_dir, azim_start=-36.0, azim_end=-14.0,
                          elev_deg=15.0, dist_mult=0.84, single_frame=None, samples=24):
    blend_path = os.path.join(assets_dir, f"{asset_id}.blend")
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene
    col = bpy.data.collections.get(f"ASSET_{asset_id}") or [c for c in bpy.data.collections if not c.name.startswith("_")][0]
    objs = [o for o in col.all_objects if o.type in ("MESH", "CURVE")]
    orig_mats = {o.name: list(o.data.materials) for o in objs}

    bpy.context.view_layer.update()
    mins, maxs = Vector((1e9, 1e9, 1e9)), Vector((-1e9, -1e9, -1e9))
    for o in objs:
        for corner in o.bound_box:
            wc = o.matrix_world @ Vector(corner)
            mins.x, mins.y, mins.z = min(mins.x, wc.x), min(mins.y, wc.y), min(mins.z, wc.z)
            maxs.x, maxs.y, maxs.z = max(maxs.x, wc.x), max(maxs.y, wc.y), max(maxs.z, wc.z)
    center = (mins + maxs) * 0.5
    size = maxs - mins
    horiz_r = max(0.3, math.hypot(size.x * 0.5, size.y * 0.5))
    radius = max(0.5, size.length * 0.5)
    el_rad = math.radians(elev_deg)
    tan_v, tan_h = 10.125 / 50.0, 18.0 / 50.0
    dist = max((size.z * 0.5 * math.cos(el_rad) + horiz_r * math.sin(el_rad)) / (0.76 * tan_v) + horiz_r * 0.85,
               horiz_r / (0.54 * tan_h) + horiz_r * 0.85) * dist_mult

    world = bpy.data.worlds.new("_HeroWorld")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.044, 0.047, 0.052, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    scol = bpy.data.collections.new("_HeroStudio")
    scene.collection.children.link(scol)
    for nm, off, eng, sz, col_rgb in [
        ("_HKey", (-2.0, -2.4, 1.9), 240.0, 1.6, (1.0, 0.97, 0.94)),
        ("_HFill", (2.4, -1.4, 1.1), 110.0, 1.9, (0.80, 0.90, 1.0)),
        ("_HRim", (0.8, 2.6, 1.8), 165.0, 1.4, (0.85, 0.94, 1.0)),
    ]:
        ld = bpy.data.lights.new(nm, type="AREA")
        ld.energy, ld.size, ld.color = eng * (radius ** 1.6), radius * sz, col_rgb
        lo = bpy.data.objects.new(nm, ld)
        lo.location = center + Vector(off) * radius
        lo.rotation_euler = (center - lo.location).to_track_quat("-Z", "Y").to_euler()
        scol.objects.link(lo)

    cd = bpy.data.cameras.new("_HeroCam")
    cd.lens = 50.0
    cam = bpy.data.objects.new("_HeroCam", cd)
    scol.objects.link(cam)
    scene.camera = cam

    mat_clay, mat_orange = make_clay_mat("_HeroClay", (0.56, 0.57, 0.59, 1.0)), make_orange_mat("_HeroOrange")
    stage_starts = {1: 0, 2: 28, 3: 56, 4: 84}
    configure_eevee(samples=samples, raytrace=False)
    os.makedirs(out_dir, exist_ok=True)
    n_frames = 150

    for f in ([single_frame] if single_frame is not None else range(n_frames)):
        t = f / (n_frames - 1)
        az = math.radians(azim_start + (azim_end - azim_start) * t)
        cam_pos = center + Vector((dist * math.cos(el_rad) * math.sin(az), -dist * math.cos(el_rad) * math.cos(az), dist * math.sin(el_rad)))
        cam_right = (center - cam_pos).normalized().cross(Vector((0.0, 0.0, 1.0))).normalized()
        aim_cam(cam, cam_pos, center - cam_right * (0.19 * dist * tan_h), lens=50.0)

        if f >= 108:
            scene.view_settings.view_transform = "AgX"
            try:
                scene.view_settings.look = "AgX - Punchy"
            except Exception:
                pass
            bg.inputs["Strength"].default_value = 0.55
            for o in objs:
                o.hide_render = False
                o.data.materials.clear()
                for m in orig_mats[o.name]:
                    o.data.materials.append(m)
        else:
            scene.view_settings.view_transform = "Standard"
            bg.inputs["Strength"].default_value = 1.0
            for o in objs:
                sf = stage_starts[max(1, min(4, int(o.get("build_stage", 1))))]
                if f < sf:
                    o.hide_render = True
                else:
                    o.hide_render = False
                    o.data.materials.clear()
                    o.data.materials.append(mat_orange if (f - sf) < 12 else mat_clay)
        scene.render.filepath = os.path.join(out_dir, f"f_{f:04d}.jpg")
        bpy.ops.render.render(write_still=True)
    print(f"[DONE HERO] {asset_id} -> {out_dir}")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(description="Render 6-segment Blender breakdown showcase sequences.")
    p.add_argument("--project-dir", required=True)
    p.add_argument("--mode", required=True, choices=["seg1_hero_dolly", "seg2_3_clay", "seg4_assembly", "seg5_hero1", "seg6_hero2", "seg7_dive"])
    p.add_argument("--blend", default=None)
    p.add_argument("--hero1", default=None, help="Hero #1 asset ID (defaults to first .blend in assets/)")
    p.add_argument("--hero2", default=None, help="Hero #2 asset ID (defaults to second .blend in assets/)")
    p.add_argument("--azim-start", type=float, default=None)
    p.add_argument("--azim-end", type=float, default=None)
    p.add_argument("--elev", type=float, default=None)
    p.add_argument("--dist-mult", type=float, default=None)
    p.add_argument("--samples", type=int, default=None)
    p.add_argument("--single-frame", type=int, default=None)
    p.add_argument("--out-dir", default=None)
    args = p.parse_args(argv)

    proj = os.path.abspath(args.project_dir)
    assets_dir = os.path.join(proj, "assets")
    master = os.path.abspath(args.blend) if args.blend else os.path.join(proj, "world_master.blend")
    if not os.path.exists(master):
        for alt in ("alley_master.blend", "cyberpunk_alley_master.blend"):
            if os.path.exists(os.path.join(proj, alt)):
                master = os.path.join(proj, alt)
                break
    out_dir = os.path.abspath(args.out_dir) if args.out_dir else os.path.join(proj, "video_parts", args.mode)
    os.makedirs(out_dir, exist_ok=True)

    avail = [os.path.splitext(os.path.basename(b))[0] for b in sorted(glob.glob(os.path.join(assets_dir, "*.blend")))]

    if args.mode == "seg5_hero1":
        hid = args.hero1 or (avail[0] if avail else "hero1")
        render_hero_timelapse(assets_dir, hid, out_dir,
                              azim_start=args.azim_start if args.azim_start is not None else -36.0,
                              azim_end=args.azim_end if args.azim_end is not None else -14.0,
                              elev_deg=args.elev if args.elev is not None else 15.0,
                              dist_mult=args.dist_mult if args.dist_mult is not None else 0.84,
                              single_frame=args.single_frame, samples=args.samples or 24)
        return

    if args.mode == "seg6_hero2":
        hid = args.hero2 or (avail[1] if len(avail) > 1 else (avail[0] if avail else "hero2"))
        render_hero_timelapse(assets_dir, hid, out_dir,
                              azim_start=args.azim_start if args.azim_start is not None else 145.0,
                              azim_end=args.azim_end if args.azim_end is not None else 118.0,
                              elev_deg=args.elev if args.elev is not None else 14.0,
                              dist_mult=args.dist_mult if args.dist_mult is not None else 0.82,
                              single_frame=args.single_frame, samples=args.samples or 24)
        return

    bpy.ops.wm.open_mainfile(filepath=master)
    scene = bpy.context.scene
    cam = scene.camera

    if args.mode == "seg1_hero_dolly":
        configure_eevee(samples=args.samples or 32, raytrace=True)
        for f in ([args.single_frame] if args.single_frame is not None else range(165)):
            t = f / 164.0
            y = 0.35 + t * 10.6
            aim_cam(cam, (-0.18 + 0.14 * math.sin(t * math.pi * 1.3), y, 1.54 - 0.06 * math.sin(t * math.pi)),
                    (0.04 * math.sin(t * 2.5), y + 18.0, 2.25), lens=28.0)
            scene.render.filepath = os.path.join(out_dir, f"f_{f:04d}.jpg")
            bpy.ops.render.render(write_still=True)
    elif args.mode == "seg2_3_clay":
        setup_clay_viewport(add_grid=True)
        configure_eevee(samples=args.samples or 16, raytrace=False)
        for f in ([args.single_frame] if args.single_frame is not None else range(120)):
            if f < 30:
                y = 10.95 + (f / 30.0) * 1.4
                aim_cam(cam, (-0.08, y, 1.54), (0.0, y + 18.0, 2.25), lens=28.0)
            else:
                t = ease_in_out((f - 30) / 89.0)
                aim_cam(cam, Vector((-0.05, 12.35, 1.54)).lerp(Vector((-0.55, -7.8, 21.5)), t),
                        Vector((0.0, 30.35, 2.25)).lerp(Vector((0.0, 21.5, 2.0)), t), lens=28.0 + 6.0 * t)
            scene.render.filepath = os.path.join(out_dir, f"f_{f:04d}.jpg")
            bpy.ops.render.render(write_still=True)
    elif args.mode == "seg4_assembly":
        mat_clay = setup_clay_viewport(add_grid=True)
        mat_orange = make_orange_mat()
        configure_eevee(samples=args.samples or 16, raytrace=False)
        pop_cols = sorted(list(bpy.data.collections["POP_Assets"].children), key=lambda c: c.name)
        col_objs = [(c, [o for o in c.all_objects if o.type in ("MESH", "CURVE")]) for c in pop_cols]
        spawn_frames = [216 if "999_" in c.name else int(8 + (i / max(1, len(col_objs) - 1)) * 204) for i, (c, _) in enumerate(col_objs)]
        for f in ([args.single_frame] if args.single_frame is not None else range(240)):
            t = f / 239.0
            aim_cam(cam, Vector((-0.55 + 0.35 * t, -7.8 + 1.2 * t, 21.5 + 1.8 * t)), Vector((0.0, 21.5 + 1.0 * t, 2.0)), lens=34.0)
            for (_, objs), sf in zip(col_objs, spawn_frames):
                if f < sf:
                    for o in objs:
                        o.hide_render = True
                else:
                    mat_use = mat_orange if (f - sf) < 7 else mat_clay
                    for o in objs:
                        o.hide_render = False
                        if len(o.data.materials) == 0 or o.data.materials[0] != mat_use:
                            o.data.materials.clear()
                            o.data.materials.append(mat_use)
            scene.render.filepath = os.path.join(out_dir, f"f_{f:04d}.jpg")
            bpy.ops.render.render(write_still=True)
    elif args.mode == "seg7_dive":
        configure_eevee(samples=args.samples or 32, raytrace=True)
        for f in ([args.single_frame] if args.single_frame is not None else range(180)):
            if f < 25:
                t = f / 25.0
                aim_cam(cam, (-0.20, -6.6 + 0.6 * t, 23.3 - 0.5 * t), (0.0, 22.5, 2.0), lens=34.0)
            else:
                t = ease_out_cubic((f - 25) / 154.0)
                p0, p1 = Vector((-0.20, -6.0, 22.8)), Vector((-0.18, 1.8, 1.58))
                loc = p0.lerp(p1, t)
                loc.z = p0.z * ((1.0 - t) ** 1.65) + p1.z * (1.0 - (1.0 - t) ** 1.65)
                aim_cam(cam, loc, Vector((0.0, 22.5, 2.0)).lerp(Vector((0.0, 22.0, 2.35)), t), lens=34.0 - 6.0 * t)
            scene.render.filepath = os.path.join(out_dir, f"f_{f:04d}.jpg")
            bpy.ops.render.render(write_still=True)
    print(f"[DONE] {args.mode} -> {out_dir}")


if __name__ == "__main__":
    main()
