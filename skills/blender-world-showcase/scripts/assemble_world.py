#!/usr/bin/env python3
"""Universal Blender 4.2+/5.3+ Multi-Agent 3D World Assembler.
Reads a custom manifest.json OR auto-discovers every *.blend asset in <project>/assets/
(zero-config mode!), builds the chosen corridor ground surface (wet_asphalt | stone_canal |
cobblestone | sand_plaza | metal_deck), appends each ASSET_<id> once into an unlinked
_ASSET_LIBRARY, instantiates ordered POP_001_* .. POP_999_* collections for viewport
timelapse animation, applies EEVEE shadow-overflow guards, saves world_master.blend,
and renders street + overhead verification stills."""
import argparse
import glob
import json
import math
import os
import sys
import bpy
from mathutils import Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import world_utils as wu


def make_surface_material(surface_type):
    if surface_type == "stone_canal":
        # Reflective dielectric canal water
        mat = bpy.data.materials.new("Mat_World_Ground")
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.inputs["Base Color"].default_value = (0.022, 0.068, 0.088, 1.0)
        bsdf.inputs["Metallic"].default_value = 0.0
        bsdf.inputs["Roughness"].default_value = 0.035
        if "IOR" in bsdf.inputs:
            bsdf.inputs["IOR"].default_value = 1.333
        if "Coat Weight" in bsdf.inputs:
            bsdf.inputs["Coat Weight"].default_value = 0.90
            bsdf.inputs["Coat Roughness"].default_value = 0.02
        tc = nt.nodes.new("ShaderNodeTexCoord")
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 14.0
        noise.inputs["Detail"].default_value = 5.0
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.055
        bump.inputs["Distance"].default_value = 0.008
        nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        return mat, wu.make_pbr_mat("Mat_World_Walkway", (0.28, 0.26, 0.23, 1.0), 0.0, 0.42, noise_scale=8.0, bump_strength=0.20, coat=0.25)

    if surface_type == "cobblestone":
        return (
            wu.make_pbr_mat("Mat_World_Ground", (0.14, 0.135, 0.13, 1.0), 0.0, 0.32, noise_scale=18.0, color_var=0.18, bump_strength=0.30, coat=0.45),
            wu.make_pbr_mat("Mat_World_Walkway", (0.22, 0.21, 0.195, 1.0), 0.0, 0.48, noise_scale=10.0, color_var=0.14, bump_strength=0.22, coat=0.20),
        )

    if surface_type == "sand_plaza":
        return (
            wu.make_pbr_mat("Mat_World_Ground", (0.48, 0.39, 0.28, 1.0), 0.0, 0.78, noise_scale=14.0, color_var=0.15, bump_strength=0.22, coat=0.0),
            wu.make_pbr_mat("Mat_World_Walkway", (0.54, 0.46, 0.36, 1.0), 0.0, 0.68, noise_scale=9.0, color_var=0.12, bump_strength=0.18, coat=0.0),
        )

    if surface_type == "metal_deck":
        return (
            wu.make_pbr_mat("Mat_World_Ground", (0.14, 0.16, 0.19, 1.0), 0.72, 0.36, noise_scale=16.0, color_var=0.10, bump_strength=0.16, coat=0.20),
            wu.make_pbr_mat("Mat_World_Walkway", (0.18, 0.20, 0.23, 1.0), 0.60, 0.42, noise_scale=12.0, color_var=0.10, bump_strength=0.14, coat=0.15),
        )

    # Default: wet_asphalt (true dielectric puddles, NEVER metallic!)
    mat = bpy.data.materials.new("Mat_World_Ground")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.082, 0.088, 0.096, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.0
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = 1.75
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.90
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 0.85
        bsdf.inputs["Coat Roughness"].default_value = 0.025
        if "Coat IOR" in bsdf.inputs:
            bsdf.inputs["Coat IOR"].default_value = 1.90

    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise_p = nt.nodes.new("ShaderNodeTexNoise")
    noise_p.inputs["Scale"].default_value = 0.35
    noise_p.inputs["Detail"].default_value = 6.0
    noise_p.inputs["Roughness"].default_value = 0.55

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.42
    ramp.color_ramp.elements[0].color = (0.02, 0.02, 0.02, 1.0)
    ramp.color_ramp.elements[1].position = 0.64
    ramp.color_ramp.elements[1].color = (0.38, 0.38, 0.38, 1.0)

    noise_g = nt.nodes.new("ShaderNodeTexNoise")
    noise_g.inputs["Scale"].default_value = 48.0
    noise_g.inputs["Detail"].default_value = 10.0

    mult_b = nt.nodes.new("ShaderNodeMath")
    mult_b.operation = "MULTIPLY"
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.22
    bump.inputs["Distance"].default_value = 0.010

    nt.links.new(tc.outputs["Object"], noise_p.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], noise_g.inputs["Vector"])
    nt.links.new(noise_p.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Roughness"])
    nt.links.new(noise_g.outputs["Fac"], mult_b.inputs[0])
    nt.links.new(ramp.outputs["Color"], mult_b.inputs[1])
    nt.links.new(mult_b.outputs["Value"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat, wu.make_pbr_mat("Mat_World_Walkway", (0.125, 0.132, 0.140, 1.0), 0.0, 0.28, noise_scale=6.0, color_var=0.14, bump_strength=0.18, coat=0.65)


def build_corridor_ground(world_cfg):
    col = wu.make_collection("ENV_Ground")
    surface = world_cfg.get("surface", "wet_asphalt")
    width = float(world_cfg.get("corridor_width", 4.2))
    length = float(world_cfg.get("corridor_length", 46.0))
    half_len = length * 0.5
    center_y = half_len - 2.0
    walk_w = 4.2

    mat_ground, mat_walk = make_surface_material(surface)
    mat_iron = wu.make_pbr_mat("Mat_Trim_Metal", (0.10, 0.11, 0.12, 1.0), metallic=0.80, roughness=0.35, coat=0.35)

    wu.add_box("Ground_Base_Slab", (width + walk_w * 2.0 + 0.4, length + 2.0, 0.24), (0.0, center_y, -0.14), col, mat_walk)
    ground_z = -0.05 if surface == "stone_canal" else 0.00
    wu.add_box("Ground_Corridor_Strip", (width, length + 2.0, 0.02), (0.0, center_y, ground_z), col, mat_ground)

    side_h = 0.24 if surface == "stone_canal" else 0.09
    side_x = width * 0.5 + walk_w * 0.5
    wu.add_box("Walkway_Left", (walk_w, length + 2.0, side_h), (-side_x, center_y, side_h * 0.5 - (0.06 if surface == "stone_canal" else 0.0)), col, mat_walk, bevel=0.018)
    wu.add_box("Walkway_Right", (walk_w, length + 2.0, side_h), (side_x, center_y, side_h * 0.5 - (0.06 if surface == "stone_canal" else 0.0)), col, mat_walk, bevel=0.018)

    if surface in ("wet_asphalt", "cobblestone", "metal_deck"):
        for y in range(4, int(length) - 4, 10):
            wu.add_cylinder(f"CenterCap_{y}", 0.40, 0.016, (0.12, float(y), 0.012), col, mat_iron, vertices=24)
            for sx in (-width * 0.46, width * 0.46):
                wu.add_box(f"Drain_{sx:.1f}_{y}", (0.24, 0.62, 0.014), (sx, float(y) + 3.0, 0.012), col, mat_iron)

    if world_cfg.get("horizon_monoliths", True):
        mat_mono = wu.make_pbr_mat("Mat_Horizon_Monolith", (0.06, 0.065, 0.075, 1.0), metallic=0.1, roughness=0.72)
        far_y = length + 3.0
        wu.add_box("Backdrop_Tower_L", (16.0, 6.0, 28.0), (-9.8, far_y, 14.0), col, mat_mono)
        wu.add_box("Backdrop_Tower_R", (16.0, 6.0, 28.0), (9.8, far_y, 14.0), col, mat_mono)
        wu.add_box("Backdrop_Bridge", (width + 2.0, 4.0, 3.0), (0.0, far_y - 0.5, 15.0), col, mat_mono)
        mat_far_a = wu.make_emissive_mat("Mat_Far_Accent_A", (0.18, 0.85, 0.95, 1.0), strength=5.0)
        mat_far_b = wu.make_emissive_mat("Mat_Far_Accent_B", (1.00, 0.52, 0.16, 1.0), strength=5.0)
        wu.add_box("Backdrop_Glow_L", (0.25, 0.25, 8.5), (-width * 0.5, far_y - 2.6, 5.8), col, mat_far_a)
        wu.add_box("Backdrop_Glow_R", (0.25, 0.25, 7.5), (width * 0.5, far_y - 2.6, 5.2), col, mat_far_b)
    return col


def build_overhead_dressing(pop_parent, world_cfg):
    style = world_cfg.get("overhead_style", "cables")
    if style == "none":
        return None
    col = wu.make_collection("POP_999_Overhead", parent=pop_parent)
    length = float(world_cfg.get("corridor_length", 46.0))
    half_w = float(world_cfg.get("corridor_width", 4.2)) * 0.5 + 0.15
    mat_rope = wu.make_pbr_mat("Mat_Overhead_Cord", (0.04, 0.042, 0.048, 1.0), metallic=0.1, roughness=0.50)

    if style == "festoon":
        mat_bulb = wu.make_emissive_mat("Mat_Festoon_Bulb", (1.0, 0.72, 0.30, 1.0), strength=8.0)
        for k, y in enumerate(range(3, int(length) - 2, 4)):
            z = 4.8 + (k % 3) * 0.65
            wu.add_catenary_cable(f"FestoonRope_{k}", (-half_w, y, z), (half_w, y + 0.3, z + 0.15), 0.45, 0.012, col, mat_rope, steps=14)
            for j in range(1, 6):
                t = j / 6.0
                px = -half_w + (2.0 * half_w) * t
                pz = z + 0.15 * t - 0.45 * 4.0 * t * (1.0 - t) - 0.08
                wu.add_cylinder(f"FestoonBulb_{k}_{j}", 0.055, 0.11, (px, y + 0.3 * t, pz), col, mat_bulb, vertices=10)
    else:
        trunks = [(-half_w * 0.75, 6.85), (-half_w * 0.65, 7.15), (half_w * 0.70, 6.95), (half_w * 0.80, 7.30)]
        pole_ys = [0.5, 4.2, 13.5, 23.0, 33.0, length - 2.0]
        for idx, (tx, tz) in enumerate(trunks):
            for i in range(len(pole_ys) - 1):
                wu.add_catenary_cable(f"TrunkWire_{idx}_{i}", (tx, pole_ys[i], tz), (tx, pole_ys[i + 1], tz),
                                      0.28 + 0.08 * ((idx + i) % 3), 0.015, col, mat_rope, steps=14)
        for k, y in enumerate(range(2, int(length) - 2, 3)):
            wu.add_catenary_cable(f"CrossWire_{k}", (-half_w, y, 4.6 + (k % 4) * 0.72),
                                  (half_w, y + 0.4, 4.9 + ((k + 2) % 4) * 0.70), 0.36 + (k % 3) * 0.12, 0.013, col, mat_rope, steps=14)
    return col


def append_asset_library(assets_dir, asset_ids):
    lib_col = bpy.data.collections.new("_ASSET_LIBRARY")
    templates = {}
    missing = []
    for aid in sorted(set(asset_ids)):
        blend_path = os.path.join(assets_dir, f"{aid}.blend")
        if not os.path.exists(blend_path):
            missing.append(aid)
            continue
        col_name = f"ASSET_{aid}"
        with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
            if col_name in data_from.collections:
                data_to.collections = [col_name]
            elif data_from.collections:
                cand = [c for c in data_from.collections if not c.startswith("_")]
                data_to.collections = [cand[0]] if cand else [data_from.collections[0]]
        loaded = data_to.collections[0] if data_to.collections else None
        if loaded:
            lib_col.children.link(loaded)
            templates[aid] = loaded
        else:
            missing.append(aid)
    print(f"[LIBRARY] Loaded {len(templates)}/{len(set(asset_ids))} assets. Missing: {missing}")
    return templates


def auto_build_manifest(assets_dir, templates):
    """Zero-config layout generator: classifies loaded assets by bounding box height into
    corridor buildings (>=4.2m tall) vs street-level props/vehicles and populates a 46m street."""
    buildings, props = [], []
    for aid, col in sorted(templates.items()):
        max_z = 0.0
        for o in col.all_objects:
            if o.type in ("MESH", "CURVE"):
                for c in o.bound_box:
                    max_z = max(max_z, (o.matrix_world @ Vector(c)).z)
        if max_z >= 4.2:
            buildings.append(aid)
        else:
            props.append(aid)
    if not buildings:
        buildings = sorted(templates.keys())

    left_b, right_b, street_p = [], [], []
    for i in range(11):
        y = 2.0 + i * 4.0
        left_b.append([y, buildings[(i * 2) % len(buildings)]])
        right_b.append([y + 0.1, buildings[(i * 2 + 1) % len(buildings)]])
    for i, aid in enumerate(props):
        side = -1.0 if i % 2 == 0 else 1.0
        y = 2.8 + i * 3.1
        street_p.append([aid, [side * 1.55, y, 0.02], 90.0 if side < 0 else -90.0, 1.0])
    return {
        "world": {"surface": "wet_asphalt", "corridor_width": 4.2, "corridor_length": 46.0, "overhead_style": "cables", "horizon_monoliths": True},
        "left_buildings": left_b,
        "right_buildings": right_b,
        "pylons": [],
        "street_props": street_p,
    }


def place_asset(templates, asset_id, pop_name, loc, rot_z_deg=0.0, scale=1.0, parent_col=None):
    if asset_id not in templates:
        return None
    src_col = templates[asset_id]
    pop_col = bpy.data.collections.new(pop_name)
    (bpy.context.scene.collection if parent_col is None else parent_col).children.link(pop_col)

    root = bpy.data.objects.new(f"{pop_name}_ROOT", None)
    root.location = loc
    root.rotation_euler = (0.0, 0.0, math.radians(rot_z_deg))
    root.scale = (scale, scale, scale)
    pop_col.objects.link(root)

    for src_obj in src_col.all_objects:
        if src_obj.type not in ("MESH", "CURVE", "LIGHT"):
            continue
        dup = src_obj.copy()
        pop_col.objects.link(dup)
        dup.parent = root
    return pop_col


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(description="Assemble any modular 3D world from manifest.json or auto-layout.")
    p.add_argument("--project-dir", required=True)
    p.add_argument("--manifest", default=None, help="Optional world manifest JSON (auto-layouts assets/ if omitted)")
    p.add_argument("--surface", default=None, choices=["wet_asphalt", "stone_canal", "cobblestone", "sand_plaza", "metal_deck"])
    p.add_argument("--out", default=None, help="Output .blend path (default: <project-dir>/world_master.blend)")
    p.add_argument("--skip-verify", action="store_true")
    args = p.parse_args(argv)

    proj = os.path.abspath(args.project_dir)
    wu.configure_project(proj)
    wu.reset_scene()
    assets_dir = os.path.join(proj, "assets")
    renders_dir = os.path.join(proj, "renders")
    os.makedirs(renders_dir, exist_ok=True)

    manifest = None
    if args.manifest and os.path.exists(args.manifest):
        with open(args.manifest, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
        needed = (
            [aid for _, aid in manifest.get("left_buildings", [])]
            + [aid for _, aid in manifest.get("right_buildings", [])]
            + [it[0] for it in manifest.get("pylons", [])]
            + [it[0] for it in manifest.get("street_props", [])]
        )
    else:
        needed = [os.path.splitext(os.path.basename(b))[0] for b in sorted(glob.glob(os.path.join(assets_dir, "*.blend")))]

    templates = append_asset_library(assets_dir, needed)
    if manifest is None:
        manifest = auto_build_manifest(assets_dir, templates)

    world_cfg = manifest.get("world", {})
    if args.surface:
        world_cfg["surface"] = args.surface
    build_corridor_ground(world_cfg)

    pop_root = wu.make_collection("POP_Assets")
    bx_off = float(world_cfg.get("corridor_width", 4.2)) * 0.5 + 1.85
    left_b = manifest.get("left_buildings", [])
    right_b = manifest.get("right_buildings", [])
    pop_idx = 1
    for i in range(max(len(left_b), len(right_b))):
        if i < len(left_b):
            y, aid = left_b[i]
            place_asset(templates, aid, f"POP_{pop_idx:03d}_BL_{aid}", (-bx_off, y, 0.08), rot_z_deg=90.0, parent_col=pop_root)
            pop_idx += 1
        if i < len(right_b):
            y, aid = right_b[i]
            place_asset(templates, aid, f"POP_{pop_idx:03d}_BR_{aid}", (bx_off, y, 0.08), rot_z_deg=-90.0, parent_col=pop_root)
            pop_idx += 1

    for aid, loc, rz in manifest.get("pylons", []):
        place_asset(templates, aid, f"POP_{pop_idx:03d}_Pylon", tuple(loc), rot_z_deg=rz, parent_col=pop_root)
        pop_idx += 1

    for aid, loc, rz, sc in manifest.get("street_props", []):
        place_asset(templates, aid, f"POP_{pop_idx:03d}_{aid}", tuple(loc), rot_z_deg=rz, scale=sc, parent_col=pop_root)
        pop_idx += 1

    build_overhead_dressing(pop_root, world_cfg)

    for lobj in bpy.data.objects:
        if lobj.type == "LIGHT":
            lobj.data.use_shadow = False
            if hasattr(lobj.data, "specular_factor"):
                lobj.data.specular_factor = 0.0

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    if hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 24
    if hasattr(scene.eevee, "use_raytracing"):
        scene.eevee.use_raytracing = True
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Punchy"
    except Exception:
        pass

    ccol = wu.make_collection("ENV_Cameras")
    cd = bpy.data.cameras.new("Cam_World_Hero")
    cd.lens = 28.0
    cd.clip_end = 250.0
    co = bpy.data.objects.new("Cam_World_Hero", cd)
    co.location = (-0.18, 0.35, 1.55)
    co.rotation_euler = (Vector((0.0, 18.0, 2.35)) - co.location).to_track_quat("-Z", "Y").to_euler()
    ccol.objects.link(co)
    scene.camera = co

    out_blend = os.path.abspath(args.out) if args.out else os.path.join(proj, "world_master.blend")
    try:
        bpy.ops.file.pack_all()
    except Exception:
        pass
    bpy.ops.wm.save_as_mainfile(filepath=out_blend)
    print(f"[MASTER SAVED] {out_blend} ({len(bpy.data.objects)} objects)")

    if not args.skip_verify:
        scene.render.filepath = os.path.join(renders_dir, "verify_street.png")
        bpy.ops.render.render(write_still=True)
        co.location = (-0.5, -6.5, 19.0)
        co.rotation_euler = (Vector((0.0, 20.0, 2.0)) - co.location).to_track_quat("-Z", "Y").to_euler()
        cd.lens = 32.0
        scene.render.filepath = os.path.join(renders_dir, "verify_overhead.png")
        bpy.ops.render.render(write_still=True)
        print("[VERIFY RENDERS DONE]")


if __name__ == "__main__":
    main()
