# DBI P-P 1.2 robot arm (DBI's original files in pp12/, shared with DBI's permission), scaled to MG90S size for the tank.
# Everything is the original mesh scaled by S, plus these edits:
#   - S = 32/58 turns the 6809 bearings (45x58x7) into stock 6705ZZ (25x32x4) and the M6 screws into M3.
#   - the planetary's module-0.5 teeth would print at module 0.28, so the Aussenrad now slides straight
#     onto the 3 pins (holes instead of planets), and its outer band + the servo gear become a printable
#     19:30 pair (module 0.84, same centre distance). The original planets only keyed the Aussenrad anyway.
#   - ST3215 / SC15 pockets are filled and recut for an MG90S with its shaft on the original gear axis.
#   - the base servo direct-drives the base gear (Sockel Zahnrad) for +-90 deg yaw.
# Mesh booleans need: pip install trimesh manifold3d rtree shapely
import math
import os
import sys
import tempfile
import numpy as np
import trimesh
import cadquery as cq
from tank import gear_profile, horn_key, BODY_C, TAB_HOLES, TUB, LID_T, ARM_BOLTS, ARM_S

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pp12")
S = ARM_S
TOP =TUB[2] + LID_T            # lid top, where the base servo's tabs sit

# ---------------------------------------------------------------- measured on the originals (mm, unscaled)
MITTE_A, MITTE_B = (10.0, 33.0), (10.1, 177.0)       # pin end / sun end joint axes (all joints along z)
UNTEN_A, OBEN_B = (14.33, 77.67), (27.0, 148.0)
D_FLIP, D_OBEN = 66.0, 65.6                          # next link: z_N = D - z' (flipped) or z' + D (Oben)
RING_Z = 65.0                                        # Aussenrad: z_N = RING_Z - z_ring (flipped into the cup)
PIN_R, PIN_PCD = 4.8, 13.2
# servo gear axes found from the pockets and the 37.4mm gear centre distance; u points from the body to the shaft
MITTE_SERVO = ((13.95, 139.79), (-0.120, 0.993))
OBEN_SERVO = ((18.76, 111.53), (0.225, 0.974))
GRIP_SERVO_X = 17.91                                 # gripper servo shaft (x, z=0), along -y; Stirnrad on x=0
BASE_E = 14.0                                        # base gear: y_unterteil = z_zahnrad + BASE_E

# ---------------------------------------------------------------- new gears (scaled)
ZG, ZR = 19, 30
GM = 2 * 37.4 * S / (ZG + ZR)                        # 0.842
GEAR_T = 4.2
BAND = (8.4, 13.75)                                  # ring-frame z of the new outer teeth (under the bearing)
JOINT_RATIO = ZR / ZG

# MG90S, servo frame as in tank.py: shaft at origin, tab underside w=0, body along -a
MG = dict(body=(-17.1, 6.1), half_w=6.3, bottom=-16.3, top=7.1, far_tab=-21.95, boss=11.3, gear_face=11.8)


def load(name):
    m = trimesh.load(f"{SRC}/{name}.stl")
    m.apply_scale(S)
    return m


def cq_mesh(wp):
    f = tempfile.NamedTemporaryFile(suffix=".stl", delete=False)
    f.close()
    cq.exporters.export(wp, f.name, tolerance=0.01, angularTolerance=0.1)
    m = trimesh.load(f.name)
    os.unlink(f.name)
    return m


U = lambda a, b: a.union(b, engine="manifold")
D = lambda a, b: a.difference(b, engine="manifold")
I = lambda a, b: a.intersection(b, engine="manifold")


def tr(x=0, y=0, z=0):
    m = np.eye(4); m[:3, 3] = [x, y, z]; return m


def rot(axis, deg):
    return trimesh.transformations.rotation_matrix(math.radians(deg), axis)


def box(x0, x1, y0, y1, z0, z1, M=np.eye(4)):
    b = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0], transform=tr((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    return b.apply_transform(M)


def cyl(r, z0, z1, x=0, y=0, M=np.eye(4), sections=64):
    c = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=sections, transform=tr(x, y, (z0 + z1) / 2))
    return c.apply_transform(M)


def frame(P, a, w):
    # local (a, c, w) -> part frame; body runs along -a, shaft along +w
    a = np.asarray(a, float); a /= np.linalg.norm(a)
    w = np.asarray(w, float); w /= np.linalg.norm(w)
    c = np.cross(w, a)
    M = np.eye(4); M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = a, c, w, P
    return M


def servo_cut(M, gear_r, insert=True, cable=10):
    # MG90S envelope with the shaft-end tab trimmed off; the far tab stays for one M2 screw.
    # insert=True extends the body and tab downward so it drops in from the open (cover) side.
    lo = MG["bottom"] - (6 if insert else 0)
    c = box(*MG["body"], -MG["half_w"], MG["half_w"], lo, MG["top"], M)
    c = U(c, box(MG["far_tab"], MG["body"][0] + 0.3, -MG["half_w"], MG["half_w"], lo if insert else -0.2, 2.7, M))
    c = U(c, cyl(6.2, MG["top"] - 0.5, MG["boss"], M=M))
    c = U(c, cyl(3.2, MG["top"] - 0.5, MG["boss"], x=-6, M=M))
    c = U(c, cyl(gear_r + 0.7, MG["boss"] - 0.3, MG["gear_face"] + GEAR_T + 0.6, M=M))
    c = U(c, cyl(0.8, 2.5, 9, x=BODY_C - TAB_HOLES, M=M, sections=16))
    if cable:
        c = U(c, box(MG["body"][0] - cable, MG["body"][0] + 0.5, -2.6, 2.6, -14, -9, M))
    return c


def servo_dummy(M):
    s = box(-16.9, 5.9, -6.1, 6.1, -15.9, 6.8, M)
    s = U(s, box(BODY_C - 16.15, -16.9, -6.1, 6.1, 0, 2.5, M))
    return U(s, cyl(5.9, 6.8, 11, M=M))


def rect_fill(centre, length, width, tilt, z0, z1):
    M = rot([0, 0, 1], -tilt) @ np.eye(4)
    M[:3, 3] = [centre[0], centre[1], 0]
    return box(-width / 2, width / 2, -length / 2, length / 2, z0, z1, M)


# ---------------------------------------------------------------- parts
def gear(z, m, t, bl=0.1):
    rp = m * z / 2
    return cq_mesh(gear_profile(z, m, rp + m, rp - 1.25 * m, bl).extrude(t))


def joint_gear():
    g = gear(ZG, GM, GEAR_T)
    key = cq_mesh(horn_key(GEAR_T + 1).translate((0, 0, -0.5)))
    return D(D(g, key), cyl(1.6, -1, GEAR_T + 1, sections=24))


def ring():
    r = load("Planetengetriebe Aussenrad")
    L = 62 * S
    r = U(r, cyl(20.48 * S + 0.05, 0.01, L - 0.01))                  # fill the module-0.5 teeth
    r = D(r, D(cyl(20, -1, 15.2), cyl(12.45, -2, 16)))                # old 34T outer band off
    r = U(r, cyl(12.44, 0.0, BAND[0] + 0.01))
    band = gear(ZR, GM, BAND[1] - BAND[0], bl=0.1).apply_translation([0, 0, BAND[0]])
    r = U(r, band)
    for a in (30, 150, 270):
        x, y = PIN_PCD * S * math.cos(math.radians(a)), PIN_PCD * S * math.sin(math.radians(a))
        r = D(r, cyl(PIN_R * S + 0.2, -1, L + 1, x, y, sections=32))
    return D(r, cyl(4.3, -1, L + 1))


def grip_gear():
    g = load("Servo Zahnrad")
    c = g.bounds.mean(0)
    g.apply_translation([-c[0], -c[1], -g.bounds[0][2]])
    # keep only the toothed slab: drop the ST3215 horn pegs
    zs = np.linspace(0.05, g.bounds[1][2] - 0.05, 40)
    sec = lambda z: g.section([0, 0, z], [0, 0, 1])
    teeth = [z for z in zs if sec(z) is not None and np.linalg.norm(sec(z).vertices[:, :2], axis=1).max() > 6.5]
    z0, z1 = min(teeth), max(teeth)
    g = I(g, cyl(20, z0, z1)).apply_translation([0, 0, -z0])
    t = z1 - z0
    key = cq_mesh(horn_key(t + 1).translate((0, 0, -0.5)))
    return D(D(g, key), cyl(1.6, -1, t + 1, sections=24)), t


RACK_EXT = 4 * math.pi * 1.5 * S        # 4 more rack teeth (module 1.5 before scaling) so the jaws stay meshed wide open
FINGER_EXT = 8.0                         # mm added to each finger


def jaw():
    # DBI's Greifer Backen: rack along x (finger at +x), finger along z. Longer rack and longer finger.
    from shapely.geometry import Polygon
    j = load("Greifer Backen")
    (x0, y0, z0), (x1, y1, z1) = j.bounds
    seg = I(j, box(x0 - 0.01, x0 + RACK_EXT, y0 - 1, y1 + 1, z0 - 1, 1.4 * S))
    j = U(j, seg.apply_translation([-RACK_EXT, 0, 0]))
    zc = 14 * S                                                       # cut above the rack bar, stretch the finger
    low = I(j, box(x0 - 30, x1 + 1, y0 - 1, y1 + 1, z0 - 1, zc))
    high = I(j, box(x0 - 30, x1 + 1, y0 - 1, y1 + 1, zc, z1 + 1)).apply_translation([0, 0, FINGER_EXT])
    sec = j.section([0, 0, zc], [0, 0, 1])
    solid = None
    for e in sec.entities:
        p = Polygon(sec.vertices[e.points][:, :2]).buffer(0)
        solid = p if solid is None else solid.symmetric_difference(p)
    mid = None
    for p in getattr(solid, "geoms", [solid]):
        m = trimesh.creation.extrude_polygon(p.buffer(0.02), FINGER_EXT + 0.1).apply_translation([0, 0, zc - 0.05])
        mid = m if mid is None else U(mid, m)
    return U(U(low, high), mid)


def mitte():
    m, cov = load("Gelenk Mitte"), load("Gelenk Deckel")
    (sx, sy), u = MITTE_SERVO
    m = U(m, rect_fill((15.47 * S, 127.2 * S), 45.2 * S, 27.0 * S, -6.9, -10 * S, 14 * S))   # stops at the cover
    M = frame([sx * S, sy * S, 9.5 - MG["gear_face"]], [u[0], u[1], 0], [0, 0, 1])
    cut = servo_cut(M, GM * (ZG + 2) / 2)
    return D(m, cut), D(cov, cut), M


def oben():
    o, cov, gcov = load("Gelenk Oben"), load("Gelenk Deckel Oben"), load("Greifer Deckel")
    (sx, sy), u = OBEN_SERVO
    o = U(o, rect_fill((15.84 * S, 98.9 * S), 45.1 * S, 27.0 * S, 13.0, -14 * S, 7.5 * S))   # stops at the cover
    Mj = frame([sx * S, sy * S, -14.0 + GEAR_T + MG["gear_face"]], [u[0], u[1], 0], [0, 0, -1])
    cut = servo_cut(Mj, GM * (ZG + 2) / 2)
    o, cov = D(o, cut), D(cov, cut)
    # gripper: SC15 pocket filled, MG90S on the same gear axis, shaft toward the tip (-y)
    fill = box(-12 * S, 28 * S, 25 * S, 65 * S, -11 * S, 11 * S)
    o = U(o, I(fill, box(0, 30, 0, 60, -20, 20)))
    gcov = U(gcov, I(fill, box(-30, 0, 0, 60, -20, 20)))
    # Stirnrad's gear half spans y 15..26 (unscaled); the servo gear sits at its tip end so the MG90S
    # body clears the wrist servo behind it
    y_t = 20.5 * S + MG["gear_face"]
    Mg = frame([GRIP_SERVO_X * S, y_t, 0], [1, 0, 0], [0, -1, 0])
    gcut = servo_cut(Mg, 13.41 * S, insert=False, cable=0)
    gcut = U(gcut, box(-7.5, -1, y_t + 13, y_t + 23, -2.5, 2.5))       # cable toward the joint servo
    return D(o, gcut), D(cov, gcut), D(gcov, gcut), Mj, Mg


def zahnrad():
    z = load("Sockel Zahnrad")
    off = BASE_E * S + 3 * S                                          # tank z = TOP + z_zs + off
    zz = lambda t: t - TOP - off
    z = D(z, box(-30, 30, -30, 30, -20, zz(TOP + 7.4)))                # clear of the servo body top
    z = D(z, cyl(6.4, -20, zz(TOP + 11.6)))                           # gearbox bosses
    key = cq_mesh(horn_key(5.2)).apply_translation([0, 0, zz(TOP + 11.4)])
    return D(z, key)


def unterteil():
    u = load("Sockel Unterteil")
    # into the tank frame: tank = (x, -z_u, y_u + 3S + TOP)
    to_tank = tr(0, 0, TOP + 3 * S) @ rot([1, 0, 0], 90)
    inv = np.linalg.inv(to_tank)
    cut = box(BODY_C - 11.8, BODY_C + 11.8, -6.6, 6.6, TOP - 2, TOP + 7.4, inv)
    cut = U(cut, cyl(6.4, TOP - 2, TOP + 11.6, M=inv))
    for x, y in UNTERTEIL_BOLTS:
        cut = U(cut, cyl(1.7, TOP - 2, TOP + 4, x, y, M=inv, sections=24))
    return D(u, cut), to_tank


UNTERTEIL_BOLTS = ARM_BOLTS         # the Unterteil's 4 floor holes, tank (x, y); its z axis maps to tank -y
GRIP_T = None

def build_parts():
    global GRIP_T
    gg, GRIP_T = grip_gear()
    parts = {}
    parts["mitte"], parts["mitte_cover"], M_mitte = mitte()
    parts["oben"], parts["oben_cover"], parts["grip_cover"], M_obj, M_grip = oben()
    parts["unten"] = load("Gelenk Unten")
    parts["ring"] = ring()
    parts["joint_gear"] = joint_gear()
    parts["grip_gear"] = gg
    parts["grip_pinion"] = load("Greifer Stirnrad")
    parts["jaw"] = jaw()
    parts["base_gear"] = zahnrad()
    parts["base_lower"], to_tank = unterteil()
    parts["base_upper"] = load("Sockel Oberteil")
    return parts, dict(mitte=M_mitte, oben=M_obj, grip=M_grip, unter=to_tank)


# ---------------------------------------------------------------- assembly
COLORS = {"print": (0.86, 0.33, 0.12), "print2": (0.16, 0.17, 0.18), "servo": (0.15, 0.3, 0.75)}
FLIP =np.diag([-1.0, 1, -1, 1])
FLIPX = np.diag([1.0, -1, -1, 1])


def joint(parentA, childB, theta, flip, D_):
    J = tr(0, 0, D_ * S) @ (FLIP if flip else np.eye(4))
    return tr(parentA[0] * S, parentA[1] * S) @ rot([0, 0, 1], theta) @ J @ tr(-childB[0] * S, -childB[1] * S)


def assemble(parts, F, yaw, t1, t2, t3, opened=0.0):
    out = []
    Mu = F["unter"]
    out.append(("base_lower", parts["base_lower"], Mu, "print2"))
    out.append(("base_upper", parts["base_upper"], Mu @ tr(0, 55 * S, 0) @ FLIPX, "print2"))
    Mz = Mu @ rot([0, 1, 0], yaw) @ tr(0, BASE_E * S, 0) @ rot([1, 0, 0], -90)
    out.append(("base_gear", parts["base_gear"], Mz, "print"))
    # Unten's two bottom screws line up with the base gear's prong holes
    un2z = np.array([[0, 0, -1, 0], [-1, 0, 0, 0], [0, 1, 0, 45 * S], [0, 0, 0, 1.0]])
    Mun = Mz @ un2z
    out.append(("unten", parts["unten"], Mun, "print"))
    M1 = Mun @ joint(UNTEN_A, MITTE_B, t1, True, D_FLIP)
    M2 = M1 @ joint(MITTE_A, MITTE_B, t2, True, D_FLIP)
    M3 = M2 @ joint(MITTE_A, OBEN_B, t3, False, D_OBEN)
    for i, (Mp, A, rz) in enumerate(((Mun, UNTEN_A, RING_Z + 0.5), (M1, MITTE_A, RING_Z), (M2, MITTE_A, RING_Z))):
        out.append((f"ring_{i + 1}", parts["ring"], Mp @ tr(A[0] * S, A[1] * S, rz * S) @ FLIPX, "print2"))
    for i, M in enumerate((M1, M2)):
        out.append((f"mitte_{i + 1}", parts["mitte"], M, "print"))
        out.append((f"mitte_cover_{i + 1}", parts["mitte_cover"], M, "print2"))
        out.append((f"servo_joint_{i + 1}", servo_dummy(F["mitte"]), M, "servo"))
        out.append((f"gear_joint_{i + 1}", parts["joint_gear"], M @ F["mitte"] @ tr(0, 0, MG["gear_face"]), "print2"))
    out.append(("oben", parts["oben"], M3, "print"))
    out.append(("oben_cover", parts["oben_cover"], M3, "print2"))
    out.append(("grip_cover", parts["grip_cover"], M3, "print2"))
    out.append(("servo_joint_3", servo_dummy(F["oben"]), M3, "servo"))
    out.append(("gear_joint_3", parts["joint_gear"], M3 @ F["oben"] @ tr(0, 0, MG["gear_face"]), "print2"))
    out.append(("servo_grip", servo_dummy(F["grip"]), M3, "servo"))
    out.append(("gear_grip", parts["grip_gear"], M3 @ F["grip"] @ tr(0, 0, MG["gear_face"]), "print2"))
    Mst = np.array([[1, 0, 0, 0], [0, 0, -1, 34.5 * S], [0, 1, 0, 0], [0, 0, 0, 1.0]])
    out.append(("grip_pinion", parts["grip_pinion"], M3 @ Mst, "print2"))
    # jaws ride in the T-slot across the head's end face, racks either side of the Stirnrad, fingers out
    Mjaw = np.array([[-1, 0, 0, (20 + opened) * S], [0, 0, -1, 4.0 * S], [0, -1, 0, 4.6 * S], [0, 0, 0, 1.0]])
    out.append(("jaw_1", parts["jaw"], M3 @ Mjaw, "print2"))
    out.append(("jaw_2", parts["jaw"], M3 @ rot([0, 1, 0], 180) @ Mjaw, "print2"))
    tip = M3 @ np.array([0, -36 * S - FINGER_EXT, 0, 1.0])
    return [(n, m.copy().apply_transform(M), c) for n, m, M, c in out], tip[:3]


def overlap(a, b):
    (a0, a1), (b0, b1) = a.bounds, b.bounds
    if (a1 < b0).any() or (b1 < a0).any():
        return 0.0
    return I(a, b).volume


def clashes(meshes, others=None, tol=0.5):
    names = list(meshes)
    pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]] if others is None else [(a, b) for a in names for b in others]
    allm = dict(meshes, **(others or {}))
    hits = []
    for a, b in pairs:
        v = overlap(allm[a], allm[b])
        if v > tol:
            hits.append((a, b, round(v, 1)))
    return hits


# joint angles: base yaw, then each joint relative to the arm standing straight up (180, 0, 0)
YAW0 = 90                                            # joint axes along the tank's y, arm reaches forward
HOME = (YAW0, 150, 70, -80)                          # servo 90 everywhere; fingertips ~11cm ahead of the turret
SPAN = 80 / JOINT_RATIO                              # +-50 deg per pitch joint from servo 10..170
FOLD_PAN = -90                                       # camera pan for folding the mast (yoke in the mast's plane)
FOLD_YAW = 0                                         # base turn for the fold (none needed)
# firmware joint limits from home, + = up/back (swept in CAD). Shoulder: 26 forward puts the claw on the hull,
# past 50 back the forearm meets the camera. Wrist: past 43 down the claw folds into the forearm.
LIMITS = {"shoulder": (-23, 50), "elbow": (-SPAN, SPAN), "wrist": (-43, SPAN)}
LINKS = ["unten", "mitte_1", "mitte_2", "oben", "mitte_cover_1", "mitte_cover_2", "oben_cover", "grip_cover", "jaw_1", "jaw_2"]


def tm(shape):
    f = tempfile.NamedTemporaryFile(suffix=".stl", delete=False); f.close()
    cq.exporters.export(cq.Workplane().add(shape), f.name, tolerance=0.05, angularTolerance=0.2)
    m = trimesh.load(f.name); os.unlink(f.name); return m


def sightline(arm, lens, target):
    vec = np.asarray(target) - lens; L = np.linalg.norm(vec)
    hit = []
    for n, m, c in arm:
        if n.startswith(("jaw", "grip_pinion")):
            continue
        loc, _, _ = m.ray.intersects_location([lens], [vec / L])
        if len(loc) and (np.linalg.norm(loc - lens, axis=1) < L - 8).any():
            hit.append(n)
    return hit


def export(meshes, d):
    os.makedirs(d, exist_ok=True)
    with open(f"{d}/index.txt", "w") as f:
        for n, m, c in meshes:
            m.export(f"{d}/{n}.stl")
            f.write(f"{n} {' '.join(map(str, B.C[c]))}\n")


if __name__ == "__main__":
    import build as B
    OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
    parts, F = build_parts()
    os.makedirs(f"{OUT}/stl", exist_ok=True)
    for n, m in parts.items():
        print(n, m.extents.round(1), "watertight", m.is_watertight, "vol", round(m.volume / 1000, 1), "cm3")
        m.export(f"{OUT}/stl/arm_{n}.stl")

    hull = [(n, tm(s), c) for n, s, c in B.hull()]
    env = {n: m for n, m, c in hull if n in ("tub", "lid", "fender_L", "fender_R", "tire_FL", "tire_FR", "wheel_FL", "wheel_FR")}
    camp, lens = B.camera()
    cam = [(n, tm(s), c) for n, s, c in camp]
    camd = {n: m for n, m, c in cam}
    lens = np.array(lens)

    arm, tip = assemble(parts, F, *HOME, opened=6)
    ad = {n: m for n, m, c in arm}
    print("home tip", tip.round(1), "arm top", round(max(m.bounds[1][2] for m in ad.values())), "lens z", round(lens[2]))
    expected = {("base_lower", "base_upper"), ("base_gear", "unten")}
    self_hits = [h for h in clashes({k: ad[k] for k in ad if not k.startswith(("jaw", "grip_pinion", "gear_", "ring_"))}) if (h[0], h[1]) not in expected]
    print("home self-clash (beyond the press fits):", self_hits or "none")
    print("home vs hull/camera:", clashes({k: ad[k] for k in LINKS}, dict(env, **camd)) or "none")
    print("sightline to fingertips:", sightline(arm, lens, tip) or "clear")
    print("sightline to floor 15cm ahead:", sightline(arm, lens, (150, -36, 0)) or "clear")

    # sweep: each pitch joint to both firmware limits, base yaw +-80.  + = up/back: shoulder angle up,
    # elbow and wrist angles down (see HOME signs)
    for j, (lo, hi) in zip(range(1, 4), LIMITS.values()):
        for d_ in (lo, hi):
            pose = list(HOME); pose[j] += d_ if j == 1 else (-d_ if j == 2 else d_)
            a2, _ = assemble(parts, F, *pose)
            m2 = {n: m for n, m, c in a2}
            h = clashes({k: m2[k] for k in LINKS}, dict(env, **camd))
            h += [x for x in clashes({k: m2[k] for k in ("unten", "mitte_1", "mitte_2", "oben", "grip_cover")}) if (x[0], x[1]) not in expected]
            print("sweep joint", j, round(pose[j]), h or "clear", flush=True)
    for yaw in (YAW0 - 80, YAW0 + 80):
        a2, _ = assemble(parts, F, yaw, *HOME[1:])
        m2 = {n: m for n, m, c in a2}
        print("sweep yaw", yaw - YAW0, clashes({k: m2[k] for k in LINKS}, dict(env, **camd)) or "clear", flush=True)

    # mast fold (B button): camera turned to look right, base turned FOLD_YAW, arm otherwise at home
    folded = None
    arm_f, _ = assemble(parts, F, YAW0 + FOLD_YAW, *HOME[1:])
    adf = {n: m for n, m, c in arm_f}
    for fold in (20, 45, 70, 90):
        cm = [(n, tm(s), c) for n, s, c in B.camera(fold, FOLD_PAN, 0)[0]]
        h = clashes({n: m for n, m, c in cm if n != "mast_base"}, dict(env, **adf))
        print("mast fold", fold, h or "clear", flush=True)
        folded = cm
    export(hull + cam + arm, f"{OUT}/_mesh")
    export(hull + folded + arm_f, f"{OUT}/_mesh_fold")
    allm = trimesh.util.concatenate([m for n, m, c in hull + folded + arm_f])
    print("folded envelope", allm.bounds.round(0).tolist())
