import os
import math
import sys
import cadquery as cq
from tank import *

OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
os.makedirs(f"{OUT}/stl", exist_ok=True)

YAW, SHOULDER, ELBOW, WRIST, OPEN = 15, 55, -70, -35, 12
PAN, TILT = 10, -20
if os.environ.get("POSE") == "stow":
    YAW, SHOULDER, ELBOW, WRIST, OPEN = 0, 120, -120, -30, 0


def rot(axis, deg, about=(0, 0, 0)):
    return cq.Location(cq.Vector(*about)) * cq.Location(cq.Vector(0, 0, 0), cq.Vector(*axis), deg) * cq.Location(cq.Vector(*[-a for a in about]))


def mv(x=0, y=0, z=0):
    return cq.Location(cq.Vector(x, y, z))


def horn_solid():
    s = (cq.Workplane("XY").circle(3.2).extrude(1.6)
         .union(cq.Workplane("XY").center(16.5, 0).circle(2.0).extrude(1.6))
         .union(cq.Workplane("XY").polyline([(0, 3.0), (16.5, 2.0), (16.5, -2.0), (0, -3.0)]).close().extrude(1.6))
         .union(cq.Workplane("XY").circle(3.5).extrude(-3)))
    return s


def servo():
    s = box(BODY_C - BODY_L / 2, BODY_C + BODY_L / 2, -15.9, 6.8, -BODY_W / 2, BODY_W / 2)
    s = s.union(box(BODY_C - 16.15, BODY_C + 16.15, 0, 2.5, -BODY_W / 2, BODY_W / 2))
    s = s.union(cyl_y(5.9, 6.8, 11)).union(cyl_y(2.9, 6.8, 11, x=-6)).union(cyl_y(2.4, 11, SHAFT_TOP))
    return s


def std_servo():
    s = box(STD_C - STD_L / 2, STD_C + STD_L / 2, -STD_BELOW, STD_TOP - 4, -STD_W / 2, STD_W / 2)
    s = s.union(box(STD_C - 27.25, STD_C + 27.25, 0, 2.5, -STD_W / 2, STD_W / 2))
    return s.union(cyl_y(3, STD_TOP - 4, STD_TOP))


def disc_horn():
    return cyl_y(DISC_D / 2, STD_TOP + 0.5 - 3, STD_TOP + 0.5)


def horn_y():
    return horn_solid().rotate((0, 0, 0), (1, 0, 0), -90).translate((0, CHEEK_IN, 0))


def tt_motor(sx, sy):
    m = mbox(sx, sy, WHEEL_X - 58.5, WHEEL_X + 11.5, MOTOR_Y[0], MOTOR_Y[1], WALL, WALL + 22.5)
    # TT shafts stick out both sides of the gearbox
    return m.union(cyl_y(2.7, -72, 72, x=sx * WHEEL_X, z=SHAFT_Z).intersect(mbox(sx, sy, 0, 100, MOTOR_Y[0] - 9, 72, -10, 50)))


parts = {
    "tub": tub(), "lid": lid(), "turret": turret(), "upper_arm": upper_arm(),
    "forearm": forearm(), "wrist": wrist(), "pinion": pinion(), "jaw_a": jaw_a(), "jaw_b": jaw_b(),
    "gripper_housing": gripper_housing(), "pan_base": pan_base(), "pan_yoke": pan_yoke(), "cam_head": cam_head(), "fender": fender(), "clamp": clamp(), "wheel": wheel(), "tire": tire(),
}

print_rot = {"fender": ((1, 0, 0), 180), "jaw_a": ((1, 0, 0), 90), "jaw_b": ((1, 0, 0), -90), "wheel": ((1, 0, 0), -90), "tire": ((1, 0, 0), -90)}
for name, p in parts.items():
    s = p.val()
    if name in print_rot:
        s = s.rotate(cq.Vector(0, 0, 0), cq.Vector(*print_rot[name][0]), print_rot[name][1])
    bb = s.BoundingBox()
    s = s.translate(cq.Vector(-bb.center.x, -bb.center.y, -bb.zmin))
    cq.exporters.export(cq.Workplane().add(s), f"{OUT}/stl/{name}.stl", tolerance=0.02, angularTolerance=0.15)
    print(name, round(bb.xlen, 1), round(bb.ylen, 1), round(bb.zlen, 1), s.isValid())

yaw = rot((0, 0, 1), YAW, (XT, 0, 0))
sh = shoulder_origin()
upper_loc = yaw * mv(*sh) * rot((0, 1, 0), -SHOULDER)
fore_loc = upper_loc * mv(L1) * rot((0, 1, 0), -ELBOW)
wrist_loc = fore_loc * mv(L2) * rot((0, 1, 0), -WRIST)
g_loc = wrist_loc * mv(GX, YMID, 0) * rot((1, 0, 1), 180)
top = TUB[2] + LID_T

C = {"print": (0.86, 0.33, 0.12), "print2": (0.16, 0.17, 0.18), "servo": (0.15, 0.3, 0.75), "motor": (0.95, 0.78, 0.1),
     "tire": (0.08, 0.08, 0.08), "pcb": (0.1, 0.35, 0.2), "batt": (0.55, 0.55, 0.6), "horn": (0.95, 0.95, 0.95), "print3": (0.33, 0.34, 0.33)}

assy = []
assy.append(("tub", parts["tub"].val(), "print2"))
assy.append(("lid", parts["lid"].val(), "print3"))
assy.append(("clamp_L", parts["clamp"].val(), "print2"))
assy.append(("clamp_R", parts["clamp"].val().mirror("XZ"), "print2"))
assy.append(("turret", parts["turret"].val().moved(yaw), "print"))
assy.append(("upper_arm", parts["upper_arm"].val().moved(upper_loc), "print"))
assy.append(("forearm", parts["forearm"].val().moved(fore_loc), "print"))
assy.append(("wrist", parts["wrist"].val().moved(wrist_loc), "print"))
assy.append(("pinion", parts["pinion"].val().moved(g_loc * rot((0, 0, 1), -math.degrees(OPEN / RP))), "print2"))
assy.append(("jaw_a", parts["jaw_a"].val().moved(g_loc * mv(0, -OPEN)), "print2"))
assy.append(("jaw_b", parts["jaw_b"].val().moved(g_loc * mv(0, OPEN)), "print2"))
assy.append(("gripper_housing", parts["gripper_housing"].val().moved(g_loc), "print"))
assy.append(("fender_L", parts["fender"].val(), "print2"))
assy.append(("fender_R", parts["fender"].val().mirror("XZ"), "print2"))

cam_loc = mv(CAM_AT[0], CAM_AT[1], TUB[2] + LID_T + 9)
yoke_loc = cam_loc * rot((0, 0, 1), PAN)
head_loc = yoke_loc * mv(0, 0, TILT_Z) * rot((0, 1, 0), -TILT)
assy.append(("pan_base", parts["pan_base"].val().moved(cam_loc), "print2"))
assy.append(("pan_yoke", parts["pan_yoke"].val().moved(yoke_loc), "print"))
assy.append(("cam_head", parts["cam_head"].val().moved(head_loc), "print2"))
assy.append(("xiao_s3_sense", box(-5, 6, TILT_Y + CHEEK_IN + 7, TILT_Y + CHEEK_IN + 28, -8.9, 8.9).val().moved(head_loc), "pcb"))
assy.append(("servo_pan", servo().val().moved(cam_loc * mv(0, 0, PAN_TAB) * rot((1, 0, 0), 90)), "servo"))
assy.append(("servo_tilt", servo().val().moved(yoke_loc * mv(0, TILT_Y, TILT_Z) * rot((0, 1, 0), -90)), "servo"))
base_servo_loc = mv(XT, 0, top) * rot((1, 0, 0), 90)
shoulder_servo_loc = yaw * mv(*sh) * rot((0, 1, 0), -90)
assy.append(("servo_shoulder_20kg", std_servo().val().moved(shoulder_servo_loc), "servo"))
assy.append(("disc_horn_shoulder", disc_horn().val().moved(upper_loc), "horn"))
servo_locs = {"servo_base": base_servo_loc,
              "servo_elbow": upper_loc * mv(L1), "servo_wrist": fore_loc * mv(L2), "servo_gripper": g_loc * rot((1, 1, 1), 120)}
horn_locs = {"servo_base": yaw * base_servo_loc, "servo_elbow": fore_loc, "servo_wrist": wrist_loc}
for n, loc in servo_locs.items():
    assy.append((n, servo().val().moved(loc), "servo"))
    if n not in horn_locs:
        continue
    hl = horn_locs[n]
    assy.append((n.replace("servo", "horn"), horn_y().val().moved(hl), "horn"))

for sx in (-1, 1):
    for sy in (-1, 1):
        tag = ("F" if sx > 0 else "R") + ("L" if sy > 0 else "R")
        assy.append((f"tt_motor_{tag}", tt_motor(sx, sy).val(), "motor"))
        w, t = parts["wheel"].val(), parts["tire"].val()
        if sy < 0:
            w, t = w.mirror("XZ"), t.mirror("XZ")
        off = mv(sx * WHEEL_X, sy * 65, SHAFT_Z)
        assy.append((f"wheel_{tag}", w.moved(off), "print3"))
        assy.append((f"tire_{tag}", t.moved(off), "tire"))

assy.append(("battery_2x18650", box(-73, 4, -20.5, 20.5, WALL, WALL + 21).val(), "batt"))
assy.append(("esp32_wroom32u", box(6, 61, -31, -3, WALL + 2, WALL + 4).val(), "pcb"))
assy.append(("zk5ad", box(-45, -19, -15, 15, WALL + 21, WALL + 33).val(), "pcb"))
assy.append(("pca9685", box(5, 67, 5, 30, WALL + 2, WALL + 4).val(), "pcb"))
assy.append(("buck_xl4015", box(-73, -47, -25.5, 25.5, WALL + 21, WALL + 35).val(), "pcb"))

a = cq.Assembly()
for n, s, c in assy:
    a.add(s, name=n, color=cq.Color(*C[c]))
a.save(f"{OUT}/robot_arm_tank_assembly.step")

os.makedirs(f"{OUT}/_mesh", exist_ok=True)
with open(f"{OUT}/_mesh/index.txt", "w") as f:
    for n, s, c in assy:
        cq.exporters.export(cq.Workplane().add(s), f"{OUT}/_mesh/{n}.stl", tolerance=0.05, angularTolerance=0.2)
        f.write(f"{n} {' '.join(map(str, C[c]))}\n")

# interference check between printed parts and the stuff they hold
names = {n: s for n, s, _ in assy}
elec = ["battery_2x18650", "esp32_wroom32u", "zk5ad", "pca9685", "buck_xl4015"]
hull = ["tub", "lid", "clamp_L", "clamp_R", "tt_motor_FL", "tt_motor_FR", "tt_motor_RL", "tt_motor_RR", "servo_base"]
arm = ["turret", "servo_shoulder_20kg", "disc_horn_shoulder", "upper_arm", "servo_elbow", "forearm",
       "servo_wrist", "wrist", "gripper_housing", "servo_gripper", "pinion", "jaw_a", "jaw_b"]
pairs = [(a, b) for i, a in enumerate(elec + hull) for b in (elec + hull)[i + 1:]]
pairs += [(a, b) for i, a in enumerate(arm) for b in arm[i + 1:]]
pairs += [(a, b) for a in arm for b in ["lid", "fender_L", "fender_R", "tub"]]
cam = ["pan_base", "servo_pan", "pan_yoke", "servo_tilt", "cam_head", "xiao_s3_sense"]
pairs += [(a, b) for i, a in enumerate(cam) for b in cam[i + 1:] if (a, b) != ("pan_base", "servo_pan")]
pairs += [(a, b) for a in cam for b in arm + ["lid", "fender_L", "fender_R", "tub", "wheel_FL", "tire_FL"]]
pairs += [("pan_base", "servo_pan"), ("fender_L", "wheel_FL"), ("fender_L", "tire_FL"), ("fender_R", "tire_FR"), ("tub", "wheel_FL"), ("fender_L", "lid")]
expected = {("servo_shoulder_20kg", "disc_horn_shoulder")}
for a_, b_ in pairs:
    if (a_, b_) in expected or a_.startswith("horn") or b_.startswith("horn"):
        continue
    v = names[a_].intersect(names[b_]).Volume()
    if v > 0.05:
        print(f"clash {a_} x {b_}: {v:.1f} mm3")
print("checked", len(pairs))
