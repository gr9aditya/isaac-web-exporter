"""Capture GUI viewport frames from an isolated Isaac/Xvfb session."""

import hashlib
import json
import math
from pathlib import Path

from isaacsim import SimulationApp

app = SimulationApp({"headless": False, "renderer": "RaytracedLighting"})
status = 1
try:
    import numpy as np
    from PIL import ImageGrab
    import omni.timeline
    import omni.usd
    from omni.kit.viewport.utility import get_active_viewport, frame_viewport_prims
    from pxr import Gf, UsdGeom, UsdLux
    import isaacsim.core.utils.stage as stage_utils

    source = Path("/work/runs/v1-sort-cell-guided/recorded_scene.usda")
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    output = Path("/work/runs/v1-reference-viewport")
    output.mkdir(parents=True, exist_ok=True)
    if not stage_utils.open_stage(str(source)):
        raise RuntimeError("Could not open recorded stage")
    stage = omni.usd.get_context().get_stage()
    light = UsdLux.DistantLight.Define(stage, "/World/ReferenceLight")
    light.CreateIntensityAttr(1800)
    eye, target = Gf.Vec3d(7, -9, 6), Gf.Vec3d(0, -0.5, 0.6)
    world = Gf.Matrix4d().SetLookAt(eye, target, Gf.Vec3d(0, 0, 1)).GetInverse()
    camera = UsdGeom.Camera.Define(stage, "/World/ReferenceCamera")
    UsdGeom.Xformable(camera.GetPrim()).AddTransformOp().Set(world)
    camera.CreateHorizontalApertureAttr(20.955)
    camera.CreateVerticalApertureAttr(20.955 * 720 / 1280)
    camera.CreateFocalLengthAttr(20.955 / (2 * math.tan(math.radians(50) / 2)) * 720 / 1280)
    viewport = get_active_viewport()
    if viewport is None:
        raise RuntimeError("No Isaac viewport")
    viewport.camera_path = "/OmniverseKit_Persp"
    frame_viewport_prims(viewport, prims=["/World"])
    for _ in range(90):
        app.update()
    ImageGrab.grab(xdisplay=":97").convert("RGB").save(output / "isaac-perspective-diagnostic.png")
    viewport.camera_path = str(camera.GetPath())
    timeline = omni.timeline.get_timeline_interface()
    result = []
    for seconds in (0.0, 15.0, 30.0):
        timeline.set_current_time(seconds)
        for _ in range(90):
            app.update()
        frame = ImageGrab.grab(xdisplay=":97").convert("RGB")
        path = output / f"isaac-full-{int(seconds)}.png"
        frame.save(path)
        # Default Isaac desktop viewport is the left pane; preserve full UI too.
        crop = frame.crop((52, 34, 988, 568))
        crop_path = output / f"isaac-viewport-{int(seconds)}.png"
        crop.save(crop_path)
        pixels = np.asarray(crop)
        item = {"seconds": seconds, "full": str(path), "viewport": str(crop_path),
                "size": list(crop.size), "stdDev": float(pixels.std()),
                "mean": float(pixels.mean())}
        result.append(item)
        print("ISAAC_VIEWPORT_FRAME", json.dumps(item), flush=True)
        if item["stdDev"] < 3:
            raise RuntimeError(f"Reference viewport is blank at {seconds}s")
    final_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    if final_sha != source_sha:
        raise RuntimeError("Source recorded USD changed during reference capture")
    (output / "report.json").write_text(json.dumps({
        "sourceSha256": source_sha, "frames": result,
        "cameraUsd": {"eye": [7, -9, 6], "target": [0, -0.5, 0.6], "fovY": 50},
        "renderer": "Isaac Sim 6.1 RTX Real-Time 2.0 on Xvfb :97",
    }, indent=2), encoding="utf-8")
    print("ISAAC_VIEWPORT_REFERENCE", json.dumps(result), flush=True)
    status = 0
except Exception as error:
    import traceback
    traceback.print_exc()
    print("ISAAC_VIEWPORT_ERROR", repr(error), flush=True)
finally:
    app.close(exit_code=status)
