# Build video from robot_arm_tank.blend (lattice-boom arm, build.py's assembly): hero shot, exploded view, step-by-step
# assembly (parts glide in from the exploded view while the rest wait as ghosts), then the arm, gripper and camera move
# and the arm stows.
# blender -b robot_arm_tank.blend -P source/video.py -- <out_prefix> [scale%] [first-last | f1,f2,... stills]
import math
import sys
import bpy
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index("--") + 1:]
out = args[0]
pct = int(args[1]) if len(args) > 1 else 100
scene = bpy.context.scene
FPS = 30
sec = lambda s: int(round(s * FPS))
GHOST = 0.07

# (title, tip, parts, camera azimuth, elevation) in build order; names match build.py's assembly
PREP = [
    ("Parts check", "Measure the 20kg servo: body, tab height, spline. Fix STD_* in tank.py if yours differs"),
    ("Print the parts", "Turret octagon down. Pinion and jaws at 0.12 mm, pinion 100% infill. Tires in TPU"),
    ("Flash + pair", "arm_tank.ino on the ESP32-32U, camera.ino on the XIAO. Pair the gamepad with the lid off"),
]
STEPS = [
    ("Tub + motors", "Shaft in the wall slot, gearbox under the lip, then the clamp on foam tape onto the post",
     ["tub", "tt_motor_FL", "tt_motor_FR", "tt_motor_RL", "tt_motor_RR", "clamp_L", "clamp_R"], -50, 38),
    ("Electronics", "Set the XL4015 to 5.1 V before anything else is connected. Velcro, Wago nuts, no solder",
     ["battery_2x18650", "buck_xl4015", "zk5ad", "esp32_wroom32u", "pca9685"], -20, 55),
    ("Lid + base servo", "MG90S in the lid slot. Horn on at 90 with the turret facing forward. Antenna in the rear hole",
     ["lid", "servo_base", "horn_base"], -60, 40),
    ("Wheels + fenders", "Wheels and TPU tires onto the TT shafts, fenders over them with 3x M3 each",
     ["wheel_FL", "wheel_FR", "wheel_RL", "wheel_RR", "tire_FL", "tire_FR", "tire_RL", "tire_RR", "fender_L", "fender_R"], -75, 22),
    ("Turret + shoulder", "20kg servo in the cradle, 4x M3. Disc horn on at 90 with the upper arm 45 deg up",
     ["turret", "servo_shoulder_20kg", "disc_horn_shoulder"], -45, 30),
    ("Upper arm", "Disc horn bolts to the big cheek, 4x M3x8. The other cheek rides on an M3 in the cradle wall",
     ["upper_arm", "servo_elbow"], -70, 25),
    ("Forearm", "Elbow horn on at 90 with the forearm square to the upper arm. Wrist servo in its cradle",
     ["horn_elbow", "forearm", "servo_wrist"], -60, 25),
    ("Wrist", "Horn on at 90 with the wrist in line with the forearm, E-clip on the far cheek screw",
     ["horn_wrist", "wrist"], -40, 22),
    ("Gripper", "Cut the horn to a 2 mm stub. Power to 90, gear on, fingers in at 20 mm gap, 4x M3x16 to the flange",
     ["servo_gripper", "pinion", "jaw_a", "jaw_b", "gripper_housing"], -20, 18),
    ("Camera", "Tower on the rear-left fender, 2x M3. Yoke arm toward the hull centre at 90. XIAO in, lens forward",
     ["pan_base", "servo_pan", "pan_yoke", "servo_tilt", "cam_head", "xiao_s3_sense"], 120, 25),
]
SRGB = lambda h: tuple(((int(h[i:i + 2], 16) / 255 + 0.055) / 1.055) ** 2.4 for i in (0, 2, 4)) + (1,)
INK, RUST, PAPER, GREY = SRGB("1A1815"), SRGB("B23A29"), SRGB("EDE9E0"), SRGB("5E5850")

O = bpy.data.objects
meshes = [o for o in scene.objects if o.type == "MESH" and o.name != "floor"]
missing = {o.name for o in meshes} - {n for s in STEPS for n in s[2]}
assert not missing, f"parts not in any step: {missing}"

# the blend is in millimetres with identity transforms; work in metres like the camera/light numbers below
for o in meshes:
    o.scale = (0.001, 0.001, 0.001)
floor = O["floor"]
floor.location.z *= 0.001
floor.scale = (0.02, 0.02, 0.001)
scene.unit_settings.scale_length = 1
bpy.context.view_layer.update()


def bbox(obs):
    pts = [o.matrix_world @ Vector(c) for o in obs for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return (lo + hi) / 2, hi - lo


# ---------- look: smooth shading, materials that can fade, studio light, paper floor ----------
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.shade_auto_smooth(angle=math.radians(35))


def fading(m):
    """material whose opacity follows the object's colour alpha (keyframed per object)"""
    nt = m.node_tree
    out_n = nt.nodes["Material Output"]
    surf = out_n.inputs["Surface"].links[0].from_socket
    info, tr, mix = nt.nodes.new("ShaderNodeObjectInfo"), nt.nodes.new("ShaderNodeBsdfTransparent"), nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(info.outputs["Alpha"], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(surf, mix.inputs[2])
    nt.links.new(mix.outputs[0], out_n.inputs["Surface"])
    m.use_transparent_shadow = True


for m in {s.material for o in meshes for s in o.material_slots if s.material}:
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.42
    fading(m)

floor.active_material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = PAPER
floor.active_material.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.8
for o in [o for o in scene.objects if o.type == "LIGHT"]:
    bpy.data.objects.remove(o)
for name, loc, power, size in (("key", (0.55, -0.75, 0.95), 24, 0.9), ("fill", (-0.8, -0.3, 0.45), 8, 1.4),
                               ("rim", (-0.5, 0.8, 0.7), 18, 0.6)):
    li = bpy.data.lights.new(name, "AREA")
    li.energy, li.size = power, size
    ob = bpy.data.objects.new(name, li)
    ob.location = loc
    ob.rotation_euler = (Vector((0.03, 0, 0.08)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(ob)
w = scene.world.node_tree.nodes["Background"]
w.inputs["Color"].default_value = PAPER
w.inputs["Strength"].default_value = 0.22

# ---------- rig: joints, gripper gear, camera pan/tilt as empties, placed by build.py's kinematics ----------
def empty(name, loc, rot=(0, 0, 0), parent=None, children=()):
    e = bpy.data.objects.new(name, None)
    e.location, e.rotation_euler = loc, rot
    scene.collection.objects.link(e)
    if parent:
        e.parent = parent
        e.matrix_parent_inverse = parent.matrix_world.inverted()
    bpy.context.view_layer.update()
    for c in children:
        c = O[c] if isinstance(c, str) else c
        c.parent = e
        c.matrix_parent_inverse = e.matrix_world.inverted()
    return e


ctr = lambda n: bbox([O[n]])[0]
# build.py pose: YAW, SHOULDER, ELBOW, WRIST, OPEN = 15, 55, -70, -35, 12; PAN, TILT = 10, -20; links L1, L2 = 80, 62
YAW0, SH0, EL0, WR0, OPEN0, PAN0, TILT0 = 15, 55, -70, -35, 12, 10, -20
RP = 8  # pinion pitch radius, mm per radian of gear turn
rz = lambda d: Matrix.Rotation(math.radians(d), 4, "Z")
ry = lambda d: Matrix.Rotation(math.radians(d), 4, "Y")
mv = lambda x, y=0, z=0: Matrix.Translation(Vector((x, y, z)) / 1000)
upper = rz(YAW0) @ mv(-18, 13, 40 + 3 + 14.6 + 9 + 40) @ ry(-SH0)
fore = upper @ mv(80) @ ry(-EL0)
wristM = fore @ mv(62) @ ry(-WR0)
pitch = (0, 0, math.radians(YAW0))  # all pitch joints turn about the yawed y axis: euler (0, angle, yaw)
yaw = empty("yaw", (0, 0, 0), children=["turret", "servo_shoulder_20kg", "horn_base"])
S = empty("S", upper.translation, pitch, yaw, ["upper_arm", "disc_horn_shoulder", "servo_elbow"])
E = empty("E", fore.translation, pitch, S, ["forearm", "horn_elbow", "servo_wrist"])
W = empty("W", wristM.translation, pitch, E, ["wrist", "horn_wrist", "gripper_housing", "servo_gripper", "jaw_a", "jaw_b"])
# the pinion turns about the wrist's x axis; an empty whose local x is that axis, so euler x is the gear angle
pin = empty("pin", ctr("pinion"), (wristM.to_3x3() @ Vector((1, 0, 0))).to_track_quat("X", "Z").to_euler(), W, ["pinion"])
u = rz(YAW0).to_3x3() @ Vector((0, 1, 0))  # jaws slide along the yawed y; jaw_a sits at +u
jaw_home = {n: O[n].location.copy() for n in ("jaw_a", "jaw_b")}
CAM = Vector((-66, 73, 0)) / 1000
pan = empty("pan", CAM + Vector((0, 0, 0.1)), children=["pan_yoke", "servo_tilt"])
tilt = empty("tilt", CAM + Vector((0, 0, (40 + 3 + 9 + 48 + 14.6 + 3 + 24) / 1000)), (0, 0, math.radians(PAN0)), pan, ["cam_head", "xiao_s3_sense"])
rest = {e: tuple(e.rotation_euler) for e in (yaw, S, E, W, pin, pan, tilt)}

# ---------- camera; captions are collected here and laid over the render in the video sequencer (sharp, no DOF) ----------
cam = scene.camera
cam.constraints.clear()
cam.data.lens = 50
cam.data.clip_start = 0.01
cam.data.dof.use_dof = True
cam.data.dof.aperture_fstop = 9
font = bpy.data.fonts.load(r"C:\Windows\Fonts\bahnschrift.ttf")
CAPS = []  # (text, px at 1080p, x, y normalised from bottom-left, colour, first, last frame)


def caption(lines, f0, f1):
    for body, px, x, y, color in lines:
        CAPS.append((body, px, x, y, color, f0, f1))


def step_card(label, title, tip, f0, f1):
    caption([(label, 22, 0.045, 0.215, RUST), (title.upper(), 78, 0.045, 0.135, INK), (tip, 30, 0.045, 0.085, GREY)], f0, f1)

# ---------- timeline ----------
alpha = lambda o, a, fr: (o.color.__setitem__(3, a), o.keyframe_insert("color", frame=fr))
c0, size0 = bbox(meshes)
home = {o.name: o.location.copy() for o in meshes}
ghost = {}
for o in meshes:  # exploded position: pushed out from the model's centre and lifted
    d = bbox([o])[0] - c0
    ghost[o.name] = home[o.name] + Vector((d.x * 0.9, d.y * 0.9, 0.09 + max(d.z, 0) * 0.9))

shots = []  # (frame, target, az, el, dist)

f = 0
caption([("ROBOT ARM TANK", 120, 0.045, 0.16, INK), ("FULL BUILD  ·  5-DOF LATTICE ARM  ·  GAMEPAD + ESP32  ·  NO SOLDER", 26, 0.047, 0.11, RUST)],
        sec(0.8), sec(5.5))
shots += [(0, c0 + Vector((0, 0, 0.03)), -65, 20, 0.95), (sec(6), c0 + Vector((0, 0, 0.03)), -15, 24, 0.98)]
f = sec(6)
for o in meshes:  # explode
    o.keyframe_insert("location", frame=f)
    o.location = ghost[o.name]
    o.keyframe_insert("location", frame=f + sec(2.4))
    alpha(o, 1, 0)
f += sec(2.6)
shots += [(f, c0 + Vector((0, 0, 0.09)), 15, 24, 1.45)]
for i, (title, tip) in enumerate(PREP):
    step_card("BEFORE YOU START", title, tip, f, f + sec(4))
    f += sec(4)
shots += [(f, c0 + Vector((0, 0, 0.09)), 75, 26, 1.45)]
for o in meshes:
    alpha(o, 1, f)
    alpha(o, GHOST, f + sec(1.2))
f += sec(1.2)

b0 = f
for k, (title, tip, parts, az, el) in enumerate(STEPS):
    cen, sz = bbox([O[n] for n in parts])
    dist = max(0.55, sz.length * 2.4)
    shots += [(f + sec(1.6), cen, az, el, dist)]
    t = f + sec(1.4)
    for j, n in enumerate(parts):
        o = O[n]
        o.keyframe_insert("location", frame=t)
        alpha(o, GHOST, t)
        o.location = home[n]
        o.keyframe_insert("location", frame=t + sec(1.5))
        alpha(o, 1, t + sec(0.9))
        t += sec(0.45)
    end = t + sec(1.5) + sec(1.6)
    shots += [(end - sec(0.3), cen, az + 14, el, dist * 0.95)]
    step_card(f"STEP {k + 1:02d} / {len(STEPS)}", title, tip, f + sec(0.8), end)
    f = end
BAR = (b0, f)  # progress bar fills over the assembly steps

# ---------- in action ----------
shots += [(f + sec(2), c0, -60, 24, 0.72)]
step_card("IN ACTION", "Arm + gripper + camera", "Right stick: base + shoulder. L1/R1 elbow, D-pad wrist + pan, L2/R2 gripper", f + sec(0.5), f + sec(15))


def pose(fr, y=0, j=(0, 0, 0), g=0, p=0, tl=0):
    """angles relative to the blend's pose: y base yaw, j shoulder/elbow/wrist (CAD sign), g mm per jaw, p pan, tl tilt"""
    for ob, ax, a in ((yaw, 2, math.radians(y)), (S, 1, -math.radians(j[0])), (E, 1, -math.radians(j[1])), (W, 1, -math.radians(j[2])),
                      (pin, 0, -g / RP), (pan, 2, math.radians(p)), (tilt, 1, -math.radians(tl))):
        r = list(rest[ob])
        r[ax] += a
        ob.rotation_euler = r
        ob.keyframe_insert("rotation_euler", frame=fr)
    for n, s in (("jaw_a", 1), ("jaw_b", -1)):
        O[n].location = jaw_home[n] + u * (s * g / 1000)
        O[n].keyframe_insert("location", frame=fr)


a = f + sec(1)
pose(0)
pose(a)
REACH = dict(j=(-25, 40, -20))
fk = lambda sh, el, wr: rz(YAW0) @ mv(-18, 13, 40 + 3 + 14.6 + 9 + 40) @ ry(-sh) @ mv(80) @ ry(-el) @ mv(62) @ ry(-wr)
grip = (fk(SH0 - 25, EL0 + 40, WR0 - 20) @ mv(80, -3, 0)).translation  # gripper centre in the reach pose
for t, kw in ((2.5, dict(y=40)), (5, dict(y=-35)), (6.5, {}), (9, dict(**REACH, p=-60, tl=15)),
              (10.5, dict(**REACH, g=8, p=-60, tl=15)), (12, dict(**REACH, g=-12, p=40, tl=-10)), (14, {})):
    pose(a + sec(t), **kw)
shots += [(a + sec(6.5), c0, -30, 22, 0.66), (a + sec(10), grip, -30, 14, 0.5),
          (a + sec(14), c0, -45, 26, 0.7)]
f = a + sec(15)
step_card("STOW", "Fold for carrying", "Circle / B: the arm folds back over the hull, gripper shut. Triangle / Y brings it home", f, f + sec(9))
shots += [(f + sec(2), c0, -110, 26, 0.75)]
STOW = dict(y=-YAW0, j=(120 - SH0, -120 - EL0, -30 - WR0), g=-OPEN0)
for t, kw in ((1, {}), (4.5, STOW), (7, STOW)):
    pose(f + sec(t), **kw)
shots += [(f + sec(8), c0, -160, 32, 0.72)]
f += sec(9)
caption([("DRIVE IT.", 120, 0.045, 0.16, RUST), ("Every step in detail: README.md", 30, 0.047, 0.11, INK)], f, f + sec(5))
shots += [(f + sec(5), c0, -200, 26, 0.8)]
END = f + sec(5)
print("KEY steps", b0, "action", a, "stow", f - sec(9), "end", END)

# ---------- camera path: Catmull-Rom through the shot keys, baked every frame ----------
def vec(s):
    return [*s[1], s[2], s[3], s[4]]


ks = [(s[0], vec(s)) for s in shots]
tgt = bpy.data.objects.new("focus", None)
scene.collection.objects.link(tgt)
cam.data.dof.focus_object = tgt
for fr in range(0, END + 1):
    i = max(k for k in range(len(ks)) if ks[k][0] <= fr) if fr >= ks[0][0] else 0
    i = min(i, len(ks) - 2)
    (t0, p0), (t1, p1) = ks[i], ks[i + 1]
    pm = ks[i - 1][1] if i > 0 else p0
    pp = ks[i + 2][1] if i + 2 < len(ks) else p1
    tm = ks[i - 1][0] if i > 0 else t0
    tp = ks[i + 2][0] if i + 2 < len(ks) else t1
    s = min(max((fr - t0) / (t1 - t0), 0), 1)
    h = (2 * s**3 - 3 * s**2 + 1, s**3 - 2 * s**2 + s, -2 * s**3 + 3 * s**2, s**3 - s**2)
    v = []
    for c in range(6):
        m0 = (p1[c] - pm[c]) / max(t1 - tm, 1) * (t1 - t0) if i > 0 else 0
        m1 = (pp[c] - p0[c]) / max(tp - t0, 1) * (t1 - t0) if i + 2 < len(ks) else 0
        v.append(h[0] * p0[c] + h[1] * m0 + h[2] * p1[c] + h[3] * m1)
    T, az, el, dist = Vector(v[:3]), math.radians(v[3]), math.radians(v[4]), v[5]
    pos = T + dist * Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    fwd = (T - pos).normalized()
    right = fwd.cross(Vector((0, 0, 1))).normalized()
    cam.location = pos
    cam.rotation_euler = (T - right * dist * 0.16 - pos).to_track_quat("-Z", "Y").to_euler()  # subject sits right of the captions
    tgt.location = T
    cam.keyframe_insert("location", frame=fr)
    cam.keyframe_insert("rotation_euler", frame=fr)
    tgt.keyframe_insert("location", frame=fr)

# ---------- render: 3D scene, with captions + progress bar laid over it in an "edit" scene's sequencer ----------
scene.render.fps = FPS
scene.render.engine = "BLENDER_EEVEE"
ee = scene.eevee
ee.taa_render_samples = 32
ee.use_raytracing = True
ee.use_shadows = True
scene.render.use_motion_blur = True
scene.frame_start, scene.frame_end = 1, END
edit = bpy.data.scenes.new("edit")
for sc in (scene, edit):
    sc.view_settings.view_transform = "Standard"
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.render.resolution_percentage = pct
    sc.render.fps = FPS
edit.frame_start, edit.frame_end = 1, END
sed = edit.sequence_editor_create()
strips = sed.strips if hasattr(sed, "strips") else sed.sequences
strips.new_scene("render", scene, 1, 1).scene_input = "CAMERA"


def keyed(st, prop, pts):
    for fr, v in pts:
        setattr(st, prop, v)
        st.keyframe_insert(prop, frame=fr)


for n, (body, px, x, y, color, f0, f1) in enumerate(CAPS):
    st = strips.new_effect(f"cap{n}", "TEXT", 2 + n % 6, max(f0, 1), length=f1 - max(f0, 1))
    st.text, st.font_size, st.font, st.color, st.use_shadow = body, px, font, color, False
    st.anchor_x, st.anchor_y, st.blend_type = "LEFT", "BOTTOM", "ALPHA_OVER"
    d = sec(0.6)
    keyed(st, "blend_alpha", ((f0, 0), (f0 + d, 1), (f1 - d, 1), (f1, 0)))
    for fr, dx in ((f0, -0.006), (f0 + sec(0.9), 0)):  # slides in a few px while it fades up
        st.location = (x + dx, y)
        st.keyframe_insert("location", frame=fr)
b0, b1 = BAR
bar = strips.new_effect("bar", "COLOR", 9, b0, length=b1 + sec(1) - b0)
bar.color, bar.blend_type = RUST[:3], "ALPHA_OVER"
bar.transform.scale_y = 6 / 1080
bar.transform.offset_y = -540 * pct / 100 + 3 * pct / 100
W_ = 960 * pct / 100
keyed(bar, "blend_alpha", ((b0, 0), (b0 + sec(0.6), 1), (b1 + sec(0.4), 1), (b1 + sec(1), 0)))
for fr, sx in ((b0, 0.001), (b1, 1)):  # left edge pinned: offset tracks the scale
    bar.transform.scale_x, bar.transform.offset_x = sx, -W_ * (1 - sx)
    bar.transform.keyframe_insert("scale_x", frame=fr)
    bar.transform.keyframe_insert("offset_x", frame=fr)

print("frames", END, "seconds", round(END / FPS, 1))
im = edit.render.image_settings
if len(args) > 2 and ("," in args[2] or args[2].isdigit()):
    im.file_format = "PNG"
    for fr in map(int, args[2].split(",")):
        edit.frame_start = edit.frame_end = fr  # a 1-frame animation render evaluates the strip fades
        edit.render.filepath = f"{out}{fr}_"
        bpy.ops.render.render(animation=True, scene=edit.name)
else:
    if len(args) > 2:
        edit.frame_start, edit.frame_end = map(int, args[2].split("-"))
    edit.render.filepath = out
    im.media_type = "VIDEO"
    im.file_format = "FFMPEG"
    edit.render.ffmpeg.format = "MPEG4"
    edit.render.ffmpeg.codec = "H264"
    edit.render.ffmpeg.constant_rate_factor = "HIGH"
    edit.render.ffmpeg.gopsize = FPS
    bpy.ops.render.render(animation=True, scene=edit.name)
