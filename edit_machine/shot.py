# One shot of a video, rendered in Blender from the project's spec.py. Called by render.py; you rarely run it yourself.
#   blender -b -P edit_machine/shot.py -- --project projects/example --shot 2 --still mid --samples 16 --scale 40
import os, sys, json, re, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, "engine.py")).read())   # the studio, materials, helpers and args (arg, SAMPLES, SCALE)
sys.path.insert(0, HERE)

PROJECT = os.path.abspath(arg("--project")); SHOT_I = int(arg("--shot", "0")); STILL = arg("--still"); RANGE = arg("--range", None, 2)
_m = importlib.util.spec_from_file_location("spec", os.path.join(PROJECT, "spec.py")); SPEC = importlib.util.module_from_spec(_m); _m.loader.exec_module(SPEC)
UI = os.path.join(PROJECT, "ui")
WORDS = json.load(open(os.path.join(PROJECT, "timing.json")))
_norm = lambda s: re.sub(r"[^a-z0-9']", "", str(s).lower())

def word_index(c):
    """a cue: a word index, a word ("agents"), the n-th time a word is said ("agents#2"), or [cue, frame offset]"""
    if isinstance(c, int): return c
    w, _, n = str(c).partition("#"); n = int(n or 1); hits = [i for i, x in enumerate(WORDS) if _norm(x["w"]) == _norm(w)]
    if len(hits) < n: raise SystemExit(f"cue '{c}': the voiceover says '{w}' {len(hits)} time(s)")
    return hits[n - 1]

def at(c):
    """the edit frame of a cue (24 fps from the first sample of the voiceover)"""
    if isinstance(c, (list, tuple)): return round(WORDS[word_index(c[0])]["t0"] * 24) + c[1]
    return round(WORDS[word_index(c)]["t0"] * 24)

def bounds(shots, total):
    starts = [0] + [at(s["cue"]) - 2 for s in shots[1:]]
    return [(starts[i], (starts[i + 1] - 1) if i + 1 < len(starts) else total - 1) for i in range(len(shots))]


def total_frames(words): return round(words[-1]["t1"] * 24) + 14
TOTAL = total_frames(WORDS)
S = SPEC.SHOTS[SHOT_I]
F0, F1 = bounds(SPEC.SHOTS, TOTAL)[SHOT_I]
CZ = 0.78
face = lambda n: os.path.join(UI, f"{n}.png")
def aspect(n):
    im = bpy.data.images.load(face(n), check_existing=True); return im.size[1] / im.size[0]

def seq_face(n):
    """a face that changes over the edit (typing): ui/NN/<n>_seq/f_####.png numbered by edit frame"""
    d = os.path.join(UI, f"{n}_seq"); first = sorted(os.listdir(d))[0]
    return os.path.join(d, first), int(first[2:6])

def glossy_hidden(o):
    """hide a face from any ray that has reflected (stops ghost duplicates in the glass behind it)"""
    o.visible_glossy = False
    nt = o.data.materials[0].node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"); src = out.inputs["Surface"].links[0].from_socket
    lp = nt.nodes.new("ShaderNodeLightPath"); gt = nt.nodes.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 0.5
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader")
    link(nt, lp.outputs["Glossy Depth"], gt.inputs[0]); link(nt, gt.outputs[0], mx.inputs[0])
    link(nt, src, mx.inputs[1]); link(nt, tr.outputs[0], mx.inputs[2]); link(nt, mx.outputs[0], out.inputs["Surface"])

_rad = {}
def face_radius(n, w, default):
    """the face's own corner radius (from its alpha: first opaque pixel along the top row), in metres at width w"""
    if n not in _rad:
        im = bpy.data.images.load(face(n), check_existing=True); W_, H_ = im.size
        px = im.pixels[:]; row = (H_ - 1) * W_ * 4  # Blender rows start at the bottom
        x0 = next((x for x in range(W_ // 2) if px[row + x * 4 + 3] > 0.05), 0)
        _rad[n] = x0 / W_
    k = _rad[n] * w
    return k if k > 0.004 else default

def glass_card(name, n, w, loc, r=None, strength=2.2, lines=None, small=None, back=True, seq=None):
    """a CRT face under glass; size from the face's aspect. Returns the glass object (face parented)."""
    h = w * aspect(n)
    r = r if r is not None else face_radius(n, w, min(w, h) * 0.06)
    small = small if small is not None else w < 0.5
    lines = lines or max(60, int(h * 300))
    g = rounded_slab(name, w, h, 0.016 if not small else 0.012, r, mat_glass_small(name + "_g") if small else mat_glass(name + "_g"), loc)
    img, last = (face(n), None) if seq is None else seq
    fc = rounded_plane(name + "_face", w - 0.012, h - 0.012, max(0.0, r - 0.006), mat_crt(name + "_crt", img, strength, lines, not small, last), (loc[0], loc[1] - 0.008 + 0.0022, loc[2]))
    parent(fc, g)
    if seq is not None:
        tex = next(nd for nd in fc.data.materials[0].node_tree.nodes if nd.type == "TEX_IMAGE")
        tex.image_user.frame_duration = TOTAL + 2
    if back:
        bk = rounded_plane(name + "_back", w - 0.008, h - 0.008, max(0.0, r - 0.004), mat_black(name + "_k"), (loc[0], loc[1] + 0.0065, loc[2])); parent(bk, g)
    g["face"] = fc.name; g["h"] = h
    return g

def power_on(card, f, t0, strength):
    """CRT power-on: a bright line opening vertically, overdriven for a few frames"""
    fc = bpy.data.objects[card["face"]]
    on = seg(f, t0, t0 + 9)
    fc.scale = (1, 1, max(0.004, decel(on)))
    m = fc.data.materials[0]; em = m.node_tree.nodes[m["strength_node"]]
    em.inputs["Strength"].default_value = strength * (1 + 3 * (1 - seg(f, t0 + 2, t0 + 10)))

def lens_dist(w_needed, lens, fill=1.0):
    return w_needed / fill * lens / 20.25   # 20.25 mm = the 9:16 sensor's width at 36 mm tall

def cam_path(cam, preset, k, target, dist):
    """motivated, slow moves; k runs 0..1 over the shot"""
    k = ease(k)
    p = {"arcL": ((-34, -3), (-22, -5), 1.0, 0.94), "arcR": ((32, -3), (20, -5), 1.0, 0.94),
         "push": ((7, -2), (3, -3), 1.0, 0.86), "low": ((-22, -13), (-12, -8), 1.0, 0.95),
         "high": ((16, 16), (8, 11), 1.0, 0.94), "slideL": ((18, -4), (-10, -4), 0.98, 0.98)}[preset]
    (a0, e0), (a1, e1), d0, d1 = p
    pos = orbit(lerp(a0, a1, k), lerp(e0, e1, k), dist * lerp(d0, d1, k), target)
    aim(cam, pos, target)

def spark_rise(f, t0, at_xyz=(0.0, -0.1, CZ + 0.55), energy=100):
    sp = spark_mesh(0.075, 0.014)
    spl = bpy.data.lights.new("sparklight", "POINT"); spl.energy = 0; spl.color = hex2rgb("#ff9a6b")[:3]; spl.shadow_soft_size = 0.04
    spo = bpy.data.objects.new("sparklight", spl); sc.collection.objects.link(spo)
    def upd(f):
        s = spring(f, t0, 150, 12)
        sp.scale = (max(0.0001, s),) * 3
        sp.location = (lerp(at_xyz[0] + 0.15, at_xyz[0], s), lerp(at_xyz[1] + 0.4, at_xyz[1], s), lerp(at_xyz[2] - 0.45, at_xyz[2], s))
        sp.rotation_euler = (0, -2.1 * (1 - s), 0)
        spo.location = (sp.location.x, sp.location.y - 0.06, sp.location.z); spl.energy = energy * s
    return upd, sp

def lifts(spec, screen_front_y, base_z):
    """floating glass widgets that lift off the screen toward camera on their cue words"""
    objs = []
    for i, L in enumerate(spec):
        g = glass_card(f"lift{i}", L["face"], L.get("w", 0.42), (0, 0, 0), strength=L.get("strength", 2.0))
        glossy_hidden(bpy.data.objects[g["face"]])
        objs.append((L, g))
    def upd(f):
        latest = None
        for L, g in objs:
            t = at(L["at"])
            if f < t - 1: g.scale = (0.0001,) * 3; continue
            s = spring(f, t - 1, 160, 15)
            latest = g
            g.scale = (lerp(0.94, 1, s),) * 3
            g.location = (L.get("x", 0), screen_front_y - 0.004 - L.get("dy", 0.12) * s, base_z + L.get("z", 0))
            g.rotation_euler = (math.radians(L.get("rx", 4)) * s, 0, math.radians(L.get("rz", 0)) * s)
        return latest
    return upd, objs

# =====================================================================================================
# templates
# =====================================================================================================

# ====================================================================================================
# templates: screen, stack, strike, prompt, cta
# ====================================================================================================
def T_screen(S):
    """the hero: one glass CRT screen, optional floating widgets, optional Claude spark"""
    W = S.get("w", 1.04)
    hero = glass_card("hero", S["face"], W, (0, 0, CZ), r=0.034, strength=S.get("strength", 2.6),
                      seq=seq_face(S["face"]) if S.get("seq") else None)
    H = hero["h"]
    up_l, objs = lifts(S.get("lifts", []), -0.008, CZ)
    up_s = spark_rise(None, at(S["spark"]), (S.get("spark_x", 0.0), -0.12, CZ + H / 2 + 0.16))[0] if "spark" in S else None
    lens = S.get("lens", 85); cam, focus = camera(lens, S.get("fstop", 2.0))
    dist = lens_dist(max(W, H * 9 / 16 * 1.0), lens, S.get("fill", 0.78))
    def update(f):
        if S.get("power", True): power_on(hero, f, F0, S.get("strength", 2.6))
        latest = up_l(f)
        if up_s: up_s(f)
        cam_path(cam, S.get("move", "arcL"), seg(f, F0, F1 + 1), (S.get("tx", 0.0), 0, CZ + S.get("tz", -0.1)), dist)
        tgt = Vector((0, -0.008, CZ)) if latest is None else Vector(latest.location)
        focus.location = tgt
    return update

def T_stack(S):
    """a row/column/fan of glass cards that arrive one by one on their words; the camera travels with them"""
    cards = S["cards"]; n = len(cards); lay = S.get("layout", "row")
    W = S.get("w", 0.5); gap = S.get("gap", 0.08)
    objs = []
    for i, c in enumerate(cards):
        if lay == "row": home = ((i - (n - 1) / 2) * (W + gap), (i % 2) * 0.05, CZ)
        elif lay == "column": home = (0, (i % 2) * 0.03, CZ + ((n - 1) / 2 - i) * (S.get("ch", 0.16) + gap * 0.5))
        else:  # grid of 2 columns
            home = ((i % 2 - 0.5) * (W + gap), 0, CZ + ((n - 1) // 2 / 2 - i // 2) * (S.get("ch", 0.2) + gap))
        g = glass_card(f"card{i}", c["face"], W, home, strength=c.get("strength", 2.2))
        objs.append((c, g, home))
    base = None
    if "base" in S:
        base = glass_card("base", S["base"], S.get("base_w", 1.0), (0, 0.22, CZ), strength=2.0)
    lens = S.get("lens", 50); cam, focus = camera(lens, S.get("fstop", 2.0))
    span_w = (n * (W + gap)) if lay == "row" else (W * 2 + gap if lay == "grid" else W)
    span_h = n * (S.get("ch", 0.16) + gap * 0.5) if lay == "column" else ((n + 1) // 2 * (S.get("ch", 0.2) + gap) if lay == "grid" else W * 1.8)
    # fit the whole layout (width with room for the orbit, and height so it clears the caption band)
    need = max(min(span_w, S.get("view_w", 1.1)) * 1.18, span_h * 9 / 16 * 2.3)
    dist = lens_dist(need, lens, S.get("fill", 0.92))
    def update(f):
        latest = None
        for c, g, home in objs:
            t = at(c["at"])
            # cards wait dimly in their slots from the first frame, then light up and spring forward on their word
            s = spring(f, t - 2, 150, 15) if f >= t - 2 else 0.0
            if f >= t - 2: latest = (g, home)
            g.scale = (lerp(0.94, 1, s),) * 3
            g.location = (home[0], home[1] + 0.12 * (1 - s), home[2])
            g.rotation_euler = (0, 0, math.radians(c.get("rz", 0)) * s)
            fc = bpy.data.objects[g["face"]]; m = fc.data.materials[0]
            m.node_tree.nodes[m["strength_node"]].inputs["Strength"].default_value = c.get("strength", 2.2) * lerp(0.07, 1.0, min(1.0, s * 1.4))
        k = seg(f, F0, F1 + 1)
        if lay == "row" and span_w > S.get("view_w", 1.1):
            first, last = objs[0][2][0], objs[-1][2][0]
            tx = lerp(first * 0.6, last * 0.6, ease(k))
        else: tx = 0
        cam_path(cam, S.get("move", "push"), k, (tx, 0, CZ + S.get("tz", -0.07 if lay != "row" else -0.04)), dist)
        focus.location = Vector((0, 0, CZ)) if latest is None else Vector(latest[1])
    return update

def T_prompt(S):
    """over the shoulder of a prompt bar; the output screen waits, the prompt types, sends, the output arrives"""
    out_w = glass_card("outwait", S["wait"], 0.9, (0, 0.0, CZ + 0.12), r=0.03, strength=2.4)
    out_d = glass_card("outdone", S["out"], 0.9, (0, 0.0, CZ + 0.12), r=0.03, strength=2.4, back=False)
    bpy.ops.mesh.primitive_cube_add(size=1); bar = bpy.context.active_object; bar.name = "progress"
    bar.data.materials.append(mat_emit("progress", hex2rgb("#9fc6ff"), 4.0))
    dock = glass_card("dock", S["dock"], 0.86, (0.1, -0.55, CZ - 0.54), r=0.05, strength=2.4, back=False, small=False, seq=seq_face(S["dock"]))
    dock.rotation_euler = (math.radians(-10), 0, 0)
    send = at(S["send"]); type_at = at(S["type"])
    cam, focus = camera(35, 2.0)
    def update(f):
        sent = f >= send + 8
        out_w.scale = (0.0001,) * 3 if sent else (1, 1, 1)
        out_d.scale = (1, 1, 1) if sent else (0.0001,) * 3
        if sent: power_on(out_d, f, send + 8, 2.4)
        g = seg(f, send, send + 8); w = max(0.001, 0.66 * g)
        bar.scale = (w, 0.004, 0.012) if (f >= send and not sent) else (0.0001,) * 3
        bar.location = (-0.33 + w / 2, -0.012, CZ + 0.12)
        k = ease(seg(f, F0, F1 + 1))
        aim(cam, (lerp(-0.24, -0.17, k), lerp(-1.74, -1.6, k), CZ - 0.5), (0.0, 0, CZ + 0.06))
        to_bar = decel(seg(f, type_at - 6, type_at + 4)) * (1 - decel(seg(f, send - 2, send + 8)))
        focus.location = Vector((0, 0, CZ + 0.12)).lerp(Vector(dock.location), to_bar)
    return update

def T_strike(S):
    """a pane that gets crossed out by two red glowing strokes, tips back; tags lift above it"""
    pane = glass_card("pane", S["face"], 0.9, (0, 0, CZ + 0.05), r=0.03, strength=2.4)
    H = pane["h"]
    strokes = []
    for i, (a, b) in enumerate([((-0.36, H * 0.36), (0.36, -H * 0.36)), ((0.36, H * 0.36), (-0.36, -H * 0.36))]):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.006, depth=1, vertices=16); s = bpy.context.active_object; s.name = f"stroke{i}"
        s.data.materials.append(mat_emit(f"strokem{i}", hex2rgb("#ff6b6b"), 5.0)); strokes.append((s, a, b))
    red = bpy.data.lights.new("redrim", "AREA"); red.shape = "RECTANGLE"; red.size = 1.0; red.size_y = 0.7; red.color = hex2rgb("#ff6b6b")[:3]; red.energy = 0
    ro = bpy.data.objects.new("redrim", red); sc.collection.objects.link(ro); ro.location = (0.15, 0.6, CZ + 0.15)
    ro.rotation_euler = (Vector((0, 0, CZ)) - Vector(ro.location)).to_track_quat("-Z", "Y").to_euler()
    tags = []
    for i, n in enumerate(S.get("tags", [])):
        tags.append(glass_card(f"tag{i}", n["face"], 0.2, (0, 0, 0), strength=2.0))
    strike = at(S["strike"]) if "strike" in S else None
    cam, focus = camera(50, 2.0)
    xs = [-0.23, 0.0, 0.23]; zs = [0.45, 0.5, 0.44]
    def update(f):
        tip = spring(f, strike, 120, 14) if strike is not None else 0
        pane.rotation_euler = (math.radians(12) * tip, 0, 0); pane.location = (0, 0.05 * tip, CZ + 0.05)
        for i, (s, a, b) in enumerate(strokes):
            p = 0 if strike is None else decel(seg(f, strike + i * 3, strike + i * 3 + 6))
            A = Vector((a[0], -0.03, a[1])); B = Vector((b[0], -0.03, b[1])); E = A.lerp(B, max(p, 0.001))
            mid = (A + E) / 2; L = (E - A).length
            # strokes ride with the pane's tip
            R = pane.matrix_world.to_3x3()
            s.location = Vector(pane.location) + R @ (mid - Vector((0, 0, 0)))
            s.scale = (1, 1, max(L, 0.0001)) if p > 0 else (0.0001,) * 3
            s.rotation_euler = (R @ (B - A)).to_track_quat("Z", "Y").to_euler()
        red.energy = 0 if strike is None else 90 * seg(f, strike, strike + 6)
        latest = None
        for i, tg in enumerate(tags):
            t = at(S["tags"][i]["at"])
            if f < t - 2: tg.scale = (0.0001,) * 3; continue
            s_ = spring(f, t - 2, 150, 16); latest = tg
            tg.scale = (1, 1, 1)
            tg.location = (xs[i], lerp(-0.01, -0.15, s_), CZ + lerp(0.27, zs[i], s_))
            tg.rotation_euler = (math.radians(12) * s_, 0, math.radians([8, 2, -7][i]) * s_)
        k = ease(seg(f, F0, F1 + 1))
        pos = orbit(lerp(12, 20, k), -4, 2.55 * (1 - 0.05 * k), (0.03, 0, CZ + 0.04)); aim(cam, pos, (0.03, 0, CZ + 0.04))
        focus.location = Vector((0, 0, CZ + 0.05)) if latest is None else Vector(latest.location)
    return update

def T_cta(S):
    """the close: the Claude spark rises, a glass pill with the comment word settles under it"""
    pl = glass_card("pill", S["face"], 0.62, (0, 0, CZ - 0.06), strength=2.2, small=False)
    up_s, sp = spark_rise(None, F0 + 2, (0, -0.02, CZ + 0.17), 120)
    cam, focus = camera(70, 1.8)
    t_p = at(S["pill_at"]) if "pill_at" in S else F0 + 8
    def update(f):
        up_s(f)
        s = spring(f, t_p - 2, 140, 15)
        pl.scale = (lerp(0.9, 1, s),) * 3 if f >= t_p - 2 else (0.0001,) * 3
        pl.location = (0, lerp(0.25, 0, s), CZ - 0.06 - 0.04 * (1 - s))
        k = ease(seg(f, F0, F1 + 1))
        pos = orbit(lerp(-10, -4, k), lerp(-3, -1, k), lens_dist(0.9, 70) * lerp(1, 0.9, k), (0, 0, CZ + 0.04)); aim(cam, pos, (0, 0, CZ + 0.04))
        focus.location = Vector((0, -0.01, CZ - 0.06)) if f >= t_p else sp.location
    return update


TEMPLATES = {"screen": T_screen, "stack": T_stack, "strike": T_strike, "prompt": T_prompt, "cta": T_cta}
UPDATE = TEMPLATES[S["t"]](S)
def handler(scene, depsgraph=None):
    UPDATE(scene.frame_current + scene.frame_subframe)
bpy.app.handlers.frame_change_pre.append(handler)

out_dir = os.path.join(PROJECT, "stills" if STILL else (arg("--out") or "frames")); os.makedirs(out_dir, exist_ok=True)
sc.render.use_overwrite = False   # frames already rendered are skipped, so a render can stop and resume
if STILL is not None:
    f = int(STILL) if STILL not in ("mid", "end", "start") else {"start": F0 + 3, "mid": (F0 + F1) // 2, "end": F1 - 2}[STILL]
    sc.frame_set(f); handler(sc)
    sc.render.filepath = os.path.join(out_dir, f"shot{SHOT_I:02d}_{f:04d}.png")
    bpy.ops.render.render(write_still=True)
else:
    a, b = (int(RANGE[0]), int(RANGE[1])) if RANGE else (F0, F1)
    sc.frame_start, sc.frame_end = a, b
    sc.render.filepath = os.path.join(out_dir, "f_")
    bpy.ops.render.render(animation=True)
