"""Isolated checkpoint: Isaac rigid motion -> USD samples -> GLB candidate.

Run only inside an isolated Isaac Sim 6.1 container with /work mounted to the
separate exporter workspace. This is a focused experiment, not the exporter.
"""

import json
import os
import traceback
from pathlib import Path

from isaacsim import SimulationApp

app = SimulationApp({"headless": True, "renderer": "RaytracedLighting"})

import omni.kit.commands
import omni.usd
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdShade, UsdPhysics

from isaacsim.core.experimental.prims import GeomPrim, RigidPrim
import isaacsim.core.experimental.utils.app as app_utils
import isaacsim.core.experimental.utils.stage as stage_utils


OUT = Path("/work/checkpoint1/output")
OUT.mkdir(parents=True, exist_ok=True)


def make_mesh_box(stage, path, size, color, center):
    x, y, z = [s / 2.0 for s in size]
    vertices = [
        Gf.Vec3f(-x, -y, -z), Gf.Vec3f(x, -y, -z),
        Gf.Vec3f(x, y, -z), Gf.Vec3f(-x, y, -z),
        Gf.Vec3f(-x, -y, z), Gf.Vec3f(x, -y, z),
        Gf.Vec3f(x, y, z), Gf.Vec3f(-x, y, z),
    ]
    faces = [0, 3, 2, 1, 4, 5, 6, 7, 0, 1, 5, 4,
             1, 2, 6, 5, 2, 3, 7, 6, 3, 0, 4, 7]
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr(vertices)
    mesh.CreateFaceVertexCountsAttr([4] * 6)
    mesh.CreateFaceVertexIndicesAttr(faces)
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.AddTranslateOp().Set(Gf.Vec3d(*center))

    material = UsdShade.Material.Define(stage, "/World/Looks/" + path.rsplit("/", 1)[-1])
    shader = UsdShade.Shader.Define(stage, str(material.GetPath()) + "/PBR")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.65)
    shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)
    return mesh


report = {"status": "started", "recorder": {}, "samples": {}, "converter": {}}

try:
    stage_utils.create_new_stage()
    stage = omni.usd.get_context().get_stage()
    stage.SetTimeCodesPerSecond(30)
    stage.SetFramesPerSecond(30)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    UsdGeom.Scope.Define(stage, "/World/Looks")
    floor = make_mesh_box(stage, "/World/Floor", (4, 4, 0.15), (0.45, 0.55, 0.65), (0, 0, -0.075))
    UsdPhysics.CollisionAPI.Apply(floor.GetPrim())
    falling = make_mesh_box(stage, "/World/FallingBox", (0.5, 0.5, 0.5), (0.95, 0.2, 0.12), (0, 0, 2.0))
    rigid = RigidPrim(paths="/World/FallingBox")
    collider = GeomPrim(paths="/World/FallingBox", apply_collision_apis=True)
    camera = UsdGeom.Camera.Define(stage, "/World/Camera")
    camera.AddTranslateOp().Set(Gf.Vec3d(3, -5, 3))
    light = UsdLux.DistantLight.Define(stage, "/World/Light")
    light.CreateIntensityAttr(800.0)
    app.update()
    base = OUT / "base.usda"
    stage.Export(str(base))
    print("CHECKPOINT_BASE", base, flush=True)

    try:
        manager = omni.kit.app.get_app().get_extension_manager()
        manager.set_extension_enabled_immediate("omni.kit.stagerecorder.core", True)
        app.update()
        result = omni.kit.commands.execute(
            "StartRecording",
            target_paths=[("/World", True)], live_mode=True,
            use_frame_range=False, start_frame=0, end_frame=0,
            use_preroll=False, preroll_frame=0, record_to="FILE",
            take_name="stage_recording", record_folder=str(OUT),
            increment_name=False, apply_root_anim=False, fps=30.0,
        )
        report["recorder"]["start"] = str(result)
        print("CHECKPOINT_RECORDER_START", result, flush=True)
    except Exception as error:
        report["recorder"]["start_error"] = repr(error)
        traceback.print_exc()

    app_utils.play()
    app.update()
    poses = []
    for frame in range(121):
        app.update()
        if frame % 2 == 0:
            positions, orientations = rigid.get_world_poses()
            pos = [float(x) for x in positions.numpy()[0]]
            quat = [float(x) for x in orientations.numpy()[0]]
            poses.append((frame / 2, pos, quat))
            if frame % 30 == 0:
                print("CHECKPOINT_POSE", frame, pos, quat, flush=True)
    try:
        result = omni.kit.commands.execute("StopRecording")
        report["recorder"]["stop"] = str(result)
        print("CHECKPOINT_RECORDER_STOP", result, flush=True)
    except Exception as error:
        report["recorder"]["stop_error"] = repr(error)
        traceback.print_exc()
    app_utils.stop()
    app.update()

    # Explicit pose track guarantees that the visual state read from PhysX is
    # represented as ordinary USD samples, even if recorder/Fabric misses it.
    animated = Usd.Stage.Open(str(base))
    animated.SetStartTimeCode(0)
    animated.SetEndTimeCode(60)
    animated.SetTimeCodesPerSecond(30)
    animated.SetFramesPerSecond(30)
    mesh = UsdGeom.Mesh.Get(animated, "/World/FallingBox")
    transform = UsdGeom.Xformable(mesh.GetPrim())
    transform.ClearXformOpOrder()
    translation = transform.AddTranslateOp()
    rotation = transform.AddOrientOp()
    for timecode, pos, quat in poses:
        translation.Set(Gf.Vec3d(*pos), timecode)
        rotation.Set(Gf.Quatf(quat[0], quat[1], quat[2], quat[3]), timecode)
    scene = OUT / "recorded_scene.usda"
    animated.GetRootLayer().Export(str(scene))
    sampled = [round(float(p[1][2]), 5) for p in poses]
    report["samples"] = {
        "count": len(poses), "first_z": sampled[0], "last_z": sampled[-1],
        "min_z": min(sampled), "max_z": max(sampled),
        "position_changes": len(set(sampled)), "scene": str(scene),
    }
    print("CHECKPOINT_SAMPLES", json.dumps(report["samples"]), flush=True)

    try:
        import omni.kit.asset_converter as converter
        context = converter.AssetConverterContext()
        context.ignore_animations = False
        context.embed_textures = True
        context.export_mdl_gltf_extension = False
        glb = OUT / "scene.glb"
        task = converter.get_instance().create_converter_task(str(scene), str(glb), None, context)
        # Kit's asynchronous task needs update ticks.
        import asyncio
        future = asyncio.ensure_future(task.wait_until_finished())
        for _ in range(1000):
            if future.done():
                break
            app.update()
        success = bool(future.result()) if future.done() else False
        report["converter"] = {
            "success": success, "status": str(task.get_status()),
            "error": task.get_error_message(), "path": str(glb),
            "bytes": glb.stat().st_size if glb.exists() else 0,
        }
        print("CHECKPOINT_CONVERTER", json.dumps(report["converter"]), flush=True)
    except Exception as error:
        report["converter"]["exception"] = repr(error)
        traceback.print_exc()

    report["status"] = "finished"
except Exception as error:
    report["status"] = "failed"
    report["error"] = repr(error)
    traceback.print_exc()
finally:
    (OUT / "checkpoint-report.json").write_text(json.dumps(report, indent=2))
    print("CHECKPOINT_REPORT", json.dumps(report), flush=True)
    app.close()
