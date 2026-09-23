"""Second independent Isaac project: robotic inspection cell, isolated from user projects.

This is a fixture plus a repeat of checkpoint one's capture/conversion procedure.
It tests multiple rigid bodies and authored hierarchy animation, not a finished exporter.
"""

import asyncio
import json
import math
import traceback
from pathlib import Path

from isaacsim import SimulationApp

app = SimulationApp({"headless": True, "renderer": "RaytracedLighting"})

import omni.usd
import omni.kit.asset_converter as converter
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade
from isaacsim.core.experimental.prims import GeomPrim, RigidPrim
import isaacsim.core.experimental.utils.app as app_utils
import isaacsim.core.experimental.utils.stage as stage_utils

OUT = Path("/work/checkpoint2/output")
OUT.mkdir(parents=True, exist_ok=True)


def box(stage, path, size, color, center):
    x, y, z = [s / 2 for s in size]
    vertices = [
        Gf.Vec3f(-x, -y, -z), Gf.Vec3f(x, -y, -z),
        Gf.Vec3f(x, y, -z), Gf.Vec3f(-x, y, -z),
        Gf.Vec3f(-x, -y, z), Gf.Vec3f(x, -y, z),
        Gf.Vec3f(x, y, z), Gf.Vec3f(-x, y, z),
    ]
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr(vertices)
    mesh.CreateFaceVertexCountsAttr([4] * 6)
    mesh.CreateFaceVertexIndicesAttr([
        0, 3, 2, 1, 4, 5, 6, 7, 0, 1, 5, 4,
        1, 2, 6, 5, 2, 3, 7, 6, 3, 0, 4, 7,
    ])
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.AddTranslateOp().Set(Gf.Vec3d(*center))
    mat_path = "/World/Looks/" + path.strip("/").replace("/", "_")
    material = UsdShade.Material.Define(stage, mat_path)
    shader = UsdShade.Shader.Define(stage, mat_path + "/PBR")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.55)
    shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)
    return mesh


report = {"status": "started", "fixture": "inspection-cell", "samples": {}, "converter": {}}
try:
    stage_utils.create_new_stage()
    stage = omni.usd.get_context().get_stage()
    stage.SetTimeCodesPerSecond(30)
    stage.SetFramesPerSecond(30)
    stage.SetStartTimeCode(0)
    stage.SetEndTimeCode(60)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    UsdGeom.Scope.Define(stage, "/World/Looks")

    floor = box(stage, "/World/Floor", (6, 5, 0.15), (0.29, 0.34, 0.40), (0, 0, -0.075))
    UsdPhysics.CollisionAPI.Apply(floor.GetPrim())
    box(stage, "/World/Robot/Base", (0.65, 0.65, 1.1), (0.18, 0.37, 0.77), (-1.6, 0, 0.55))
    pivot = UsdGeom.Xform.Define(stage, "/World/Robot/Pivot")
    pivot.AddTranslateOp().Set(Gf.Vec3d(-1.6, 0, 1.15))
    turn = pivot.AddRotateZOp()
    box(stage, "/World/Robot/Pivot/Arm", (1.8, 0.20, 0.20), (0.22, 0.63, 0.86), (0.9, 0, 0))
    box(stage, "/World/Robot/Pivot/Tool", (0.22, 0.35, 0.50), (0.95, 0.75, 0.18), (1.8, 0, -0.18))
    carrier = UsdGeom.Xform.Define(stage, "/World/Carrier")
    travel = carrier.AddTranslateOp()
    box(stage, "/World/Carrier/Tray", (0.72, 0.72, 0.12), (0.35, 0.70, 0.45), (0, 0, 0.55))

    for tick in range(61):
        turn.Set(-40 + 80 * tick / 60, tick)
        travel.Set(Gf.Vec3d(0.45 + 0.9 * tick / 60, -1.25, 0), tick)

    payloads = [
        ("/World/PayloadA", (0.32, 0.32, 0.32), (0.90, 0.20, 0.22), (0.55, 0.55, 2.0)),
        ("/World/PayloadB", (0.44, 0.26, 0.28), (0.93, 0.54, 0.12), (1.45, 0.45, 2.6)),
    ]
    for path, size, color, center in payloads:
        mesh = box(stage, path, size, color, center)
        GeomPrim(paths=path, apply_collision_apis=True)
    rigs = {path: RigidPrim(paths=path) for path, *_ in payloads}
    app.update()
    base = OUT / "inspection_cell_base.usda"
    stage.Export(str(base))

    app_utils.play()
    app.update()
    samples = {path: [] for path in rigs}
    for frame in range(121):
        app.update()
        if frame % 2 == 0:
            for path, rig in rigs.items():
                positions, orientations = rig.get_world_poses()
                pos = [float(x) for x in positions.numpy()[0]]
                quat = [float(x) for x in orientations.numpy()[0]]
                samples[path].append((frame / 2, pos, quat))
    app_utils.stop()
    app.update()

    result = Usd.Stage.Open(str(base))
    for path, track in samples.items():
        mesh = UsdGeom.Mesh.Get(result, path)
        xform = UsdGeom.Xformable(mesh.GetPrim())
        xform.ClearXformOpOrder()
        translate = xform.AddTranslateOp()
        orient = xform.AddOrientOp()
        for timecode, pos, quat in track:
            translate.Set(Gf.Vec3d(*pos), timecode)
            orient.Set(Gf.Quatf(*quat), timecode)
        zs = [round(s[1][2], 5) for s in track]
        report["samples"][path] = {
            "count": len(track), "first_z": zs[0], "last_z": zs[-1],
            "position_changes": len(set(zs)),
        }
    recorded = OUT / "inspection_cell_recorded.usda"
    result.GetRootLayer().Export(str(recorded))

    context = converter.AssetConverterContext()
    context.ignore_animations = False
    context.embed_textures = True
    context.export_mdl_gltf_extension = False
    glb = OUT / "scene.glb"
    task = converter.get_instance().create_converter_task(str(recorded), str(glb), None, context)
    future = asyncio.ensure_future(task.wait_until_finished())
    for _ in range(1000):
        if future.done():
            break
        app.update()
    success = bool(future.result()) if future.done() else False
    report["converter"] = {
        "success": success, "status": str(task.get_status()),
        "error": task.get_error_message(), "bytes": glb.stat().st_size if glb.exists() else 0,
    }
    report["status"] = "finished"
except Exception as error:
    report["status"] = "failed"
    report["error"] = repr(error)
    traceback.print_exc()
finally:
    (OUT / "test-report.json").write_text(json.dumps(report, indent=2))
    print("SECOND_PROJECT_REPORT", json.dumps(report), flush=True)
    app.close()
