"""Universal Blender 4.2+/5.3+ procedural 3D asset-building SDK.
Provides headless-safe bmesh primitives, box UV projection, corrugated/arch/cable/lantern
builders, procedural PBR & emissive materials, build_stage (1..4) tagging for 4-stage
hero construction turntables, packed .blend saving, and isolated studio QA previews."""
import math
import os
import bpy
import bmesh
from mathutils import Vector

BASE_DIR = os.path.abspath(os.environ.get("WORLD_PROJECT_DIR", os.getcwd()))
TEX_DIR = os.path.join(BASE_DIR, "textures")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
PREVIEWS_DIR = os.path.join(BASE_DIR, "previews")


def configure_project(project_dir):
    """Point all output/texture helpers at the active project directory."""
    global BASE_DIR, TEX_DIR, ASSETS_DIR, PREVIEWS_DIR
    BASE_DIR = os.path.abspath(project_dir)
    TEX_DIR = os.path.join(BASE_DIR, "textures")
    ASSETS_DIR = os.path.join(BASE_DIR, "assets")
    PREVIEWS_DIR = os.path.join(BASE_DIR, "previews")
    os.makedirs(TEX_DIR, exist_ok=True)
    os.makedirs(ASSETS_DIR, exist_ok=True)
    os.makedirs(PREVIEWS_DIR, exist_ok=True)
    return BASE_DIR


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(ASSETS_DIR, exist_ok=True)
    os.makedirs(PREVIEWS_DIR, exist_ok=True)


def make_collection(name, parent=None):
    col = bpy.data.collections.new(name)
    if parent is None:
        bpy.context.scene.collection.children.link(col)
    else:
        parent.children.link(col)
    return col


def link_obj(obj, col, build_stage=1):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)
    obj["build_stage"] = int(max(1, min(4, build_stage)))
    return obj


def set_smooth(obj):
    if obj.type != "MESH" or not obj.data:
        return
    mesh = obj.data
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    mesh.update()


def add_bevel(obj, width=0.012, segments=2):
    mod = obj.modifiers.new("Bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(32.0)
    return mod


def assign_mat(obj, mat):
    if obj.type not in ("MESH", "CURVE"):
        return
    if len(obj.data.materials) == 0:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat


def box_uv_project(obj, scale=1.0):
    """Fast headless-safe box UV projection in pure bmesh (zero viewport dependency)."""
    if obj.type != "MESH":
        return
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    uv_layer = bm.loops.layers.uv.verify()
    for f in bm.faces:
        n = f.normal
        ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
        for loop in f.loops:
            v = loop.vert.co
            if az >= ax and az >= ay:
                u, w = v.x * scale, v.y * scale
            elif ax >= ay and ax >= az:
                u, w = v.y * scale, v.z * scale
            else:
                u, w = v.x * scale, v.z * scale
            loop[uv_layer].uv = (u, w)
    bm.to_mesh(me)
    bm.free()
    me.update()


def add_box(name, size, loc, col, mat=None, rot_deg=(0, 0, 0), bevel=0.0, build_stage=1, uv_scale=1.0):
    sx, sy, sz = size
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    obj.location = loc
    obj.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    link_obj(obj, col, build_stage)
    box_uv_project(obj, scale=uv_scale)
    if bevel > 0.0:
        add_bevel(obj, width=bevel, segments=2)
    if mat:
        assign_mat(obj, mat)
    return obj


def add_cylinder(name, radius, depth, loc, col, mat=None, rot_deg=(0, 0, 0), vertices=24,
                 radius2=None, build_stage=1, smooth=True):
    bm = bmesh.new()
    r2 = radius if radius2 is None else radius2
    bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False, segments=vertices,
        radius1=radius, radius2=r2, depth=depth,
    )
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    obj.location = loc
    obj.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    link_obj(obj, col, build_stage)
    box_uv_project(obj, scale=1.0)
    if smooth:
        set_smooth(obj)
    if mat:
        assign_mat(obj, mat)
    return obj


def add_uv_plane(name, width, height, loc, col, mat, rot_deg=(90, 0, 0), build_stage=1, flip_x=False):
    """Quad with exact 0..1 UVs (vertical facing -Y by default when rot_deg=(90,0,0))."""
    bm = bmesh.new()
    hw, hh = width / 2.0, height / 2.0
    f = bm.faces.new((
        bm.verts.new((-hw, -hh, 0)),
        bm.verts.new((hw, -hh, 0)),
        bm.verts.new((hw, hh, 0)),
        bm.verts.new((-hw, hh, 0)),
    ))
    uv_layer = bm.loops.layers.uv.verify()
    uvs = [(1, 0), (0, 0), (0, 1), (1, 1)] if flip_x else [(0, 0), (1, 0), (1, 1), (0, 1)]
    for loop, uv in zip(f.loops, uvs):
        loop[uv_layer].uv = uv
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    obj.location = loc
    obj.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    link_obj(obj, col, build_stage)
    if mat:
        assign_mat(obj, mat)
    return obj


def add_arch(name, span, depth, thickness, loc, col, mat=None, segments=16, rot_deg=(0, 0, 0), build_stage=2):
    """Build a semicircular architectural arch spanning X with extruded depth along Y."""
    bm = bmesh.new()
    r_in = max(0.05, span * 0.5)
    r_out = r_in + thickness
    hy = depth * 0.5
    rings = []
    for i in range(segments + 1):
        ang = math.pi * (i / segments)
        ca, sa = math.cos(ang), math.sin(ang)
        rings.append((
            bm.verts.new((r_in * ca, -hy, r_in * sa)),
            bm.verts.new((r_out * ca, -hy, r_out * sa)),
            bm.verts.new((r_out * ca, hy, r_out * sa)),
            bm.verts.new((r_in * ca, hy, r_in * sa)),
        ))
    for i in range(segments):
        a, b = rings[i], rings[i + 1]
        for k in range(4):
            kn = (k + 1) % 4
            bm.faces.new((a[k], a[kn], b[kn], b[k]))
    bm.faces.new((rings[0][0], rings[0][3], rings[0][2], rings[0][1]))
    bm.faces.new((rings[-1][0], rings[-1][1], rings[-1][2], rings[-1][3]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    obj.location = loc
    obj.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    link_obj(obj, col, build_stage)
    box_uv_project(obj, scale=0.8)
    set_smooth(obj)
    if mat:
        assign_mat(obj, mat)
    return obj


def add_corrugated_panel(name, width, height, depth_amp, ribs, loc, col, mat, rot_deg=(0, 0, 0), build_stage=1):
    bm = bmesh.new()
    segs_x = max(16, ribs * 4)
    segs_z = 2
    verts_grid = []
    for iz in range(segs_z + 1):
        z = -height / 2.0 + (height * iz / segs_z)
        row = []
        for ix in range(segs_x + 1):
            t = ix / segs_x
            row.append(bm.verts.new((-width / 2.0 + width * t, math.sin(t * ribs * 2.0 * math.pi) * depth_amp, z)))
        verts_grid.append(row)
    for iz in range(segs_z):
        for ix in range(segs_x):
            bm.faces.new((verts_grid[iz][ix], verts_grid[iz][ix + 1], verts_grid[iz + 1][ix + 1], verts_grid[iz + 1][ix]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    obj.location = loc
    obj.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    link_obj(obj, col, build_stage)
    box_uv_project(obj, scale=0.8)
    set_smooth(obj)
    sol = obj.modifiers.new("Solidify", "SOLIDIFY")
    sol.thickness = 0.014
    if mat:
        assign_mat(obj, mat)
    return obj


def add_catenary_cable(name, p0, p1, sag, radius, col, mat, steps=16, build_stage=3):
    curve = bpy.data.curves.new(name, type="CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    spline = curve.splines.new("POLY")
    spline.points.add(steps)
    v0, v1 = Vector(p0), Vector(p1)
    for i in range(steps + 1):
        t = i / steps
        pt = v0.lerp(v1, t)
        pt.z -= sag * 4.0 * t * (1.0 - t)
        spline.points[i].co = (pt.x, pt.y, pt.z, 1.0)
    obj = bpy.data.objects.new(name, curve)
    link_obj(obj, col, build_stage)
    if mat:
        assign_mat(obj, mat)
    return obj


def add_lantern(name, radius, height, loc, col, mat_body, mat_cap, build_stage=3):
    bm = bmesh.new()
    rings, segs = 14, 24
    ring_verts = []
    for ir in range(rings + 1):
        t = ir / rings
        z = (t - 0.5) * height
        r = max(radius * 0.36, radius * (math.sin(t * math.pi) ** 0.55) * (1.0 + 0.035 * math.sin(t * 20.0 * math.pi)))
        ring_verts.append([bm.verts.new((r * math.cos(2.0 * math.pi * s / segs), r * math.sin(2.0 * math.pi * s / segs), z)) for s in range(segs)])
    uv_layer = bm.loops.layers.uv.verify()
    for ir in range(rings):
        for s in range(segs):
            sn = (s + 1) % segs
            f = bm.faces.new((ring_verts[ir][s], ring_verts[ir][sn], ring_verts[ir + 1][sn], ring_verts[ir + 1][s]))
            f.loops[0][uv_layer].uv = (s / segs, ir / rings)
            f.loops[1][uv_layer].uv = ((s + 1) / segs, ir / rings)
            f.loops[2][uv_layer].uv = ((s + 1) / segs, (ir + 1) / rings)
            f.loops[3][uv_layer].uv = (s / segs, (ir + 1) / rings)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    obj.location = loc
    link_obj(obj, col, build_stage)
    set_smooth(obj)
    assign_mat(obj, mat_body)
    cap_r = radius * 0.44
    add_cylinder(f"{name}_cap_top", cap_r, 0.032, (loc[0], loc[1], loc[2] + height / 2.0 + 0.01), col, mat_cap, vertices=18, build_stage=build_stage)
    add_cylinder(f"{name}_cap_bot", cap_r, 0.028, (loc[0], loc[1], loc[2] - height / 2.0 - 0.01), col, mat_cap, vertices=18, build_stage=build_stage)
    return obj


# --- Procedural & Image PBR Material Builders ---

def make_pbr_mat(name, base_color=(0.3, 0.3, 0.3, 1.0), metallic=0.0, roughness=0.55,
                 noise_scale=12.0, color_var=0.08, bump_strength=0.12, coat=0.0):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if coat > 0.0 and "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = coat
        bsdf.inputs["Coat Roughness"].default_value = 0.08

    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = noise_scale
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.62

    mix_col = nt.nodes.new("ShaderNodeMix")
    mix_col.data_type = "RGBA"
    mix_col.inputs[6].default_value = (
        max(0.0, base_color[0] * (1.0 - color_var * 2.2)),
        max(0.0, base_color[1] * (1.0 - color_var * 2.2)),
        max(0.0, base_color[2] * (1.0 - color_var * 2.2)),
        1.0,
    )
    mix_col.inputs[7].default_value = (
        min(1.0, base_color[0] * (1.0 + color_var)),
        min(1.0, base_color[1] * (1.0 + color_var)),
        min(1.0, base_color[2] * (1.0 + color_var)),
        1.0,
    )

    ramp_r = nt.nodes.new("ShaderNodeMapRange")
    ramp_r.inputs["To Min"].default_value = max(0.05, roughness - 0.14)
    ramp_r.inputs["To Max"].default_value = min(0.98, roughness + 0.14)

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.015

    nt.links.new(tex_coord.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], mix_col.inputs["Factor"])
    nt.links.new(mix_col.outputs[2], bsdf.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], ramp_r.inputs["Value"])
    nt.links.new(ramp_r.outputs["Result"], bsdf.inputs["Roughness"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_image_emissive_mat(name, tex_filename, emission_strength=3.5, roughness=0.25, tint=(1.0, 1.0, 1.0, 1.0)):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Emission Strength"].default_value = emission_strength

    img_path = tex_filename if os.path.isabs(tex_filename) else os.path.join(TEX_DIR, tex_filename)
    tex = nt.nodes.new("ShaderNodeTexImage")
    if os.path.exists(img_path):
        tex.image = bpy.data.images.load(img_path, check_existing=True)
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    else:
        bsdf.inputs["Base Color"].default_value = tint
        bsdf.inputs["Emission Color"].default_value = tint
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_emissive_mat(name, color=(1.0, 0.72, 0.35, 1.0), strength=6.0, roughness=0.2):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Emission Color"].default_value = color
    bsdf.inputs["Emission Strength"].default_value = strength
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_frosted_glass_mat(name, glow_color=(1.0, 0.72, 0.32, 1.0), strength=2.4):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.92, 0.84, 0.70, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.22
    bsdf.inputs["Emission Color"].default_value = glow_color
    bsdf.inputs["Emission Strength"].default_value = strength
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 0.6
        bsdf.inputs["Coat Roughness"].default_value = 0.08
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def save_asset_and_preview(asset_id, col, cam_dist_mult=2.2, elev_deg=20.0, azim_deg=-35.0,
                           dark_studio=True, preview_res=640, render_preview=True):
    """Pack & save clean ASSET_<id>.blend, then optionally render isolated studio QA PNG."""
    os.makedirs(ASSETS_DIR, exist_ok=True)
    os.makedirs(PREVIEWS_DIR, exist_ok=True)
    blend_path = os.path.join(ASSETS_DIR, f"{asset_id}.blend")
    try:
        bpy.ops.file.pack_all()
    except Exception:
        pass
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    bpy.context.view_layer.update()
    mins, maxs = Vector((1e9, 1e9, 1e9)), Vector((-1e9, -1e9, -1e9))
    count = 0
    for obj in col.all_objects:
        if obj.type in ("MESH", "CURVE"):
            for corner in obj.bound_box:
                wc = obj.matrix_world @ Vector(corner)
                mins.x, mins.y, mins.z = min(mins.x, wc.x), min(mins.y, wc.y), min(mins.z, wc.z)
                maxs.x, maxs.y, maxs.z = max(maxs.x, wc.x), max(maxs.y, wc.y), max(maxs.z, wc.z)
            count += 1
    extent = maxs - mins if count else Vector((2, 2, 2))
    if not render_preview:
        print(f"[ASSET OK] {asset_id}: {count} objs, bbox={tuple(round(v, 2) for v in extent)}, saved {blend_path}")
        return blend_path, None

    center = (mins + maxs) * 0.5 if count else Vector((0, 0, 1))
    radius = max(0.35, extent.length * 0.5)
    pcol = make_collection("_PreviewStudio")
    world = bpy.data.worlds.new("_PreviewWorld")
    bpy.context.scene.world = world
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.045, 0.052, 0.062, 1.0) if dark_studio else (0.18, 0.19, 0.21, 1.0)
        bg.inputs["Strength"].default_value = 0.55 if dark_studio else 1.0

    def add_area(nm, loc, energy, size, color):
        ld = bpy.data.lights.new(nm, type="AREA")
        ld.energy, ld.size, ld.color = energy, size, color
        lo = bpy.data.objects.new(nm, ld)
        lo.location = loc
        lo.rotation_euler = (center - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        pcol.objects.link(lo)

    d = radius * cam_dist_mult
    add_area("_Key", center + Vector((-d * 0.9, -d * 1.1, d * 0.9)), 140.0 * (radius ** 1.6), radius * 1.2, (1.0, 0.96, 0.90))
    add_area("_Fill", center + Vector((d * 1.1, -d * 0.6, d * 0.5)), 55.0 * (radius ** 1.6), radius * 1.5, (0.76, 0.86, 1.0))
    add_area("_Rim", center + Vector((d * 0.4, d * 1.2, d * 0.8)), 90.0 * (radius ** 1.6), radius * 1.0, (0.85, 0.92, 1.0))

    az, el = math.radians(azim_deg), math.radians(elev_deg)
    cam_pos = center + Vector((d * math.cos(el) * math.sin(az), -d * math.cos(el) * math.cos(az), d * math.sin(el)))
    cd = bpy.data.cameras.new("_PreviewCam")
    cd.lens = 50.0
    co = bpy.data.objects.new("_PreviewCam", cd)
    co.location = cam_pos
    co.rotation_euler = (center - cam_pos).to_track_quat("-Z", "Y").to_euler()
    pcol.objects.link(co)

    scene = bpy.context.scene
    scene.camera = co
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = preview_res
    scene.render.resolution_y = preview_res
    scene.render.image_settings.file_format = "PNG"
    if hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 24
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Punchy"
    except Exception:
        pass
    out_png = os.path.join(PREVIEWS_DIR, f"{asset_id}.png")
    scene.render.filepath = out_png
    bpy.ops.render.render(write_still=True)
    print(f"[ASSET OK] {asset_id}: {count} objs, bbox={tuple(round(v, 2) for v in extent)}, saved {blend_path} & {out_png}")
    return blend_path, out_png
