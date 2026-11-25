# blender -b -P render.py -- <mesh_dir> <out_prefix> [views] [blend_out]
# views: comma list of iso,side,camera,folded (folded just reuses the iso camera on a folded mesh dir)
import math
import sys
import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
mesh_dir, out = args[0], args[1]
# views "none" just rebuilds the .blend (no PNGs)
views = [v for v in args[2].split(",") if v not in ("", "none")] if len(args) > 2 else ["iso", "side", "camera"]
blend_out = args[3] if len(args) > 3 else None

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

mats = {}
for line in open(f"{mesh_dir}/index.txt"):
    name, r, g, b = line.split()
    bpy.ops.wm.stl_import(filepath=f"{mesh_dir}/{name}.stl")
    ob = bpy.context.selected_objects[0]
    ob.name = name
    ob.scale = (0.001, 0.001, 0.001)
    key = (r, g, b)
    if key not in mats:
        m = bpy.data.materials.new(f"m{len(mats)}")
        m.use_nodes = True
        bsdf = m.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = (float(r), float(g), float(b), 1)
        bsdf.inputs["Roughness"].default_value = 0.55
        mats[key] = m
    ob.data.materials.append(mats[key])
    for p in ob.data.polygons:
        p.use_smooth = False

bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, 0))
floor = bpy.context.active_object
fm = bpy.data.materials.new("floor")
fm.use_nodes = True
fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.8, 0.78, 1)
floor.data.materials.append(fm)

sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3.5
sun.data.angle = math.radians(8)
sun.rotation_euler = (math.radians(40), math.radians(-15), math.radians(-35))
scene.collection.objects.link(sun)
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.85, 0.87, 0.9, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
scene.world = world

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.lens = 50
scene.collection.objects.link(cam)
scene.camera = cam
scene.render.engine = "CYCLES"
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 1400, 950

target = Vector((0.03, 0, 0.11))
POS = {"iso": (0.5, 0.45, 0.36), "side": (0.03, 0.72, 0.13), "camera": (-0.5, 0.36, 0.4), "folded": (0.5, 0.45, 0.36)}


def aim(loc):
    cam.location = Vector(loc)
    d = target - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


for v in views:
    aim(POS[v])
    scene.render.filepath = f"{out}_{v}.png"
    bpy.ops.render.render(write_still=True)

if blend_out:
    aim(POS["iso"])
    bpy.ops.wm.save_as_mainfile(filepath=blend_out)
