"""
Build a sculpted, photorealistic, QA-clean 3D Porsche 911 (992 GT3) in Blender 5.3
with dramatic dark-metallic automotive studio lighting and animated overhead softbox sweep.

Coordinate convention:
  - Front of car: -Y (nose at Y = -2.28 m)
  - Rear of car:  +Y (tail at Y = +2.28 m)
  - Width:        X  (-0.97 m left to +0.97 m right)
  - Height:       Z  (ground at Z = 0.0 m, roof at Z = 1.29 m)
  - Camera:       straight down -Z (+Y up in image), so nose points DOWN and tail UP.
"""
import argparse
import math
import os
import sys
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler

def parse_cli():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="./porsche911.blend", help="Output .blend path")
    return p.parse_args(argv)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def get_or_create_collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        if parent is None:
            bpy.context.scene.collection.children.link(col)
        else:
            parent.children.link(col)
    return col


def link_obj(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)


def smooth_mesh(obj):
    me = obj.data
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.update()


def clean_bm(bm):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-4, edges=bm.edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)


def apply_subsurf(obj, levels=2, render_levels=2):
    mod = obj.modifiers.new("Subsurf", "SUBSURF")
    mod.levels = levels
    mod.render_levels = render_levels
    mod.use_limit_surface = True
    return mod


def apply_bevel(obj, width=0.005, segments=2, angle_deg=35.0):
    mod = obj.modifiers.new("Bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(angle_deg)
    mod.use_clamp_overlap = True
    mod.harden_normals = False
    return mod


def make_materials():
    mats = {}

    def new_bsdf(name, base_color, metallic=0.0, roughness=0.3, coat=0.0, coat_rough=0.04,
                 ior=1.5, transmission=0.0, emission=None, emission_strength=0.0):
        mat = bpy.data.materials.new(name)
        nt = mat.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["IOR"].default_value = ior
        if "Coat Weight" in bsdf.inputs:
            bsdf.inputs["Coat Weight"].default_value = coat
            bsdf.inputs["Coat Roughness"].default_value = coat_rough
        if "Transmission Weight" in bsdf.inputs:
            bsdf.inputs["Transmission Weight"].default_value = transmission
        if emission is not None and "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
            bsdf.inputs["Emission Strength"].default_value = emission_strength
        mats[name] = mat
        return mat

    # Rich Gunmetal / Obsidian Metallic Porsche Car Paint (liquid metallic reflections like reference!)
    paint = new_bsdf(
        "M_CarPaint_Agate",
        base_color=(0.028, 0.032, 0.038),
        metallic=0.84,
        roughness=0.17,
        coat=1.0,
        coat_rough=0.03,
    )
    nt = paint.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 220.0
    noise.inputs["Detail"].default_value = 6.0
    ramp = nt.nodes.new("ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value = 0.25
    ramp.inputs["From Max"].default_value = 0.75
    ramp.inputs["To Min"].default_value = 0.14
    ramp.inputs["To Max"].default_value = 0.21
    nt.links.new(tex_coord.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Value"])
    nt.links.new(ramp.outputs["Result"], bsdf.inputs["Roughness"])

    # Deep Gloss Carbon Fiber (Roof, Rear Wing, Hood Vents, Splitter, Diffuser)
    carbon = new_bsdf(
        "M_CarbonFiber",
        base_color=(0.008, 0.009, 0.011),
        metallic=0.30,
        roughness=0.18,
        coat=1.0,
        coat_rough=0.035,
    )
    cnt = carbon.node_tree
    cbsdf = next(n for n in cnt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = cnt.nodes.new("ShaderNodeTexCoord")
    checker = cnt.nodes.new("ShaderNodeTexChecker")
    checker.inputs["Scale"].default_value = 320.0
    checker.inputs["Color1"].default_value = (0.005, 0.006, 0.008, 1.0)
    checker.inputs["Color2"].default_value = (0.018, 0.020, 0.025, 1.0)
    cnt.links.new(tc.outputs["Object"], checker.inputs["Vector"])
    cnt.links.new(checker.outputs["Color"], cbsdf.inputs["Base Color"])

    # Pitch-Dark Glossy Automotive Tinted Glass (like Defender windshield!)
    new_bsdf(
        "M_Glass_Tinted",
        base_color=(0.002, 0.003, 0.005),
        metallic=0.0,
        roughness=0.015,
        coat=1.0,
        coat_rough=0.008,
        ior=1.52,
        transmission=0.14,
    )

    # Clear Headlight Glass Lens (thin transparent glass, no solid-ball TIR darkening)
    mat_gc = new_bsdf(
        "M_Glass_Clear",
        base_color=(0.94, 0.97, 1.0),
        metallic=0.0,
        roughness=0.02,
        coat=1.0,
        coat_rough=0.01,
        ior=1.48,
        transmission=0.0,
    )
    bsdf_gc = next(n for n in mat_gc.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Alpha" in bsdf_gc.inputs:
        bsdf_gc.inputs["Alpha"].default_value = 0.22

    # Chrome/Silver Headlight Reflector Bowl
    new_bsdf("M_Headlight_Reflector", base_color=(0.78, 0.82, 0.88), metallic=0.96, roughness=0.14, coat=1.0, coat_rough=0.02)

    # Satin Black Trim / Louvers / Shutlines / Rubber
    new_bsdf("M_Trim_Black", base_color=(0.006, 0.007, 0.008), metallic=0.05, roughness=0.52)
    new_bsdf("M_Interior_Alcantara", base_color=(0.012, 0.013, 0.016), metallic=0.0, roughness=0.88)
    new_bsdf("M_Rubber_Tire", base_color=(0.010, 0.011, 0.012), metallic=0.0, roughness=0.72)

    # Dark Satin Gunmetal Alloy (Wheels, Wing Pylons, Exhaust)
    new_bsdf("M_Alloy_Satin", base_color=(0.18, 0.20, 0.23), metallic=0.95, roughness=0.22)
    new_bsdf("M_Brake_Disc", base_color=(0.35, 0.36, 0.38), metallic=0.95, roughness=0.30)

    # Rich Electric Royal Cobalt Blue (matches Defender's vivid blue straps!)
    new_bsdf(
        "M_Accent_CobaltBlue",
        base_color=(0.010, 0.032, 0.72),
        metallic=0.18,
        roughness=0.20,
        coat=0.95,
        coat_rough=0.04,
    )

    # Crisp 4-Point Porsche DRL LEDs + main projector
    new_bsdf(
        "M_LED_White",
        base_color=(1.0, 1.0, 1.0),
        metallic=0.0,
        roughness=0.05,
        emission=(0.90, 0.96, 1.0),
        emission_strength=18.0,
    )

    # Emissive 992 Crimson Rear Light Bar
    new_bsdf(
        "M_LED_Red",
        base_color=(0.35, 0.006, 0.012),
        metallic=0.0,
        roughness=0.10,
        coat=1.0,
        coat_rough=0.02,
        emission=(0.95, 0.015, 0.025),
        emission_strength=3.2,
    )

    # Porsche Gold Crest
    new_bsdf("M_Badge_Gold", base_color=(0.68, 0.50, 0.14), metallic=0.92, roughness=0.20)

    return mats


# ---------------------------------------------------------------------------
# Parametric Porsche 911 (992 GT3) Body Lofting
# ---------------------------------------------------------------------------
def _interp_catmull(pts, x):
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        if x0 <= x <= x1:
            t = (x - x0) / max(1e-9, (x1 - x0))
            t2 = t * t
            t3 = t2 * t
            h00 = 2 * t3 - 3 * t2 + 1
            h10 = t3 - 2 * t2 + t
            h01 = -2 * t3 + 3 * t2
            h11 = t3 - t2
            m0 = (pts[i + 1][1] - pts[max(0, i - 1)][1]) / max(1e-6, pts[i + 1][0] - pts[max(0, i - 1)][0]) * (x1 - x0)
            m1 = (pts[min(len(pts) - 1, i + 2)][1] - pts[i][1]) / max(1e-6, pts[min(len(pts) - 1, i + 2)][0] - pts[i][0]) * (x1 - x0)
            return h00 * y0 + h10 * m0 + h01 * y1 + h11 * m1
    return pts[-1][1]


def half_width_at_y(y):
    pts = [
        (-2.26, 0.00),
        (-2.24, 0.40),
        (-2.16, 0.65),
        (-1.98, 0.81),
        (-1.72, 0.895),
        (-1.42, 0.935),  # Front wheel arch peak
        (-1.12, 0.915),
        (-0.82, 0.875),  # Front fender tuck into A-pillar
        (-0.45, 0.862),  # Iconic 911 narrow coke-bottle door waist!
        (0.00,  0.868),
        (0.45,  0.900),  # Rear haunch flare
        (0.85,  0.958),  # Muscular 911 rear hips
        (1.22,  0.980),  # Rear wheel arch peak (widest!)
        (1.58,  0.952),
        (1.90,  0.885),
        (2.12,  0.760),
        (2.22,  0.540),
        (2.26,  0.00),
    ]
    return _interp_catmull(pts, y)


def lower_body_height_at_y(y):
    pts = [
        (-2.26, 0.28),
        (-2.16, 0.42),
        (-1.92, 0.56),
        (-1.55, 0.71),
        (-1.15, 0.78),
        (-0.75, 0.82),
        (-0.20, 0.86),
        (0.45,  0.90),
        (1.05,  0.93),
        (1.55,  0.90),
        (1.98,  0.83),
        (2.22,  0.72),
        (2.26,  0.50),
    ]
    return _interp_catmull(pts, y)


def center_height_at_y(y):
    pts = [
        (-2.26, 0.26),
        (-2.16, 0.39),
        (-1.90, 0.52),
        (-1.55, 0.64),
        (-1.15, 0.74),
        (-0.75, 0.81),
        (-0.20, 0.84),
        (0.45,  0.86),
        (1.05,  0.91),
        (1.55,  0.89),
        (1.98,  0.82),
        (2.22,  0.71),
        (2.26,  0.48),
    ]
    return _interp_catmull(pts, y)


def fender_crest_boost(y, u):
    boost = 0.0
    if -2.12 < y < -0.72:
        fy = max(0.0, math.sin(math.pi * (y + 2.12) / 1.40)) ** 0.85
        fu = math.exp(-((u - 0.74) / 0.19) ** 2)
        boost += 0.088 * fy * fu
        fhood = math.exp(-((u - 0.25) / 0.22) ** 2)
        boost -= 0.020 * fy * fhood
    if 0.35 < y < 2.02:
        ry = max(0.0, math.sin(math.pi * (y - 0.35) / 1.67)) ** 0.9
        ru = math.exp(-((u - 0.78) / 0.20) ** 2)
        boost += 0.048 * ry * ru
    return boost


def surface_z_on_hood(x, y):
    w = max(0.25, half_width_at_y(y))
    u = min(1.0, abs(x) / w)
    cz = math.sqrt(max(0.0, 1.0 - u * u))
    z_belt = lower_body_height_at_y(y)
    z_ctr = center_height_at_y(y)
    z_base = z_ctr * (cz ** 1.3) + z_belt * (1.0 - cz ** 1.3)
    return z_base + 0.022 * math.sin(math.pi * u) + fender_crest_boost(y, u)


def build_body_shell(col, mats):
    bm = bmesh.new()
    ys = [
        -2.24, -2.18, -2.08, -1.94, -1.78, -1.60, -1.42, -1.24, -1.04, -0.84,
        -0.62, -0.38, -0.14,  0.10,  0.34,  0.58,  0.82,  1.04,  1.26,  1.48,
         1.68,  1.86,  2.02,  2.14,  2.22,
    ]
    n_ring = 24
    rings = []

    for y in ys:
        w = max(0.18, half_width_at_y(y))
        z_belt = lower_body_height_at_y(y)
        z_ctr = center_height_at_y(y)
        z_bot = 0.145 if (-2.05 < y < 2.02) else 0.175
        if y < -1.95:
            z_bot += 0.03 * ((-1.95 - y) / 0.30)
        if y > 1.90:
            z_bot += 0.08 * ((y - 1.90) / 0.35)

        ring_verts = []
        for k in range(n_ring):
            theta = (2.0 * math.pi * k) / n_ring
            sx = math.sin(theta)
            cz = math.cos(theta)
            u = abs(sx)

            if cz >= 0:
                x = sx * w * (1.0 - 0.04 * (cz ** 2))
                z_base = z_ctr * (cz ** 1.3) + z_belt * (1.0 - cz ** 1.3)
                z = z_base + 0.022 * math.sin(math.pi * u) + fender_crest_boost(y, u)
            else:
                t_low = -cz
                rocker_tuck = 1.0 - 0.10 * (t_low ** 1.8)
                x = sx * w * rocker_tuck
                z = z_belt * (1.0 - t_low ** 0.72) + z_bot * (t_low ** 0.72)

            ring_verts.append(bm.verts.new((x, y, z)))
        rings.append(ring_verts)

    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        for k in range(n_ring):
            kn = (k + 1) % n_ring
            bm.faces.new((r0[k], r0[kn], r1[kn], r1[k]))

    v_front = bm.verts.new((0.0, -2.275, 0.29))
    r_front = rings[0]
    for k in range(n_ring):
        kn = (k + 1) % n_ring
        bm.faces.new((v_front, r_front[kn], r_front[k]))

    v_rear = bm.verts.new((0.0, 2.265, 0.54))
    r_rear = rings[-1]
    for k in range(n_ring):
        kn = (k + 1) % n_ring
        bm.faces.new((v_rear, r_rear[k], r_rear[kn]))

    clean_bm(bm)
    me = bpy.data.meshes.new("Porsche_Body_Shell")
    bm.to_mesh(me)
    bm.free()

    obj = bpy.data.objects.new("Body_Shell", me)
    link_obj(obj, col)
    obj.data.materials.append(mats["M_CarPaint_Agate"])
    smooth_mesh(obj)
    apply_subsurf(obj, levels=2, render_levels=2)
    return obj


def build_cabin_greenhouse(col, mats):
    """
    Seamless Porsche 911 teardrop fastback greenhouse:
    tinted glass + flush carbon-fiber roof + sculpted A/C roof arch rails.
    """
    stations = [
        (-0.84, 0.72, 0.61, 0.79, 0.83, 0.022),
        (-0.60, 0.73, 0.62, 0.81, 0.99, 0.030),
        (-0.32, 0.73, 0.61, 0.83, 1.16, 0.036),
        (-0.08, 0.73, 0.60, 0.84, 1.26, 0.038),
        (0.22,  0.72, 0.58, 0.86, 1.285, 0.036),
        (0.54,  0.70, 0.55, 0.87, 1.24, 0.034),
        (0.86,  0.66, 0.51, 0.89, 1.14, 0.028),
        (1.18,  0.61, 0.46, 0.89, 1.02, 0.022),
        (1.48,  0.55, 0.41, 0.88, 0.93, 0.016),
        (1.66,  0.47, 0.33, 0.85, 0.88, 0.010),
    ]

    bm = bmesh.new()
    rings = []
    for (y, wb, wt, zb, zt, cr) in stations:
        pts_ring = [
            (-wb,        y, zb),
            (-wb * 0.94, y, zb + (zt - zb) * 0.45),
            (-wt,        y, zt - 0.015),
            (-wt * 0.55, y, zt + cr * 0.75),
            (0.0,        y, zt + cr),
            (wt * 0.55,  y, zt + cr * 0.75),
            (wt,         y, zt - 0.015),
            (wb * 0.94,  y, zb + (zt - zb) * 0.45),
            (wb,         y, zb),
            (0.0,        y, zb - 0.04),
        ]
        rings.append([bm.verts.new(p) for p in pts_ring])

    n_r = len(rings[0])
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        for k in range(n_r):
            kn = (k + 1) % n_r
            bm.faces.new((r0[k], r1[k], r1[kn], r0[kn]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    clean_bm(bm)

    me = bpy.data.meshes.new("Porsche_Greenhouse_Glass")
    bm.to_mesh(me)
    bm.free()
    glass_obj = bpy.data.objects.new("Greenhouse_Glass", me)
    link_obj(glass_obj, col)
    glass_obj.data.materials.append(mats["M_Glass_Tinted"])
    smooth_mesh(glass_obj)
    apply_subsurf(glass_obj, levels=2, render_levels=2)

    # Flush Carbon-Fiber Roof Panel (closed solid block hugging the exact roofline!)
    bm_r = bmesh.new()
    roof_stations = [
        (-0.30, 0.585, 1.168, 0.038),
        (-0.08, 0.585, 1.268, 0.040),
        (0.22,  0.565, 1.294, 0.038),
        (0.54,  0.535, 1.248, 0.035),
        (0.72,  0.510, 1.192, 0.030),
    ]
    r_rows = []
    for (y, wt, zt, cr) in roof_stations:
        row = []
        for s in (-1.0, -0.6, -0.25, 0.0, 0.25, 0.6, 1.0):
            x = s * wt
            bubble = cr * (1.0 - (s ** 2)) - 0.006 * math.exp(-((s / 0.28) ** 2))
            z = zt + bubble
            row.append(bm_r.verts.new((x, y, z)))
        r_rows.append(row)

    for i in range(len(r_rows) - 1):
        for j in range(len(r_rows[0]) - 1):
            bm_r.faces.new((r_rows[i][j], r_rows[i][j + 1], r_rows[i + 1][j + 1], r_rows[i + 1][j]))
    clean_bm(bm_r)

    me_r = bpy.data.meshes.new("Porsche_Roof_Panel")
    bm_r.to_mesh(me_r)
    bm_r.free()
    roof_obj = bpy.data.objects.new("Roof_Panel", me_r)
    link_obj(roof_obj, col)
    roof_obj.data.materials.append(mats["M_CarbonFiber"])
    sol = roof_obj.modifiers.new("Solidify", "SOLIDIFY")
    sol.thickness = 0.020
    sol.offset = -1.0
    smooth_mesh(roof_obj)
    apply_subsurf(roof_obj, levels=2, render_levels=2)

    # Sculpted A-Pillars & C-Pillars hugging the roof & glass cleanly
    bm_p = bmesh.new()
    for side in (-1.0, 1.0):
        rail_pts = [
            (side * 0.71, -0.82, 0.80),
            (side * 0.67, -0.56, 0.99),
            (side * 0.61, -0.28, 1.16),
            (side * 0.59,  0.00, 1.26),
            (side * 0.57,  0.30, 1.27),
            (side * 0.54,  0.62, 1.21),
            (side * 0.51,  0.96, 1.10),
            (side * 0.49,  1.28, 0.98),
            (side * 0.47,  1.56, 0.89),
        ]
        prev_ring = None
        for idx, pt in enumerate(rail_pts):
            p = Vector(pt)
            if idx == 0:
                tang = (Vector(rail_pts[1]) - p).normalized()
            elif idx == len(rail_pts) - 1:
                tang = (p - Vector(rail_pts[-2])).normalized()
            else:
                tang = (Vector(rail_pts[idx + 1]) - Vector(rail_pts[idx - 1])).normalized()
            up = Vector((0, 0, 1))
            right = tang.cross(up).normalized()
            up_ortho = right.cross(tang).normalized()
            w_rad = 0.036 + (0.048 if idx >= 5 else 0.0) * max(0.0, (idx - 4) / 4.0)
            h_rad = 0.025
            ring = []
            for a_i in range(8):
                ang = (2.0 * math.pi * a_i) / 8
                off = right * (math.cos(ang) * w_rad) + up_ortho * (math.sin(ang) * h_rad)
                ring.append(bm_p.verts.new(p + off))
            if prev_ring is not None:
                for a_i in range(8):
                    a_n = (a_i + 1) % 8
                    bm_p.faces.new((prev_ring[a_i], prev_ring[a_n], ring[a_n], ring[a_i]))
            else:
                bm_p.faces.new(list(reversed(ring)))
            if idx == len(rail_pts) - 1:
                bm_p.faces.new(ring)
            prev_ring = ring

    clean_bm(bm_p)
    me_p = bpy.data.meshes.new("Porsche_Roof_Pillars")
    bm_p.to_mesh(me_p)
    bm_p.free()
    pillars_obj = bpy.data.objects.new("Roof_Pillars", me_p)
    link_obj(pillars_obj, col)
    pillars_obj.data.materials.append(mats["M_CarPaint_Agate"])
    smooth_mesh(pillars_obj)
    apply_subsurf(pillars_obj, levels=1, render_levels=2)

    return glass_obj, roof_obj, pillars_obj


def _make_box(bm, center, size, rot=(0.0, 0.0, 0.0)):
    mat = Matrix.Translation(Vector(center)) @ Euler(rot, "XYZ").to_matrix().to_4x4() @ Matrix.Diagonal((*size, 1.0))
    bmesh.ops.create_cube(bm, size=1.0, matrix=mat)


def _make_cyl(bm, center, radius, depth, segs=24, rot=(0.0, 0.0, 0.0)):
    mat = Matrix.Translation(Vector(center)) @ Euler(rot, "XYZ").to_matrix().to_4x4()
    bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False, segments=segs,
        radius1=radius, radius2=radius, depth=depth, matrix=mat,
    )


def build_headlights(col, mats):
    """Bright chrome-reflector Porsche 911 oval headlights with forward-facing glowing 4-point LED DRLs."""
    bm_h = bmesh.new()
    bm_g = bmesh.new()
    bm_led = bmesh.new()

    for side in (-1.0, 1.0):
        # POSITIVE +X rotation (+46 deg) tilts local +Z FORWARD (-Y) straight out the nose!
        cx, cy, cz = side * 0.62, -1.85, 0.562
        rot = Euler((math.radians(46.0), math.radians(side * 10.0), math.radians(side * -10.0)), "XYZ").to_matrix().to_4x4()
        base_m = Matrix.Translation((cx, cy, cz)) @ rot

        # Bright silver/chrome reflector oval bowl
        bmesh.ops.create_uvsphere(
            bm_h, u_segments=24, v_segments=12, radius=1.0,
            matrix=base_m @ Matrix.Diagonal((0.145, 0.195, 0.044, 1.0))
        )
        # Central main LED projector orb
        bmesh.ops.create_uvsphere(
            bm_led, u_segments=16, v_segments=10, radius=1.0,
            matrix=base_m @ Matrix.Translation((0.0, 0.0, 0.044)) @ Matrix.Diagonal((0.052, 0.058, 0.024, 1.0))
        )
        # Signature Porsche 4-Point LED DRLs
        for dx, dy in ((-0.072, -0.084), (0.072, -0.084), (-0.072, 0.084), (0.072, 0.084)):
            bmesh.ops.create_uvsphere(
                bm_led, u_segments=12, v_segments=8, radius=1.0,
                matrix=base_m @ Matrix.Translation((dx, dy, 0.042)) @ Matrix.Diagonal((0.028, 0.032, 0.020, 1.0))
            )
        # Thin crystal glass lens dome
        bmesh.ops.create_uvsphere(
            bm_g, u_segments=24, v_segments=12, radius=1.0,
            matrix=base_m @ Matrix.Translation((0.0, 0.0, 0.020)) @ Matrix.Diagonal((0.154, 0.205, 0.056, 1.0))
        )

    out = []
    for name, bm, mat_key in [
        ("Headlights_Housing", bm_h, "M_Headlight_Reflector"),
        ("Headlights_Glass", bm_g, "M_Glass_Clear"),
        ("Headlights_DRL", bm_led, "M_LED_White"),
    ]:
        clean_bm(bm)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        obj = bpy.data.objects.new(name, me)
        link_obj(obj, col)
        obj.data.materials.append(mats[mat_key])
        smooth_mesh(obj)
        if name == "Headlights_Glass":
            obj.visible_shadow = False
        out.append(obj)
    return out


def build_hood_details(col, mats):
    """
    Flush 992 GT3 twin carbon hood vents, frunk panel shutlines, attached front carbon splitter,
    Porsche crest, and clean electric cobalt-blue motorsport accents (zero z-fighting!).
    """
    # 1) Twin GT3 Hood Nostril Vents (recessed flush into hood, clean manifold boxes)
    bm_v = bmesh.new()
    for side in (-1.0, 1.0):
        vx, vy = side * 0.22, -1.78
        vz = surface_z_on_hood(vx, vy) - 0.008
        rot = (math.radians(-17.0), 0.0, math.radians(side * -7.0))
        _make_box(bm_v, (vx, vy, vz), (0.20, 0.24, 0.036), rot)
    clean_bm(bm_v)
    me_v = bpy.data.meshes.new("Hood_Vents")
    bm_v.to_mesh(me_v)
    bm_v.free()
    vents = bpy.data.objects.new("Hood_Vents", me_v)
    link_obj(vents, col)
    vents.data.materials.append(mats["M_CarbonFiber"])
    smooth_mesh(vents)
    apply_bevel(vents, width=0.005, segments=2)

    # 2) Front Carbon Splitter (solidly attached into front lower bumper, zero floating!)
    bm_s = bmesh.new()
    n_pts = 20
    top_ring, bot_ring, top_in, bot_in = [], [], [], []
    for i in range(n_pts + 1):
        t = (i / n_pts) * math.pi
        x = math.cos(t) * 0.83
        y = -1.94 - math.sin(t) * 0.36
        top_ring.append(bm_s.verts.new((x, y, 0.225)))
        bot_ring.append(bm_s.verts.new((x, y, 0.160)))
        xi = math.cos(t) * 0.66
        yi = -1.68 - math.sin(t) * 0.24
        top_in.append(bm_s.verts.new((xi, yi, 0.240)))
        bot_in.append(bm_s.verts.new((xi, yi, 0.165)))

    for i in range(n_pts):
        bm_s.faces.new((top_ring[i], top_ring[i + 1], top_in[i + 1], top_in[i]))
        bm_s.faces.new((bot_in[i], bot_in[i + 1], bot_ring[i + 1], bot_ring[i]))
        bm_s.faces.new((top_ring[i + 1], top_ring[i], bot_ring[i], bot_ring[i + 1]))
        bm_s.faces.new((top_in[i], top_in[i + 1], bot_in[i + 1], bot_in[i]))
    bm_s.faces.new((top_ring[0], bot_ring[0], bot_in[0], top_in[0]))
    bm_s.faces.new((top_ring[-1], top_in[-1], bot_in[-1], bot_ring[-1]))
    clean_bm(bm_s)

    me_s = bpy.data.meshes.new("Front_Splitter")
    bm_s.to_mesh(me_s)
    bm_s.free()
    splitter = bpy.data.objects.new("Front_Splitter", me_s)
    link_obj(splitter, col)
    splitter.data.materials.append(mats["M_CarbonFiber"])
    smooth_mesh(splitter)
    apply_bevel(splitter, width=0.005, segments=2)

    # 3) Porsche Hood Crest
    bm_c = bmesh.new()
    cz = surface_z_on_hood(0.0, -2.06) + 0.004
    _make_box(bm_c, (0.0, -2.06, cz), (0.048, 0.064, 0.012), (math.radians(-26.0), 0.0, 0.0))
    clean_bm(bm_c)
    me_c = bpy.data.meshes.new("Porsche_Crest")
    bm_c.to_mesh(me_c)
    bm_c.free()
    crest = bpy.data.objects.new("Porsche_Crest", me_c)
    link_obj(crest, col)
    crest.data.materials.append(mats["M_Badge_Gold"])
    apply_bevel(crest, width=0.003, segments=2)

    # 4) Electric Cobalt Blue Motorsport Accents (closed manifold ribbons offset +8mm proud, zero z-fighting!)
    bm_a = bmesh.new()

    def add_closed_ribbon(pts_xyz, half_w=0.022, thick=0.007):
        top_l, top_r, bot_l, bot_r = [], [], [], []
        for x, y, z in pts_xyz:
            top_l.append(bm_a.verts.new((x - half_w, y, z + thick)))
            top_r.append(bm_a.verts.new((x + half_w, y, z + thick)))
            bot_l.append(bm_a.verts.new((x - half_w, y, z)))
            bot_r.append(bm_a.verts.new((x + half_w, y, z)))
        for i in range(len(pts_xyz) - 1):
            bm_a.faces.new((top_l[i], top_r[i], top_r[i + 1], top_l[i + 1]))
            bm_a.faces.new((bot_r[i], bot_l[i], bot_l[i + 1], bot_r[i + 1]))
            bm_a.faces.new((top_l[i + 1], bot_l[i + 1], bot_l[i], top_l[i]))
            bm_a.faces.new((top_r[i], bot_r[i], bot_r[i + 1], top_r[i + 1]))
        bm_a.faces.new((top_l[0], bot_l[0], bot_r[0], top_r[0]))
        bm_a.faces.new((top_r[-1], bot_r[-1], bot_l[-1], top_l[-1]))

    # Front motorsport tow strap attached to front splitter
    _make_box(bm_a, (0.28, -2.26, 0.215), (0.052, 0.16, 0.014), (0.0, 0.0, math.radians(-8.0)))

    # Twin motorsport stripes along frunk hood (offset +0.009m above hood surface)
    for sx in (-0.072, 0.072):
        pts_hood = [(sx, y, surface_z_on_hood(sx, y) + 0.009) for y in (-2.10, -1.94, -1.76, -1.56, -1.34, -1.10, -0.86)]
        add_closed_ribbon(pts_hood, half_w=0.022, thick=0.006)

    # Twin motorsport stripes across carbon roof (hugging roof curve cleanly)
    for sx in (-0.072, 0.072):
        pts_roof = [
            (sx, -0.26, 1.206),
            (sx, -0.08, 1.306),
            (sx,  0.22, 1.330),
            (sx,  0.54, 1.281),
            (sx,  0.68, 1.224),
        ]
        add_closed_ribbon(pts_roof, half_w=0.022, thick=0.006)

    clean_bm(bm_a)
    me_a = bpy.data.meshes.new("Motorsport_Blue_Accents")
    bm_a.to_mesh(me_a)
    bm_a.free()
    accents = bpy.data.objects.new("Motorsport_Blue_Accents", me_a)
    link_obj(accents, col)
    accents.data.materials.append(mats["M_Accent_CobaltBlue"])
    smooth_mesh(accents)

    return vents, splitter, crest, accents


def build_mirrors_and_wipers(col, mats):
    bm_m = bmesh.new()
    for side in (-1.0, 1.0):
        _make_box(bm_m, (side * 0.85, -0.56, 0.89), (0.16, 0.042, 0.030), (0.0, math.radians(side * -18.0), math.radians(side * 12.0)))
        m_cap = (
            Matrix.Translation((side * 0.98, -0.53, 0.925))
            @ Euler((0.0, 0.0, math.radians(side * 15.0)), "XYZ").to_matrix().to_4x4()
            @ Matrix.Diagonal((0.105, 0.070, 0.050, 1.0))
        )
        bmesh.ops.create_uvsphere(bm_m, u_segments=16, v_segments=10, radius=1.0, matrix=m_cap)
    clean_bm(bm_m)
    me_m = bpy.data.meshes.new("Side_Mirrors")
    bm_m.to_mesh(me_m)
    bm_m.free()
    mirrors = bpy.data.objects.new("Side_Mirrors", me_m)
    link_obj(mirrors, col)
    mirrors.data.materials.append(mats["M_CarPaint_Agate"])
    smooth_mesh(mirrors)

    bm_w = bmesh.new()
    _make_box(bm_w, (-0.26, -0.78, 0.852), (0.48, 0.015, 0.012), (0.0, 0.0, math.radians(6.0)))
    _make_box(bm_w, (0.26, -0.76, 0.862), (0.46, 0.015, 0.012), (0.0, 0.0, math.radians(-4.0)))
    clean_bm(bm_w)
    me_w = bpy.data.meshes.new("Wipers")
    bm_w.to_mesh(me_w)
    bm_w.free()
    wipers = bpy.data.objects.new("Wipers", me_w)
    link_obj(wipers, col)
    wipers.data.materials.append(mats["M_Trim_Black"])
    return mirrors, wipers


def build_rear_details(col, mats):
    # 1) Rear Engine Decklid Grille
    bm_g = bmesh.new()
    _make_box(bm_g, (0.0, 1.74, 0.880), (0.76, 0.36, 0.028), (math.radians(10.0), 0.0, 0.0))
    for i in range(-6, 7):
        _make_box(bm_g, (i * 0.056, 1.74, 0.900), (0.016, 0.34, 0.018), (math.radians(10.0), 0.0, 0.0))
    clean_bm(bm_g)
    me_g = bpy.data.meshes.new("Rear_Grille")
    bm_g.to_mesh(me_g)
    bm_g.free()
    grille = bpy.data.objects.new("Rear_Grille", me_g)
    link_obj(grille, col)
    grille.data.materials.append(mats["M_Trim_Black"])

    # 2) Full-Width 992 Crimson LED Light Bar
    bm_lb = bmesh.new()
    n_seg = 24
    prev_verts = None
    for i in range(n_seg + 1):
        u = -1.0 + 2.0 * (i / n_seg)
        x = u * 0.78
        y = 2.225 - 0.14 * (u ** 2)
        z = 0.745 - 0.025 * (u ** 2)
        v_top = bm_lb.verts.new((x, y, z + 0.018))
        v_bot = bm_lb.verts.new((x, y + 0.016, z - 0.018))
        if prev_verts is not None:
            bm_lb.faces.new((prev_verts[0], v_top, v_bot, prev_verts[1]))
        prev_verts = (v_top, v_bot)
    clean_bm(bm_lb)
    me_lb = bpy.data.meshes.new("Rear_Lightbar")
    bm_lb.to_mesh(me_lb)
    bm_lb.free()
    lightbar = bpy.data.objects.new("Rear_Lightbar", me_lb)
    link_obj(lightbar, col)
    lightbar.data.materials.append(mats["M_LED_Red"])
    sol = lightbar.modifiers.new("Solidify", "SOLIDIFY")
    sol.thickness = 0.022
    smooth_mesh(lightbar)

    # 3) Iconic 992 GT3 Swan-Neck Carbon Rear Wing
    bm_w = bmesh.new()
    n_span = 20
    span_rings = []
    for i in range(n_span + 1):
        u = -1.0 + 2.0 * (i / n_span)
        x = u * 0.84
        y_le = 1.98 + 0.04 * (u ** 2)
        chord = 0.29 - 0.03 * (u ** 2)
        z_mid = 1.15 + 0.018 * (1.0 - u ** 2)
        ring = [
            bm_w.verts.new((x, y_le,               z_mid + 0.005)),
            bm_w.verts.new((x, y_le + chord * 0.3, z_mid + 0.022)),
            bm_w.verts.new((x, y_le + chord * 0.7, z_mid + 0.024)),
            bm_w.verts.new((x, y_le + chord,       z_mid + 0.032)),
            bm_w.verts.new((x, y_le + chord * 0.6, z_mid - 0.006)),
            bm_w.verts.new((x, y_le + chord * 0.2, z_mid - 0.010)),
        ]
        span_rings.append(ring)

    for i in range(n_span):
        r0, r1 = span_rings[i], span_rings[i + 1]
        for k in range(6):
            kn = (k + 1) % 6
            bm_w.faces.new((r0[k], r1[k], r1[kn], r0[kn]))
    bm_w.faces.new(list(reversed(span_rings[0])))
    bm_w.faces.new(span_rings[-1])

    for side in (-1.0, 1.0):
        _make_box(bm_w, (side * 0.845, 2.15, 1.14), (0.016, 0.36, 0.145), (math.radians(-6.0), 0.0, 0.0))

    clean_bm(bm_w)
    me_w = bpy.data.meshes.new("Rear_Wing")
    bm_w.to_mesh(me_w)
    bm_w.free()
    wing = bpy.data.objects.new("Rear_Wing", me_w)
    link_obj(wing, col)
    wing.data.materials.append(mats["M_CarbonFiber"])
    smooth_mesh(wing)
    apply_bevel(wing, width=0.004, segments=2)

    # Swan-neck aluminum pylons
    bm_py = bmesh.new()
    for side in (-1.0, 1.0):
        _make_box(bm_py, (side * 0.30, 1.94, 1.03), (0.022, 0.12, 0.30), (math.radians(16.0), 0.0, 0.0))
        _make_box(bm_py, (side * 0.30, 2.05, 1.185), (0.024, 0.18, 0.024), (math.radians(-4.0), 0.0, 0.0))
    clean_bm(bm_py)
    me_py = bpy.data.meshes.new("Rear_Wing_Pylons")
    bm_py.to_mesh(me_py)
    bm_py.free()
    pylons = bpy.data.objects.new("Rear_Wing_Pylons", me_py)
    link_obj(pylons, col)
    pylons.data.materials.append(mats["M_Alloy_Satin"])
    apply_bevel(pylons, width=0.004, segments=2)

    # Cobalt Blue wing endplate top trim
    bm_we = bmesh.new()
    for side in (-1.0, 1.0):
        _make_box(bm_we, (side * 0.855, 2.15, 1.215), (0.014, 0.35, 0.016), (math.radians(-6.0), 0.0, 0.0))
    clean_bm(bm_we)
    me_we = bpy.data.meshes.new("Rear_Wing_BlueTrim")
    bm_we.to_mesh(me_we)
    bm_we.free()
    wing_trim = bpy.data.objects.new("Rear_Wing_BlueTrim", me_we)
    link_obj(wing_trim, col)
    wing_trim.data.materials.append(mats["M_Accent_CobaltBlue"])

    # Rear Diffuser & Twin Center GT3 Exhausts
    bm_d = bmesh.new()
    _make_box(bm_d, (0.0, 2.16, 0.24), (1.36, 0.28, 0.14), (math.radians(10.0), 0.0, 0.0))
    for fx in (-0.54, -0.36, -0.18, 0.18, 0.36, 0.54):
        _make_box(bm_d, (fx, 2.23, 0.21), (0.018, 0.20, 0.11), (math.radians(12.0), 0.0, 0.0))
    clean_bm(bm_d)
    me_d = bpy.data.meshes.new("Rear_Diffuser")
    bm_d.to_mesh(me_d)
    bm_d.free()
    diffuser = bpy.data.objects.new("Rear_Diffuser", me_d)
    link_obj(diffuser, col)
    diffuser.data.materials.append(mats["M_CarbonFiber"])

    bm_ex = bmesh.new()
    for ex in (-0.075, 0.075):
        _make_cyl(bm_ex, (ex, 2.27, 0.24), 0.044, 0.16, segs=20, rot=(math.radians(90.0), 0.0, 0.0))
    clean_bm(bm_ex)
    me_ex = bpy.data.meshes.new("Exhaust_Tips")
    bm_ex.to_mesh(me_ex)
    bm_ex.free()
    exhaust = bpy.data.objects.new("Exhaust_Tips", me_ex)
    link_obj(exhaust, col)
    exhaust.data.materials.append(mats["M_Alloy_Satin"])
    smooth_mesh(exhaust)

    return grille, lightbar, wing, pylons, wing_trim, diffuser, exhaust


def build_interior_and_rollcage(col, mats):
    bm_i = bmesh.new()
    _make_box(bm_i, (0.0, -0.45, 0.80), (1.28, 0.34, 0.18))
    for side in (-1.0, 1.0):
        _make_box(bm_i, (side * 0.33, 0.12, 0.72), (0.42, 0.42, 0.12))
        _make_box(bm_i, (side * 0.33, 0.34, 0.96), (0.40, 0.10, 0.50), (math.radians(-14.0), 0.0, 0.0))
    clean_bm(bm_i)
    me_i = bpy.data.meshes.new("Interior_Cabin")
    bm_i.to_mesh(me_i)
    bm_i.free()
    interior = bpy.data.objects.new("Interior_Cabin", me_i)
    link_obj(interior, col)
    interior.data.materials.append(mats["M_Interior_Alcantara"])

    bm_rc = bmesh.new()
    tubes = [
        ((-0.44, 0.62, 1.12), (0.44, 0.62, 1.12)),
        ((-0.44, 0.62, 1.12), (0.38, 1.24, 0.94)),
        ((0.44,  0.62, 1.12), (-0.38, 1.24, 0.94)),
        ((-0.44, 0.62, 1.12), (-0.42, 1.26, 0.92)),
        ((0.44,  0.62, 1.12), (0.42,  1.26, 0.92)),
    ]
    for p0, p1 in tubes:
        v0, v1 = Vector(p0), Vector(p1)
        mid = (v0 + v1) * 0.5
        vec = v1 - v0
        quat = vec.normalized().to_track_quat("Z", "Y")
        mat = Matrix.Translation(mid) @ quat.to_matrix().to_4x4()
        bmesh.ops.create_cone(
            bm_rc, cap_ends=True, cap_tris=False, segments=12,
            radius1=0.024, radius2=0.024, depth=vec.length, matrix=mat
        )
    clean_bm(bm_rc)
    me_rc = bpy.data.meshes.new("Roll_Cage")
    bm_rc.to_mesh(me_rc)
    bm_rc.free()
    rollcage = bpy.data.objects.new("Roll_Cage", me_rc)
    link_obj(rollcage, col)
    rollcage.data.materials.append(mats["M_Accent_CobaltBlue"])
    smooth_mesh(rollcage)
    return interior, rollcage


def build_wheels_and_brakes(col, mats):
    """
    Real 3D recessed GT3 center-lock wheels (zero z-fighting, zero floating!):
    Tire has a proper outer ring + recessed inner barrel; spokes & calipers sit cleanly inside.
    """
    bm_tire = bmesh.new()
    bm_rim = bmesh.new()
    bm_cal = bmesh.new()

    wheels = [
        (-0.80, -1.34, 0.340, 0.260),  # Front Left
        ( 0.80, -1.34, 0.340, 0.260),  # Front Right
        (-0.82,  1.16, 0.355, 0.305),  # Rear Left
        ( 0.82,  1.16, 0.355, 0.305),  # Rear Right
    ]

    for wx, wy, r, w in wheels:
        side = -1.0 if wx < 0 else 1.0
        rot_x = (0.0, math.radians(90.0), 0.0)

        # Real hollow torus-like tire profile (32 radial segs x 10 profile segs) -> NO flat cap z-fighting!
        n_rad, n_prof = 32, 10
        r_inner = r * 0.72
        r_mid = (r + r_inner) * 0.5
        r_tube_z = (r - r_inner) * 0.5
        r_tube_x = w * 0.5
        tire_rings = []
        for i in range(n_rad):
            ang = (2.0 * math.pi * i) / n_rad
            ca, sa = math.cos(ang), math.sin(ang)
            ring = []
            for j in range(n_prof):
                p_ang = (2.0 * math.pi * j) / n_prof
                px = math.cos(p_ang) * r_tube_x
                pr = r_mid + math.sin(p_ang) * r_tube_z
                ring.append(bm_tire.verts.new((wx + px, wy + ca * pr, r + sa * pr)))
            tire_rings.append(ring)
        for i in range(n_rad):
            r0, r1 = tire_rings[i], tire_rings[(i + 1) % n_rad]
            for j in range(n_prof):
                jn = (j + 1) % n_prof
                bm_tire.faces.new((r0[j], r1[j], r1[jn], r0[jn]))

        # Recessed alloy wheel hub & barrel (strictly inside r_inner so zero overlap with tire!)
        _make_cyl(bm_rim, (wx - side * 0.03, wy, r), r_inner * 0.96, w * 0.55, segs=24, rot=rot_x)
        # Center-lock nut
        _make_cyl(bm_rim, (wx + side * (w * 0.36), wy, r), r * 0.14, 0.05, segs=12, rot=rot_x)
        # 10 sleek GT3 spokes extending from center hub to outer lip
        for s_i in range(10):
            ang = (2.0 * math.pi * s_i) / 10
            dy = math.cos(ang) * (r_inner * 0.50)
            dz = math.sin(ang) * (r_inner * 0.50)
            _make_box(
                bm_rim,
                (wx + side * (w * 0.30), wy + dy, r + dz),
                (0.032, r_inner * 0.92, 0.022),
                (ang, 0.0, 0.0),
            )
        # Cobalt-blue brake caliper solidly overlapping the brake hub inside wheel well
        _make_box(bm_cal, (wx + side * (w * 0.14), wy + 0.12, r + 0.03), (0.095, 0.17, 0.12))

    out = []
    for name, bm, mat_key in [
        ("Wheels_Tires", bm_tire, "M_Rubber_Tire"),
        ("Wheels_Rims", bm_rim, "M_Alloy_Satin"),
        ("Brake_Calipers", bm_cal, "M_Accent_CobaltBlue"),
    ]:
        clean_bm(bm)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        obj = bpy.data.objects.new(name, me)
        link_obj(obj, col)
        obj.data.materials.append(mats[mat_key])
        smooth_mesh(obj)
        out.append(obj)
    return out


# ---------------------------------------------------------------------------
# Studio Lighting, World, Camera & Animation
# ---------------------------------------------------------------------------
def setup_studio_and_animation():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = (d.type == "METAL")

    scene.cycles.samples = 64
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.025
    scene.cycles.use_denoising = True
    scene.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 6
    scene.cycles.sample_clamp_indirect = 8.0
    scene.render.use_persistent_data = True

    scene.render.resolution_x = 720
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.frame_start = 1
    scene.frame_end = 109

    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"

    scene.view_settings.view_transform = "AgX"
    try:
        scene.view_settings.look = "AgX - Punchy"
    except TypeError:
        pass
    scene.view_settings.exposure = -0.30

    # World: Very dark studio reflections so the black car stays deep obsidian,
    # pure white for camera rays when film_transparent=False
    world = bpy.data.worlds.new("Studio_World")
    scene.world = world
    wnt = world.node_tree
    wnt.nodes.clear()
    out = wnt.nodes.new("ShaderNodeOutputWorld")
    mix = wnt.nodes.new("ShaderNodeMixShader")
    lp = wnt.nodes.new("ShaderNodeLightPath")
    bg_cam = wnt.nodes.new("ShaderNodeBackground")
    bg_cam.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bg_cam.inputs["Strength"].default_value = 1.0
    bg_env = wnt.nodes.new("ShaderNodeBackground")
    bg_env.inputs["Color"].default_value = (0.015, 0.018, 0.024, 1.0)
    bg_env.inputs["Strength"].default_value = 0.18
    wnt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    wnt.links.new(bg_env.outputs["Background"], mix.inputs[1])
    wnt.links.new(bg_cam.outputs["Background"], mix.inputs[2])
    wnt.links.new(mix.outputs["Shader"], out.inputs["Surface"])

    studio_col = get_or_create_collection("Studio_Rig")

    # Top-Down Telephoto Camera with subtle animated 3D parallax glide & pitch (matches Defender camera drift!)
    cam_data = bpy.data.cameras.new("Cam_TopDown")
    cam_data.lens = 150.0
    cam_data.sensor_width = 36.0
    cam_data.sensor_fit = "HORIZONTAL"
    cam_data.clip_start = 0.5
    cam_data.clip_end = 100.0
    cam_obj = bpy.data.objects.new("Cam_TopDown", cam_data)
    link_obj(cam_obj, studio_col)
    scene.camera = cam_obj

    # Subtle 3D overhead camera push-in & forward pitch across f1..f109
    cam_keys = [
        (1,   (0.0,  0.42, 18.1), math.radians(-1.4)),
        (30,  (0.0,  0.34, 17.9), math.radians(-1.1)),
        (60,  (0.0,  0.08, 17.4), math.radians(0.2)),
        (86,  (0.0, -0.22, 16.9), math.radians(1.5)),
        (109, (0.0, -0.45, 16.5), math.radians(2.5)),
    ]
    for f, loc, rx in cam_keys:
        cam_obj.location = loc
        cam_obj.rotation_euler = (rx, 0.0, 0.0)
        cam_obj.keyframe_insert("location", frame=f)
        cam_obj.keyframe_insert("rotation_euler", frame=f)

    # 3/4 Hero Preview Camera (for QA look-dev check)
    cam34_data = bpy.data.cameras.new("Cam_Hero34")
    cam34_data.lens = 75.0
    cam34_obj = bpy.data.objects.new("Cam_Hero34", cam34_data)
    link_obj(cam34_obj, studio_col)
    cam34_obj.location = (4.6, -5.2, 2.2)
    direction = Vector((0.0, 0.0, 0.58)) - cam34_obj.location
    cam34_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    def add_area(name, loc, rot_deg, sx, sy, energy, color=(1.0, 1.0, 1.0)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.shape = "RECTANGLE"
        ld.size = sx
        ld.size_y = sy
        ld.energy = energy
        ld.color = color
        lo = bpy.data.objects.new(name, ld)
        lo.location = loc
        lo.rotation_euler = tuple(math.radians(a) for a in rot_deg)
        link_obj(lo, studio_col)
        return lo, ld

    # Automotive studio softboxes: wide soft sweep for liquid-gunmetal hood gradients!
    key_obj, key_data = add_area("Light_Sweep_Key", (0.0, 3.2, 4.6), (18.0, 0.0, 0.0), 3.2, 2.2, 0.0, (0.98, 0.99, 1.0))
    rim_l_obj, rim_l_data = add_area("Light_Rim_Left", (-3.0, 0.2, 3.8), (0.0, -38.0, 0.0), 1.2, 6.4, 0.0, (0.90, 0.95, 1.0))
    rim_r_obj, rim_r_data = add_area("Light_Rim_Right", (3.0, 0.2, 3.8), (0.0, 38.0, 0.0), 1.2, 6.4, 0.0, (0.90, 0.95, 1.0))
    front_obj, front_data = add_area("Light_Front_Fill", (0.0, -3.4, 3.6), (-36.0, 0.0, 0.0), 2.8, 1.4, 0.0, (1.0, 1.0, 1.0))
    top_obj, top_data = add_area("Light_Top_Fill", (0.0, 0.0, 6.2), (0.0, 0.0, 0.0), 3.6, 5.2, 0.0, (0.96, 0.98, 1.0))

    # Continuous dark-to-gleaming automotive lighting sweep ALL the way through f109!
    light_keys = [
        # (frame, key_E, rim_E, front_E, top_E, key_y, key_rx_deg)
        (1,   0.0,    6.0,   0.0,   0.0,   3.4,  22.0),
        (29,  0.0,   10.0,   0.0,   0.0,   3.2,  20.0),
        (31,  65.0,  75.0,  25.0,  10.0,   2.8,  18.0),
        (42,  180.0, 180.0,  80.0,  35.0,  1.8,  12.0),
        (54,  360.0, 320.0, 180.0,  75.0,  0.6,   4.0),
        (68,  620.0, 480.0, 340.0, 140.0, -0.5,  -4.0),
        (84,  880.0, 620.0, 520.0, 210.0, -1.6, -12.0),
        (100, 1120.0, 740.0, 720.0, 280.0, -2.6, -18.0),
        (109, 1240.0, 800.0, 820.0, 320.0, -3.2, -22.0),
    ]

    for f, kE, rE, fE, tE, ky, krx in light_keys:
        key_data.energy = kE
        key_data.keyframe_insert("energy", frame=f)
        rim_l_data.energy = rE
        rim_l_data.keyframe_insert("energy", frame=f)
        rim_r_data.energy = rE
        rim_r_data.keyframe_insert("energy", frame=f)
        front_data.energy = fE
        front_data.keyframe_insert("energy", frame=f)
        top_data.energy = tE
        top_data.keyframe_insert("energy", frame=f)
        key_obj.location.y = ky
        key_obj.keyframe_insert("location", index=1, frame=f)
        key_obj.rotation_euler.x = math.radians(krx)
        key_obj.keyframe_insert("rotation_euler", index=0, frame=f)

    scene.frame_set(95)


def main():
    args = parse_cli()
    out_path = os.path.abspath(args.out)

    clear_scene()
    mats = make_materials()
    car_col = get_or_create_collection("Porsche_911")

    build_body_shell(car_col, mats)
    build_cabin_greenhouse(car_col, mats)
    build_headlights(car_col, mats)
    build_hood_details(car_col, mats)
    build_mirrors_and_wipers(car_col, mats)
    build_rear_details(car_col, mats)
    build_interior_and_rollcage(car_col, mats)
    build_wheels_and_brakes(car_col, mats)

    setup_studio_and_animation()

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out_path)
    print("PORSCHE_911_BUILT:", out_path)


if __name__ == "__main__":
    main()
