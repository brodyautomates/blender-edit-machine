# Shared studio for every Blender video: render settings, materials, geometry helpers, lights, halo, lens compositor.
# Loaded by shot.py with exec(), after VIDEO/SAMPLES/SCALE are set. Derived from build.py (the approved 15 s demo).
import bpy, bmesh, math, json, sys, os
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # the repo
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default=None, n=1):
    if name not in args: return default
    i = args.index(name)
    return args[i + 1] if n == 1 else args[i + 1:i + 1 + n]
SAMPLES = int(arg("--samples", "128"))
SCALE = int(arg("--scale", "100"))
# ---------- math ----------
def clamp01(x): return max(0.0, min(1.0, x))
def seg(f, a, b): return clamp01((f - a) / (b - a))
def lerp(a, b, k): return a + (b - a) * k
def decel(x): return 1 - (1 - clamp01(x)) ** 3
def ease(x):
    x = clamp01(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2
def spring(f, at_, k=170.0, c=20.0, m=0.8):
    if f < at_: return 0.0
    t = (f - at_) / 24.0
    w0 = math.sqrt(k / m); z = c / (2 * math.sqrt(k * m))
    if z < 1:
        wd = w0 * math.sqrt(1 - z * z)
        return 1 - math.exp(-z * w0 * t) * (math.cos(wd * t) + (z * w0 / wd) * math.sin(wd * t))
    return 1 - math.exp(-w0 * t) * (1 + w0 * t)
def hex2rgb(h, a=1.0):
    h = h.lstrip("#"); s = lambda c: (c / 255) ** 2.2
    return (s(int(h[0:2], 16)), s(int(h[2:4], 16)), s(int(h[4:6], 16)), a)

# ---------- scene ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
try:   # Metal on the Macs; Linux sandboxes have no GPU, so Cycles falls back to the CPU
    prefs.compute_device_type = "METAL"; prefs.get_devices()
    for d in prefs.devices: d.use = True
    sc.cycles.device = "GPU"
except Exception:
    sc.cycles.device = "CPU"
sc.cycles.samples = SAMPLES
sc.cycles.use_adaptive_sampling = True
sc.cycles.adaptive_threshold = 0.01
sc.cycles.use_denoising = True
sc.cycles.denoiser = "OPENIMAGEDENOISE"
sc.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
sc.cycles.denoising_prefilter = "ACCURATE"
BOUNCES = int(arg("--bounces", "16"))
sc.cycles.max_bounces = BOUNCES
sc.cycles.transmission_bounces = BOUNCES
sc.cycles.glossy_bounces = max(4, BOUNCES // 2)
sc.cycles.caustics_refractive = True
sc.cycles.caustics_reflective = False
sc.cycles.blur_glossy = 0.6
sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
sc.render.resolution_percentage = SCALE
sc.render.fps = 24
sc.render.use_motion_blur = True
sc.render.motion_blur_shutter = float(arg("--shutter", "0.35"))
sc.view_settings.view_transform = "AgX"
try: sc.view_settings.look = "AgX - Medium High Contrast"
except Exception: pass
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_depth = "16"
sc.render.film_transparent = False

world = bpy.data.worlds.new("void"); sc.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.0, 0.0, 0.0, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.0

def link(nt, a, b): nt.links.new(a, b)

# ---------- materials ----------
def mat_glass(name, tint=(0.96, 0.98, 1.0, 1), rough=0.02):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = tint
    p.inputs["Roughness"].default_value = rough
    p.inputs["IOR"].default_value = 1.5
    p.inputs["Transmission Weight"].default_value = 1.0
    p.inputs["Coat Weight"].default_value = 0.6
    p.inputs["Coat Roughness"].default_value = 0.01
    return m

def mat_floor():
    m = bpy.data.materials.new("floor"); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (0.001, 0.001, 0.0015, 1)
    p.inputs["Roughness"].default_value = 0.72
    p.inputs["Specular IOR Level"].default_value = 0.14
    return m

def mat_crt(name, img_path, strength=3.2, pitch_lines=640, mask=True, seq_last=None):
    """CRT display: image -> scanlines x RGB phosphor mask -> emission. Alpha punches holes (transparent).
    seq_last: the path is the first file of a sequence numbered by the edit's frames, ending at seq_last."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N = nt.nodes
    N.clear()
    out = N.new("ShaderNodeOutputMaterial")
    tex = N.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(img_path); tex.interpolation = "Cubic"
    tex.image.colorspace_settings.name = "sRGB"
    if seq_last is not None:
        tex.image.source = "SEQUENCE"
        iu = tex.image_user; iu.frame_start = 1; iu.frame_offset = 0; iu.frame_duration = seq_last; iu.use_auto_refresh = True; iu.use_cyclic = False
    uv = N.new("ShaderNodeTexCoord")
    link(nt, uv.outputs["UV"], tex.inputs["Vector"])
    # scanlines: a soft sine along V, about `pitch_lines` lines over the screen
    sep = N.new("ShaderNodeSeparateXYZ"); link(nt, uv.outputs["UV"], sep.inputs[0])
    mv = N.new("ShaderNodeMath"); mv.operation = "MULTIPLY"; mv.inputs[1].default_value = pitch_lines * math.pi
    link(nt, sep.outputs["Y"], mv.inputs[0])
    sn = N.new("ShaderNodeMath"); sn.operation = "SINE"; link(nt, mv.outputs[0], sn.inputs[0])
    sl = N.new("ShaderNodeMapRange"); sl.inputs["From Min"].default_value = -1; sl.inputs["To Min"].default_value = 0.72; sl.inputs["To Max"].default_value = 1.06
    link(nt, sn.outputs[0], sl.inputs["Value"])
    col = tex.outputs["Color"]
    lines = N.new("ShaderNodeMixRGB"); lines.blend_type = "MULTIPLY"; lines.inputs[0].default_value = 1
    link(nt, col, lines.inputs[1]); link(nt, sl.outputs[0], lines.inputs[2])
    last = lines.outputs[0]
    if mask:
        # RGB phosphor triads along U (only resolves up close)
        mu = N.new("ShaderNodeMath"); mu.operation = "MULTIPLY"; mu.inputs[1].default_value = pitch_lines * 1.25 * 2 * math.pi
        link(nt, sep.outputs["X"], mu.inputs[0])
        comb = N.new("ShaderNodeCombineColor")
        for k, ch in enumerate(["Red", "Green", "Blue"]):
            a = N.new("ShaderNodeMath"); a.operation = "ADD"; a.inputs[1].default_value = k * 2 * math.pi / 3
            link(nt, mu.outputs[0], a.inputs[0])
            s2 = N.new("ShaderNodeMath"); s2.operation = "SINE"; link(nt, a.outputs[0], s2.inputs[0])
            r = N.new("ShaderNodeMapRange"); r.inputs["From Min"].default_value = -1; r.inputs["To Min"].default_value = 0.78; r.inputs["To Max"].default_value = 1.12
            link(nt, s2.outputs[0], r.inputs["Value"]); link(nt, r.outputs[0], comb.inputs[ch])
        mk = N.new("ShaderNodeMixRGB"); mk.blend_type = "MULTIPLY"; mk.inputs[0].default_value = 1
        link(nt, last, mk.inputs[1]); link(nt, comb.outputs[0], mk.inputs[2]); last = mk.outputs[0]
    em = N.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = strength
    link(nt, last, em.inputs["Color"])
    tr = N.new("ShaderNodeBsdfTransparent")
    mix = N.new("ShaderNodeMixShader"); link(nt, tex.outputs["Alpha"], mix.inputs[0]); link(nt, tr.outputs[0], mix.inputs[1]); link(nt, em.outputs[0], mix.inputs[2])
    link(nt, mix.outputs[0], out.inputs["Surface"])
    m["strength_node"] = em.name
    return m

def mat_emit(name, color, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; N.clear()
    out = N.new("ShaderNodeOutputMaterial")
    p = N.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = color; p.inputs["Roughness"].default_value = 0.25
    p.inputs["Emission Color"].default_value = color; p.inputs["Emission Strength"].default_value = strength
    p.inputs["Coat Weight"].default_value = 0.4
    link(nt, p.outputs[0], out.inputs["Surface"])
    return m

def mat_black(name="black"):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]; p.inputs["Base Color"].default_value = (0.002, 0.002, 0.003, 1); p.inputs["Roughness"].default_value = 0.6
    return m

# ---------- geometry ----------
def slab(name, w, h, d, bevel, mat, loc=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    o = bpy.context.active_object; o.name = name
    o.scale = (w, d, h); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    o.location = loc  # positioned after baking, so animation sets absolute positions
    b = o.modifiers.new("bevel", "BEVEL"); b.width = bevel; b.segments = 6; b.limit_method = "NONE"; b.harden_normals = False
    bpy.ops.object.shade_smooth()
    o.data.materials.append(mat)
    return o

def plane(name, w, h, mat, loc=(0, 0, 0), rot=(math.radians(90), 0, 0)):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0), rotation=rot)
    o = bpy.context.active_object; o.name = name
    o.scale = (w, h, 1); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    o.location = loc
    o.data.materials.append(mat)
    return o

def rounded_plane(name, w, h, r, mat, loc=(0, 0, 0)):
    """a flat rounded rectangle in X/Z facing -Y, UVs spanning its bounds, so images get clean rounded corners"""
    r = max(0.0, min(r, w / 2 - 1e-4, h / 2 - 1e-4))
    pts = []
    for cx, cz, a0 in [(w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)]:
        for k in range(17):
            a = math.radians(a0 + k * 90 / 16)
            pts.append((cx + math.cos(a) * r, cz + math.sin(a) * r))
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    vs = [bm.verts.new((x, 0, z)) for x, z in pts]
    f = bm.faces.new(vs); f.normal_update()
    if f.normal.y > 0: f.normal_flip()
    uvl = bm.loops.layers.uv.new("UVMap")
    for lp in f.loops:
        x, _, z = lp.vert.co; lp[uvl].uv = ((x + w / 2) / w, (z + h / 2) / h)
    bmesh.ops.triangulate(bm, faces=[f])
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    o.data.materials.append(mat); o.location = loc
    return o

def rounded_slab(name, w, h, d, r, mat, loc=(0, 0, 0), edge=0.0025):
    """UI-style glass: a rounded rectangle in X/Z (facing -Y), solidified to depth d, with a small edge bevel
    so every edge catches the strip lights."""
    r = min(r, w / 2 - 1e-4, h / 2 - 1e-4)
    pts = []
    for cx, cz, a0 in [(w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)]:
        for k in range(13):
            a = math.radians(a0 + k * 7.5)
            pts.append((cx + math.cos(a) * r, cz + math.sin(a) * r))
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    vs = [bm.verts.new((x, 0, z)) for x, z in pts]
    bm.faces.new(vs); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    s = o.modifiers.new("solid", "SOLIDIFY"); s.thickness = d; s.offset = 0
    bv = o.modifiers.new("bevel", "BEVEL"); bv.width = min(edge, d * 0.4); bv.segments = 4; bv.limit_method = "ANGLE"; bv.angle_limit = math.radians(60)
    for p_ in o.data.polygons: p_.use_smooth = True
    o.data.materials.append(mat)
    o.location = loc
    return o

def mat_glass_small(name):
    m = mat_glass(name, tint=(0.32, 0.34, 0.38, 1), rough=0.09)  # smoked: a thin slab stops piping light into a white glow
    p = m.node_tree.nodes["Principled BSDF"]; p.inputs["Coat Weight"].default_value = 0.0; p.inputs["Specular IOR Level"].default_value = 0.35
    return m

def screen_card(name, w, h, d, r, img, strength, lines, loc, seq_last=None, mask=True, glass=None, back=True):
    """A glass card with a CRT face just behind its front surface and a black backing behind that."""
    g = rounded_slab(name, w, h, d, r, glass or (mat_glass_small(name + "_g") if w < 0.5 else mat_glass(name + "_g")), loc)
    face = rounded_plane(name + "_face", w - 0.012, h - 0.012, max(0.0, r - 0.006), mat_crt(name + "_crt", img, strength, lines, mask, seq_last), (loc[0], loc[1] - d / 2 + 0.0022, loc[2]))
    parent(face, g)
    if back:
        bk = rounded_plane(name + "_back", w - 0.008, h - 0.008, max(0.0, r - 0.004), mat_black(name + "_k"), (loc[0], loc[1] + d / 2 - 0.0015, loc[2]))
        parent(bk, g)
    return g

def parent(child, par):
    bpy.context.view_layer.update()   # matrices must be current, or the child's offset is applied twice
    child.parent = par
    child.matrix_parent_inverse = par.matrix_world.inverted()

RAYS = [1, 0.8, 0.94, 0.72, 1, 0.84, 0.9, 0.75, 0.98, 0.79, 0.88, 0.7]
def spark_mesh(R=0.07, depth=0.012):
    pts = []
    n = len(RAYS); inner = R * 0.2
    for i in range(n):
        a = i / n * 2 * math.pi + (0.06 if i % 2 else -0.05)
        a0, a1 = a - math.pi / n * 0.55, a + math.pi / n * 0.55
        tip = R * RAYS[i]
        p0 = (math.cos(a0) * inner, math.sin(a0) * inner)
        pt = (math.cos(a) * tip, math.sin(a) * tip)
        p1 = (math.cos(a1) * inner, math.sin(a1) * inner)
        c0 = (math.cos(a - 0.05) * tip * 0.72, math.sin(a - 0.05) * tip * 0.72)
        c1 = (math.cos(a + 0.05) * tip * 0.72, math.sin(a + 0.05) * tip * 0.72)
        for t in [0, 0.25, 0.5, 0.75]:
            pts.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c0[0] + t * t * pt[0], (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c0[1] + t * t * pt[1]))
        for t in [0, 0.25, 0.5, 0.75]:
            pts.append(((1 - t) ** 2 * pt[0] + 2 * (1 - t) * t * c1[0] + t * t * p1[0], (1 - t) ** 2 * pt[1] + 2 * (1 - t) * t * c1[1] + t * t * p1[1]))
    me = bpy.data.meshes.new("spark"); bm = bmesh.new()
    vs = [bm.verts.new((x, 0, y)) for x, y in pts]
    bm.faces.new(vs); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("spark", me); sc.collection.objects.link(o)
    s = o.modifiers.new("solid", "SOLIDIFY"); s.thickness = depth; s.offset = 0
    b = o.modifiers.new("bevel", "BEVEL"); b.width = 0.0022; b.segments = 4; b.limit_method = "ANGLE"
    o.data.materials.append(mat_emit("spark", hex2rgb("#d97757"), 3.6))
    for p_ in o.data.polygons: p_.use_smooth = True
    return o

def area(name, w, h, energy, loc, target, color=(1, 1, 1)):
    l = bpy.data.lights.new(name, "AREA"); l.shape = "RECTANGLE"; l.size = w; l.size_y = h; l.energy = energy; l.color = color
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
    d = Vector(target) - Vector(loc); o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return o

def camera(lens, fstop):
    c = bpy.data.cameras.new("cam"); c.lens = lens; c.sensor_fit = "VERTICAL"; c.sensor_height = 36.0
    c.dof.use_dof = True; c.dof.aperture_fstop = max(fstop, float(arg("--fmin", "2.8"))); c.dof.aperture_blades = 0; c.clip_start = 0.02
    o = bpy.data.objects.new("cam", c); sc.collection.objects.link(o); sc.camera = o
    focus = bpy.data.objects.new("focus", None); sc.collection.objects.link(focus); c.dof.focus_object = focus
    return o, focus

def aim(o, pos, target, roll=0.0):
    o.location = pos
    d = Vector(target) - Vector(pos)
    q = d.to_track_quat("-Z", "Y"); o.rotation_euler = q.to_euler()
    o.rotation_euler.rotate_axis("Z", roll)

def orbit(az, el, dist, target):
    az, el = math.radians(az), math.radians(el)
    return (target[0] + math.sin(az) * math.cos(el) * dist, target[1] - math.cos(az) * math.cos(el) * dist, target[2] + math.sin(el) * dist)

# ---------- studio ----------
# no floor: the hero floats in a void with a halo behind it (a floor reflected the strip lights into the caption band)
area("softbox", 2.6, 1.4, 200, (0.3, 0.9, 3.2), (0, 0, 0.7))  # above and behind: front glass never mirrors it
area("stripL", 0.06, 2.6, 260, (-1.3, 0.6, 0.9), (0, 0, 0.75))
area("stripR", 0.06, 2.6, 320, (1.4, 0.9, 1.0), (0, 0, 0.75))
area("kicker", 1.6, 0.5, 60, (0, 1.6, 1.5), (0, 0, 0.7))
# the halo: a soft radial glow card far behind the hero (no wall, so no horizon line)
glow_m = bpy.data.materials.new("halo"); glow_m.use_nodes = True; gnt = glow_m.node_tree; gN = gnt.nodes; gN.clear()
g_out = gN.new("ShaderNodeOutputMaterial"); g_em = gN.new("ShaderNodeEmission"); g_em.inputs["Color"].default_value = (0.55, 0.62, 0.78, 1)
g_tc = gN.new("ShaderNodeTexCoord"); g_grad = gN.new("ShaderNodeTexGradient"); g_grad.gradient_type = "SPHERICAL"
g_map = gN.new("ShaderNodeMapping"); g_map.inputs["Location"].default_value = (0, 0, 0); g_map.inputs["Scale"].default_value = (2.15, 2.15, 1)  # falloff reaches zero inside the card, so no edge
link(gnt, g_tc.outputs["Object"], g_map.inputs["Vector"]); link(gnt, g_map.outputs["Vector"], g_grad.inputs["Vector"])
g_pow = gN.new("ShaderNodeMath"); g_pow.operation = "POWER"; g_pow.inputs[1].default_value = 2.4; link(gnt, g_grad.outputs["Fac"], g_pow.inputs[0])
g_mul = gN.new("ShaderNodeMath"); g_mul.operation = "MULTIPLY"; g_mul.inputs[1].default_value = 0.32; link(gnt, g_pow.outputs[0], g_mul.inputs[0])
link(gnt, g_mul.outputs[0], g_em.inputs["Strength"]); link(gnt, g_em.outputs[0], g_out.inputs["Surface"])
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0), rotation=(math.radians(90), 0, 0)); halo_card = bpy.context.active_object
halo_card.scale = (1, 1, 1); halo_card.location = (0.25, 2.6, 1.05); halo_card.scale = (3.4, 3.4, 1); halo_card.data.materials.append(glow_m)
halo_card.visible_glossy = False  # glows behind the hero without painting a disc into the floor

# ---------- the compositor: phosphor bloom + edge-only dispersion ----------
sc.use_nodes = True
tree = sc.node_tree; tree.nodes.clear()
rl = tree.nodes.new("CompositorNodeRLayers")
glare = tree.nodes.new("CompositorNodeGlare")
try: glare.glare_type = "BLOOM"
except Exception: glare.glare_type = "FOG_GLOW"
glare.quality = "HIGH"; glare.threshold = 1.2; glare.mix = -0.82
try: glare.size = 7
except Exception: pass
lens = tree.nodes.new("CompositorNodeLensdist"); lens.inputs["Dispersion"].default_value = float(arg("--disp", "0")); lens.use_fit = True
comp = tree.nodes.new("CompositorNodeComposite")
tree.links.new(rl.outputs["Image"], glare.inputs["Image"]); tree.links.new(glare.outputs["Image"], lens.inputs["Image"]); tree.links.new(lens.outputs["Image"], comp.inputs["Image"])

