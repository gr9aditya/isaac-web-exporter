"""Capture nonempty Isaac RGB for the owned sort fixture at three times."""

import json
import math
import sys
import time
from pathlib import Path

sys.argv.append("--/exts/isaacsim.core.throttling/enable_async=false")
sys.argv.append("--reset-user")
from isaacsim import SimulationApp

app = SimulationApp({"headless": True, "renderer": "RaytracedLighting"})
status = 1
try:
    import numpy as np
    from PIL import Image
    import omni.timeline
    import omni.usd
    import omni.replicator.core as rep
    from pxr import Gf, UsdGeom, UsdLux
    import isaacsim.core.utils.stage as stage_utils

    source = "/work/runs/v1-sort-cell-guided/recorded_scene.usda"
    output = Path("/work/runs/v1-reference")
    output.mkdir(parents=True, exist_ok=True)
    if not stage_utils.open_stage(source):
        raise RuntimeError("Cannot open sort workflow in Isaac context")
    stage = omni.usd.get_context().get_stage()
    light = UsdLux.DistantLight.Define(stage, "/World/ReferenceLight")
    light.CreateIntensityAttr(1800)
    # Viewer camera (7, 6, 9) Y-up maps to Isaac (7, -9, 6) Z-up.
    eye = Gf.Vec3d(7, -9, 6)
    target = Gf.Vec3d(0, -0.5, 0.6)
    world = Gf.Matrix4d().SetLookAt(eye, target, Gf.Vec3d(0, 0, 1)).GetInverse()
    camera_prim = UsdGeom.Camera.Define(stage, "/World/ReferenceCamera")
    UsdGeom.Xformable(camera_prim.GetPrim()).AddTransformOp().Set(world)
    camera_prim.CreateHorizontalApertureAttr(20.955)
    camera_prim.CreateVerticalApertureAttr(20.955 * 720 / 1280)
    camera_prim.CreateFocalLengthAttr(20.955 / (2 * math.tan(math.radians(50) / 2)) * 720 / 1280)
    render_product = rep.create.render_product(camera_prim.GetPath(), (1280, 720))
    rep.orchestrator.set_capture_on_play(False)
    annotator = rep.annotators.get("rgb")
    annotator.attach(render_product)
    timeline = omni.timeline.get_timeline_interface()
    timeline.play()
    for _ in range(3):
        app.update()
    captured = []
    for seconds in (0.0, 15.0, 30.0):
        timeline.set_current_time(seconds)
        array = None
        for attempt in range(4):
            for _ in range(5):
                app.update()
            rep.orchestrator.step(rt_subframes=8, pause_timeline=True,
                                  delta_time=0.0, wait_for_render=True)
            rep.orchestrator.wait_until_complete()
            data = annotator.get_data()
            array = np.asarray(data)
            print("REFERENCE_ATTEMPT", seconds, attempt, array.shape, flush=True)
            if array.size:
                break
        if array is None or not array.size:
            raise RuntimeError(f"Isaac returned empty RGB at {seconds}s")
        if array.ndim == 1 and array.size % (1280 * 720) == 0:
            array = array.reshape((720, 1280, array.size // (1280 * 720)))
        if array.ndim != 3 or array.shape[2] < 3:
            raise RuntimeError(f"Unexpected RGB shape: {array.shape}")
        if array.dtype != np.uint8:
            array = (np.clip(array, 0, 1) * 255).astype(np.uint8)
        path = output / f"isaac-{int(seconds)}.png"
        Image.fromarray(array[:, :, :3]).save(path)
        captured.append({"seconds": seconds, "image": str(path),
                         "shape": list(array.shape),
                         "pixelStdDev": float(array[:, :, :3].std())})
    print("ISAAC_REFERENCE_V1", json.dumps(captured), flush=True)
    annotator.detach()
    render_product.destroy()
    status = 0
except Exception as error:
    import traceback
    traceback.print_exc()
    print("ISAAC_REFERENCE_ERROR", repr(error), flush=True)
finally:
    app.close(exit_code=status)
