"""Inspect native Stage Recorder output from the isolated checkpoint."""

import asyncio
import json
from pathlib import Path
from isaacsim import SimulationApp

app = SimulationApp({"headless": True})
from pxr import Sdf, Usd, UsdGeom
import omni.kit.asset_converter as converter

out = Path("/work/checkpoint1/output")
try:
    recording = Usd.Stage.Open(str(out / "stage_recording.usd"))
    prim = recording.GetPrimAtPath("/World/FallingBox")
    attrs = {}
    for attr in prim.GetAttributes():
        times = attr.GetTimeSamples()
        if times:
            attrs[attr.GetName()] = {
                "samples": len(times), "first_time": times[0], "last_time": times[-1],
                "first_value": str(attr.Get(times[0]))[:180],
                "last_value": str(attr.Get(times[-1]))[:180],
            }

    root = Sdf.Layer.CreateNew(str(out / "stage_composed.usda"))
    root.subLayerPaths = ["stage_recording.usd", "base.usda"]
    root.Save()
    composed = Usd.Stage.Open(root)
    end = max((value["last_time"] for value in attrs.values()), default=0.0)
    composed.SetStartTimeCode(0)
    composed.SetEndTimeCode(end)
    composed.SetTimeCodesPerSecond(30)
    composed.SetFramesPerSecond(30)
    root.Save()
    composed_box = UsdGeom.Xformable(composed.GetPrimAtPath("/World/FallingBox"))
    first_matrix = composed_box.GetLocalTransformation(Usd.TimeCode(0))
    last_matrix = composed_box.GetLocalTransformation(Usd.TimeCode(end))
    def transform_summary(stage):
        box = UsdGeom.Xformable(stage.GetPrimAtPath("/World/FallingBox"))
        return {
            "order": str(box.GetXformOpOrderAttr().Get()),
            "ops": {
                op.GetOpName(): {
                    "samples": len(op.GetAttr().GetTimeSamples()),
                    "at_zero": str(op.Get(Usd.TimeCode(0)))[:180],
                    "at_end": str(op.Get(Usd.TimeCode(end)))[:180],
                }
                for op in box.GetOrderedXformOps()
            },
        }
    report = {
        "prim_valid": bool(prim),
        "animated_attributes": attrs,
        "composed_prim_valid": bool(composed.GetPrimAtPath("/World/FallingBox")),
        "composed_time_range": [composed.GetStartTimeCode(), composed.GetEndTimeCode()],
        "composed_first_z": float(first_matrix.ExtractTranslation()[2]),
        "composed_last_z": float(last_matrix.ExtractTranslation()[2]),
        "base_transform": transform_summary(Usd.Stage.Open(str(out / "base.usda"))),
        "recording_transform": transform_summary(recording),
        "composed_transform": transform_summary(composed),
    }
    context = converter.AssetConverterContext()
    context.ignore_animations = False
    context.embed_textures = True
    context.export_mdl_gltf_extension = False
    glb = out / "scene_from_recorder.glb"
    task = converter.get_instance().create_converter_task(str(out / "stage_composed.usda"), str(glb), None, context)
    future = asyncio.ensure_future(task.wait_until_finished())
    for _ in range(1000):
        if future.done():
            break
        app.update()
    report["native_converter"] = {
        "success": bool(future.result()) if future.done() else False,
        "status": str(task.get_status()),
        "error": task.get_error_message(),
        "bytes": glb.stat().st_size if glb.exists() else 0,
    }
    flattened = out / "stage_flattened.usda"
    composed.Flatten().Export(str(flattened))
    flat_glb = out / "scene_flattened.glb"
    flat_task = converter.get_instance().create_converter_task(str(flattened), str(flat_glb), None, context)
    flat_future = asyncio.ensure_future(flat_task.wait_until_finished())
    for _ in range(1000):
        if flat_future.done():
            break
        app.update()
    report["flattened_converter"] = {
        "success": bool(flat_future.result()) if flat_future.done() else False,
        "status": str(flat_task.get_status()),
        "error": flat_task.get_error_message(),
        "bytes": flat_glb.stat().st_size if flat_glb.exists() else 0,
    }
    (out / "recorder-inspection.json").write_text(json.dumps(report, indent=2))
    print("RECORDER_INSPECTION", json.dumps(report), flush=True)
finally:
    app.close()
