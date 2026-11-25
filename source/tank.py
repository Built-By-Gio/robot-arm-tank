import math
import cadquery as cq

# SG90 / MG90S, servo frame: shaft axis = +Y, origin on the shaft axis at the underside of the mounting tabs,
# body runs along -X from the shaft. Check SHAFT_TOP against your servos, the horn pockets key off it.
SHAFT_TOP = 15.1
BODY_C = -5.5
BODY_L, BODY_W = 22.8, 12.2
TAB_HOLES = 13.9
CHEEK_IN = SHAFT_TOP - 0.5
HORN_DEPTH = 2.2

# Standard-size shoulder servo (DS3218 / MG996R class), same frame convention. Measure yours and fix these:
STD_L, STD_W = 40.5, 20.2
STD_BELOW = 26.5          # body bottom to tab underside
STD_TOP = 14.0            # tab underside to spline top
STD_C = -(STD_L / 2 - 10.2)
STD_HOLES = [(STD_C + sx * 24.75, sz * 5) for sx in (-1, 1) for sz in (-1, 1)]
DISC_D, DISC_BOLT_R = 25, 8.5   # 25T aluminium disc horn, 4x M3 on this radius

TUB = (154, 128, 40)
WALL = 3
LID_T = 3
XT = 0
WHEEL_X = 60
BOSS_X = TUB[0] / 2 - 6
SHAFT_Z = 14.25
MOTOR_Y = (42.2, 61)

L1, L2, LW = 80, 62, 50


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def mbox(sx, sy, x0, x1, y0, y1, z0, z1):
    xs, ys = sorted((sx * x0, sx * x1)), sorted((sy * y0, sy * y1))
    return box(xs[0], xs[1], ys[0], ys[1], z0, z1)


def cyl_y(r, y0, y1, x=0, z=0):
    return cq.Workplane("XZ").circle(r).extrude(-(y1 - y0)).translate((x, y0, z))


def cyl_x(r, x0, x1, y=0, z=0):
    return cq.Workplane("YZ").circle(r).extrude(x1 - x0).translate((x0, y, z))


def cyl_z(r, z0, z1, x=0, y=0):
    return cq.Workplane("XY").circle(r).extrude(z1 - z0).translate((x, y, z0))


def horn_pocket(depth):
    # single-arm SG90 horn lying in the XY plane, arm along +X, pocket from z=0 to z=depth
    p = (cq.Workplane("XY").circle(3.2).extrude(depth)
         .union(cq.Workplane("XY").center(16.5, 0).circle(2.2).extrude(depth))
         .union(cq.Workplane("XY").polyline([(0, 3.2), (16.5, 2.2), (16.5, -2.2), (0, -3.2)]).close().extrude(depth))
         .union(cq.Workplane("XY").circle(3.9).extrude(depth)))
    for r in (8, 11, 14):
        p = p.union(cyl_z(0.75, 0, depth + 4, x=r))
    return p


def horn_pocket_y(y_face, into):
    # pocket on a face normal to Y; into=+1 cuts toward +Y
    p = horn_pocket(HORN_DEPTH).rotate((0, 0, 0), (1, 0, 0), -90)
    if into < 0:
        p = p.mirror("XZ")
    return p.translate((0, y_face, 0))


def cradle(xmin=-24, xmax=13):
    plate = box(xmin, xmax, -3, 0, -10, 10).cut(box(BODY_C - 11.6, BODY_C + 11.6, -4, 1, -6.3, 6.3))
    for x in (BODY_C - TAB_HOLES, BODY_C + TAB_HOLES):
        plate = plate.cut(cyl_y(0.9, -4, 1, x=x))
    back = (box(xmin, xmax, -20, -16.5, -10, 10)
            .cut(box(xmin - 1, -14, -21, -15, -4.5, 4.5))
            .cut(cyl_y(1.35, -21, -15)))
    bars = box(xmin, xmax, -20, 0, 6.4, 10).union(box(xmin, xmax, -20, 0, -10, -6.4))
    return plate.union(back).union(bars)


def truss(a, b, h, z, web=1.4):
    # tight Warren pitch for the lattice-boom look
    n = max(1, round((b - a) / 9))
    w = (b - a) / n
    tris = []
    for i in range(n):
        x0 = a + i * w
        tris.append([(x0, z - h), (x0 + w, z - h), (x0 + w / 2, z + h)])
        if i < n - 1:
            tris.append([(x0 + w / 2, z + h), (x0 + 1.5 * w, z + h), (x0 + w, z - h)])
    out = None
    for t in tris:
        c = cq.Workplane("XZ").polyline(t).close().offset2D(-web).extrude(-40).translate((0, -20, 0))
        out = c if out is None else out.union(c)
    return out


def cheek_blank(reach, t):
    pts = [(-10, -5), (-5, -10), (reach, -10), (reach, 10), (-5, 10), (-10, 5)]
    c = cq.Workplane("XZ").polyline(pts).close().extrude(-t)
    return c.cut(truss(13, reach - 3, 8, 0))


def link(L, end="cradle"):
    reach = L - 24
    cheek = cheek_blank(reach, 5)
    cp = cheek.translate((0, CHEEK_IN, 0)).cut(horn_pocket_y(CHEEK_IN, 1)).cut(cyl_y(3, 0, 30))
    cn = cheek.translate((0, -25, 0)).cut(cyl_y(1.65, -30, 0))
    bridge = box(L - 32, L - 24, -25, CHEEK_IN + 5, -10, 10).edges("|Y").edges("<X").chamfer(2)
    l = cp.union(cn).union(bridge)
    if end == "cradle":
        l = l.union(cradle().translate((L, 0, 0)))
    elif end == "flange":
        f = box(L - 26, L - 20, -25, CHEEK_IN + 5, -14, 14).edges("|X").chamfer(3)
        for x, y in BOLTS:
            f = f.cut(cyl_x(1.65, L - 40, L - 18, y=YMID - y, z=x))
        l = l.union(f)
    return l


def tub():
    X, Y, H = TUB
    ix = X / 2 - WALL
    outer = cq.Workplane("XY").box(X, Y, H, centered=(True, True, False)).edges("|Z").chamfer(6).faces("<Z").edges().chamfer(1.5)
    inner = cq.Workplane("XY").box(X - 2 * WALL, Y - 2 * WALL, H, centered=(True, True, False)).edges("|Z").chamfer(1.5).translate((0, 0, WALL))
    t = outer.cut(inner)
    for sx in (-1, 1):
        for sy in (-1, 1):
            t = t.union(cyl_z(4, 0, H, x=sx * BOSS_X, y=sy * 30)).cut(cyl_z(1.4, 10, H + 1, x=sx * BOSS_X, y=sy * 30))
            # open-top shaft slot, deeper than needed so the motor always sits on the floor
            slot = mbox(sx, sy, WHEEL_X - 5, WHEEL_X + 5, 58, 70, 11, H + 1).union(cyl_y(5, 0, 12, x=sx * WHEEL_X, z=11).translate((0, sy * 64 - 6, 0)))
            t = t.cut(slot)
            # gearbox end tucks under this lip
            t = t.union(mbox(sx, sy, WHEEL_X + 8, ix + 1, MOTOR_Y[0], 62, 26, 30))
            # rail keeps the motor out of the electronics bay
            t = t.union(mbox(sx, sy, 1, ix - 1, MOTOR_Y[0] - 2.5, MOTOR_Y[0], WALL, 9))
        # the two motor cans nearly touch at x=0, so the clamp post sits just inboard of them
        t = t.union(cyl_z(3.5, 0, 26, x=0, y=sx * 36)).cut(cyl_z(1.35, 10, 27, x=0, y=sx * 36))
    t = t.cut(box(ix - 1, X / 2 + 1, -9.5, 9.5, 25, 38))
    return t


def lid():
    X, Y, _ = TUB
    z0 = TUB[2]
    p = (cq.Workplane("XY").box(X, Y, LID_T, centered=(True, True, False)).edges("|Z").chamfer(6)
         .faces(">Z").edges().chamfer(1.5).translate((0, 0, z0)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            p = p.cut(cyl_z(1.65, z0 - 1, z0 + 5, x=sx * BOSS_X, y=sy * 30))
    p = p.cut(box(XT + BODY_C - 11.6, XT + BODY_C + 11.6, -6.3, 6.3, z0 - 1, z0 + 5))
    for x in (BODY_C - TAB_HOLES, BODY_C + TAB_HOLES):
        p = p.cut(cyl_z(0.9, z0 - 1, z0 + 5, x=XT + x))
    top = z0 + LID_T
    ring = cyl_z(33, top - 0.5, top + CHEEK_IN - 0.4, x=XT).cut(cyl_z(30, top - 1, top + 20, x=XT))
    p = p.union(ring).cut(box(XT + 12, XT + 24, -8, 8, z0 - 1, z0 + 5))
    for sy in (-1, 1):
        p = p.union(mbox(1, sy, -X / 2 + 3, X / 2 - 3, 56, 64, top - 0.5, top + 6))
        for x in (-45, 0, 45):
            p = p.cut(cyl_z(1.35, top, top + 7, x=x, y=sy * 60))
    # SMA bulkhead for the main board's antenna
    p = p.cut(cyl_z(3.25, z0 - 1, z0 + 5, x=-X / 2 + 15, y=-45))
    return p


TURRET_T = 9
STD_IN = STD_TOP - 1.5
STD_BACK = (-STD_BELOW - 4, -STD_BELOW - 0.5)
STD_CHEEK_N = (STD_BACK[0] - 5.5, STD_BACK[0] - 0.5)
STD_XMAX = 19.5


def std_cradle(xmin=-40, xmax=STD_XMAX):
    hz = STD_W / 2 + 4
    plate = box(xmin, xmax, -3, 0, -hz, hz).cut(box(STD_C - STD_L / 2 - 0.3, STD_C + STD_L / 2 + 0.3, -4, 1, -STD_W / 2 - 0.3, STD_W / 2 + 0.3))
    for x, z in STD_HOLES:
        plate = plate.cut(cyl_y(1.35, -4, 1, x=x, z=z))
    back = (box(xmin, xmax, *STD_BACK, -hz, hz)
            .cut(box(xmin - 1, STD_C - STD_L / 2 + 6, STD_BACK[0] - 1, STD_BACK[1] + 1, -5, 5))
            .cut(cyl_y(1.35, STD_BACK[0] - 1, STD_BACK[1] + 1)))
    bars = box(xmin, xmax, STD_BACK[0], 0, STD_W / 2 + 0.4, hz).union(box(xmin, xmax, STD_BACK[0], 0, -hz, -STD_W / 2 - 0.4))
    cap = box(xmax - 3, xmax, STD_BACK[0], 0, -hz, hz)
    for z in (-8, 8):
        cap = cap.cut(cyl_x(1.35, xmax - 8, xmax + 1, y=-8, z=z))
    return plate.union(back).union(bars).union(cap)


def turret():
    z0 = TUB[2] + LID_T + CHEEK_IN
    oct_ = lambda r: [(r * math.cos(math.radians(22.5 + 45 * i)), r * math.sin(math.radians(22.5 + 45 * i))) for i in range(8)]
    t = (cq.Workplane("XY").polyline(oct_(44)).close().workplane(offset=TURRET_T).polyline(oct_(38)).close().loft()
         .translate((XT, 0, z0)))
    t = t.cut(horn_pocket(HORN_DEPTH).translate((XT, 0, z0))).cut(cyl_z(3.5, z0 - 1, z0 + 20, x=XT))
    t = t.cut(box(XT + 8, XT + 20, -6, 6, z0 - 1, z0 + 20))
    c = std_cradle().rotate((0, 0, 0), (0, 1, 0), -90).translate(shoulder_origin())
    return t.union(c)


def shoulder_origin():
    return (XT - 18, 13, TUB[2] + LID_T + CHEEK_IN + TURRET_T + 40)


def upper_arm():
    reach = L1 - 24
    pts = [(-15, -8), (-8, -15), (24, -15), (40, -10), (reach, -10), (reach, 10), (40, 10), (24, 15), (-8, 15), (-15, 8)]
    blank = cq.Workplane("XZ").polyline(pts).close().extrude(-5).cut(truss(17, reach - 3, 7, 0))
    cp = blank.translate((0, STD_IN, 0)).cut(cyl_y(DISC_D / 2 + 0.3, STD_IN - 1, STD_IN + 2)).cut(cyl_y(3.5, 0, 40))
    for i in range(4):
        a = math.radians(45 + 90 * i)
        cp = cp.cut(cyl_y(1.7, 0, 40, x=DISC_BOLT_R * math.cos(a), z=DISC_BOLT_R * math.sin(a)))
    cn = blank.translate((0, STD_CHEEK_N[0], 0)).cut(cyl_y(1.65, -60, 0))
    bridge = box(L1 - 32, L1 - 24, STD_CHEEK_N[0], STD_IN + 5, -10, 10).edges("|Y").edges("<X").chamfer(2)
    return cp.union(cn).union(bridge).union(cradle().translate((L1, 0, 0)))


YMID = (CHEEK_IN + 5 - 25) / 2

# Gripper is drawn in frame H: gear axis +Z, fingers/racks at +-X sliding along Y.
# H maps onto the wrist with H z -> wrist +x, H x -> wrist +z, H y -> wrist -y; back of the housing bolts to the wrist flange.
# The gripper servo lies along Y (frame map servo x,y,z -> H y,z,x) so the housing is only as wide as the racks.
MOD, TEETH = 1.0, 16
RP = MOD * TEETH / 2
BACKLASH = 0.08
RZ = (14.3, 20.9)
ROOT = RP + 1.25 * MOD
RACK_T = 4
HX = ROOT + RACK_T + 2.25
HY = (-24, 13)
BOLTS = [(sx * 11, y) for sx in (-1, 1) for y in (-15, 4)]
GX = LW + 1


def h_to_wrist(w):
    return w.rotate((0, 0, 0), (1, 0, 1), 180).translate((GX, YMID, 0))


def pinion():
    rb = RP * math.cos(math.radians(20))
    ra, rf = RP + MOD, RP - 1.25 * MOD
    inv = lambda a: math.tan(a) - a
    half = math.pi / (2 * TEETH) - BACKLASH / RP + inv(math.radians(20))
    pts = []
    for k in range(TEETH):
        c = 2 * math.pi * k / TEETH
        flank = []
        for i in range(9):
            r = rb + (ra - rb) * i / 8
            flank.append((r, half - inv(math.acos(rb / r))))
        side = [(rf, half)] + flank
        for r, a in side:
            pts.append((r * math.cos(c - a), r * math.sin(c - a)))
        for r, a in reversed(side):
            pts.append((r * math.cos(c + a), r * math.sin(c + a)))
    g = cq.Workplane("XY").polyline(pts).close().extrude(6).translate((0, 0, CHEEK_IN))
    # horn cut down to the hub plus a short stub, the stub keys the gear
    key = cyl_z(3.9, 0, HORN_DEPTH).union(box(0, 5.6, -2.9, 2.9, 0, HORN_DEPTH)).translate((0, 0, CHEEK_IN))
    return g.cut(key).cut(cyl_z(1.6, 0, 40)).cut(cyl_z(2.9, CHEEK_IN + 4, 40))


def rack_teeth(sign, y0, y1):
    # sign=+1: rack on +X side with teeth pointing -X
    p = math.pi * MOD
    ha, hf = MOD, 1.25 * MOD
    tan20 = math.tan(math.radians(20))
    w = lambda u: p / 4 - BACKLASH / 2 - u * tan20
    out = None
    for k in range(math.floor(y0 / p), math.ceil(y1 / p) + 1):
        yc = p / 2 + k * p
        if yc < y0 or yc > y1:
            continue
        prof = [(RP + hf + 0.01, yc - w(-hf)), (RP - ha, yc - w(ha)), (RP - ha, yc + w(ha)), (RP + hf + 0.01, yc + w(-hf))]
        prof = [(sign * x, y) for x, y in prof]
        t = cq.Workplane("XY").polyline(prof).close().extrude(RZ[1] - RZ[0]).translate((0, 0, RZ[0]))
        out = t if out is None else out.union(t)
    return out


def gripper_housing():
    h = box(-HX, HX, *HY, -21, 0).edges("|Z").chamfer(2)
    h = h.cut(box(-HX + 2, HX - 2, HY[0] + 2, HY[1] - 2, -19, -3)).cut(box(-5, 5, HY[0] - 1, HY[0] + 3, -17, -8))
    body = box(-6.3, 6.3, BODY_C - 11.6, BODY_C + 11.6, -20, 1)
    h = h.cut(body)
    for y in (BODY_C - TAB_HOLES, BODY_C + TAB_HOLES):
        h = h.cut(cyl_z(0.9, -6, 1, y=y))
    for s in (-1, 1):
        h = h.union(mbox(s, 1, 7.5, HX, *HY, 0, RZ[0]))
        h = h.union(mbox(s, 1, ROOT + RACK_T + 0.4, HX, *HY, RZ[0], RZ[1] + 0.2))
        h = h.union(mbox(s, 1, ROOT + 2, HX, *HY, RZ[1] + 0.2, RZ[1] + 2.6))
    for x, y in BOLTS:
        h = h.union(cyl_z(3, -21, -3, x=x, y=y)).cut(cyl_z(1.35, -22, -9, x=x, y=y))
    return h


def finger(sign):
    # sign=+1: finger on the +X rack, sitting on the -Y side of centre
    y0, y1 = (-5, 0) if sign > 0 else (0, 5)
    root = box(*sorted((sign * (RP - MOD), sign * (ROOT + 1.7))), y0, y1, RZ[1] - 0.2, 25)
    plate = box(*sorted((sign * -8, sign * (ROOT + 1.7))), y0, y1, 25, 55)
    f = root.union(plate).edges("|Y").edges(">Z").chamfer(2)
    ys = (y1 - 0.8, y1 + 0.1) if sign > 0 else (y0 - 0.1, y0 + 0.8)
    for z in range(33, 53, 3):
        f = f.cut(box(-20, 20, ys[0], ys[1], z, z + 1.2))
    return f


def jaw_a():
    return box(ROOT, ROOT + RACK_T, -5, 26, *RZ).union(rack_teeth(1, -4, 24)).union(finger(1))


def jaw_b():
    return box(-ROOT - RACK_T, -ROOT, -26, 5, *RZ).union(rack_teeth(-1, -24, 4)).union(finger(-1))


def forearm():
    return link(L2)


def wrist():
    return link(LW, end="flange")


# Pan-tilt camera on the front-left fender. Local frame P: pan axis at the origin, z=0 on the fender top.
CAM_AT = (-66, 73)
PAN_TAB = 48
PAN_HORN = PAN_TAB + CHEEK_IN
TILT_Z = PAN_HORN + 3 + 24
TILT_Y = -22
# the camera antenna goes in the mirrored hole on the right fender
CAM_SMA = (-60, 73)


def pan_base():
    # pan servo shaft up, body toward -X, tabs on the top plate
    b = box(-22, 13, -10, 10, 0, PAN_TAB).edges("|Z").chamfer(2)
    b = b.cut(box(BODY_C - 11.9, BODY_C + 11.9, -6.6, 6.6, -1, PAN_TAB - 3))
    # tower walls get windows so it's not a solid block; servo wire drops down inside
    for x in (-15, 4):
        b = b.cut(box(x - 4, x + 4, -11, 11, 8, PAN_TAB - 22))
    b = b.cut(box(BODY_C - 11.6, BODY_C + 11.6, -6.3, 6.3, 0, PAN_TAB + 1))
    for x in (BODY_C - TAB_HOLES, BODY_C + TAB_HOLES):
        b = b.cut(cyl_z(0.9, PAN_TAB - 6, PAN_TAB + 1, x=x))
    b = b.cut(box(-23, -16, -4, 4, -1, 8))
    for y in (-8.3, 8.3):
        b = b.cut(cyl_z(1.35, -1, 8, x=-6, y=y))
    return b


def pan_yoke():
    # sits on the pan horn (arm pointing -Y), carries the tilt servo with its shaft along Y
    y = box(-11, 11, -42, 6, PAN_HORN, PAN_HORN + 3).edges("|Z").chamfer(3)
    horn = horn_pocket(HORN_DEPTH).rotate((0, 0, 0), (0, 0, 1), -90).translate((0, 0, PAN_HORN))
    y = y.cut(horn).cut(cyl_z(3, PAN_HORN - 1, PAN_HORN + 5))
    c = cradle(xmin=-24).rotate((0, 0, 0), (0, 1, 0), -90).translate((0, TILT_Y, TILT_Z))
    return y.union(c)


def cam_head():
    # frame: origin on the tilt axis, world-aligned at tilt 0; lens looks +X, XIAO drops in from the top
    plate = box(-8, 8, CHEEK_IN, CHEEK_IN + 5, -11.5, 11.5)
    plate = plate.cut(horn_pocket_y(CHEEK_IN, 1)).cut(cyl_y(3, 0, 40))
    pod = box(-8, 8, CHEEK_IN + 5, CHEEK_IN + 30.5, -11.5, 11.5).edges("|Y").chamfer(1.5)
    pod = pod.cut(box(-5.5, 6.5, CHEEK_IN + 6.5, CHEEK_IN + 28.5, -9.5, 12.5))
    pod = pod.cut(box(5, 10, CHEEK_IN + 11, CHEEK_IN + 24, -6, 6))
    pod = pod.cut(box(-4, 4, CHEEK_IN + 27.5, CHEEK_IN + 32, -6, 12.5))
    return plate.union(pod).translate((0, TILT_Y, 0))


def fender():
    z0 = TUB[2] + LID_T + 6
    hx = WHEEL_X + 36
    f = box(-hx, hx, 56, 90, z0, z0 + 3).edges("|Z").edges("<Y").chamfer(12)
    skirt = box(-hx, hx, 87, 90, z0 - 14, z0 + 3).edges("|Y").edges("<Z").chamfer(10)
    f = f.union(skirt)
    for x in (-72, -24, 24, 72):
        f = f.cut(box(x - 12, x + 12, 86, 91, z0 - 10, z0 - 6))
    for x in (-45, 0, 45):
        f = f.cut(cyl_z(1.65, z0 - 1, z0 + 5, x=x, y=60))
    for y in (-8.3, 8.3):
        f = f.cut(cyl_z(1.65, z0 - 1, z0 + 5, x=CAM_AT[0] - 6, y=CAM_AT[1] + y))
    return f.cut(cyl_z(3.25, z0 - 1, z0 + 5, x=CAM_SMA[0], y=CAM_SMA[1]))


def clamp():
    c = box(-12, 12, 32, MOTOR_Y[1] - 1, 26, 30).edges("|Z").chamfer(3)
    return c.cut(cyl_z(1.65, 20, 40, x=0, y=36))


def wheel():
    w = cyl_y(30, 0, 20).union(cyl_y(32.5, 0, 2)).union(cyl_y(32.5, 18, 20))
    w = w.cut(cyl_y(26, -1, 15)).union(cyl_y(7, 0, 20))
    for i in range(5):
        a = math.radians(72 * i)
        w = w.cut(cyl_y(5, 10, 21, x=17 * math.cos(a), z=17 * math.sin(a)))
    bore = cyl_y(2.75, -1, 9).intersect(box(-1.85, 1.85, -2, 10, -3, 3))
    return w.cut(bore).cut(cyl_y(1.2, 0, 21)).cut(cyl_y(2.6, 17, 21))


def tire():
    t = cyl_y(33.5, 2, 18).cut(cyl_y(29.6, 0, 20))
    for i in range(24):
        g = box(31.8, 36, 4, 16, -1.25, 1.25).rotate((0, 0, 0), (0, 1, 0), 15 * i)
        t = t.cut(g)
    return t
