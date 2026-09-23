"""Render first/last frames of the self-authored v0 fixture in isolated Isaac."""

from pathlib import Path
import json
import time

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

    source = "/work/runs/v0-falling-box/recorded_scene.usda"
    output = Path("/work/runs/isaac-reference")
    output.mkdir(parents=True, exist_ok=True)
    if not stage_utils.open_stage(source):
        raise RuntimeError("Cannot open recorded fixture in Isaac context")
    stage = omni.usd.get_context().get_stage()
    light = UsdLux.DistantLight.Define(stage, "/World/ReferenceLight")
    light.CreateIntensityAttr(750)
    eye, target, up = Gf.Vec3d(4, 4, 3), Gf.Vec3d(0, 0, 0.8), Gf.Vec3d(0, 0, 1)
    world = Gf.Matrix4d().SetLookAt(eye, target, up).GetInverse()
    camera_prim = UsdGeom.Camera.Define(stage, "/World/ReferenceCamera")
    UsdGeom.Xformable(camera_prim.GetPrim()).AddTransformOp().Set(world)
    render_product = rep.create.render_product(camera_prim.GetPath(), (960, 720))
    annotator = rep.annotators.get("rgb")
    annotator.attach(render_product)
    timeline = omni.timeline.get_timeline_interface()
    images = []
    for second in (0.0, 5.0):
        timeline.set_current_time(second)
        rgb = None
        for attempt in range(3):
            rep.orchestrator.step(rt_subframes=16, delta_time=0.0)
            rep.orchestrator.wait_until_complete()
            for _ in range(10):
                app.update()
                time.sleep(0.05)
            rgb = annotator.get_data()
            print("ISAAC_CAPTURE_ATTEMPT", second, attempt, np.asarray(rgb).shape, flush=True)
            if rgb is not None and np.asarray(rgb).size:
                break
        if rgb is None:
            raise RuntimeError(f"No camera RGB at {second}s")
        array = np.asarray(rgb)
        print("ISAAC_RGB_DATA", second, array.shape, str(array.dtype), flush=True)
        if array.ndim == 1 and array.size and array.size % (960 * 720) == 0:
            array = array.reshape((720, 960, array.size // (960 * 720)))
        if array.ndim != 3 or array.shape[2] < 3:
            raise RuntimeError(f"Unexpected RGB shape at {second}s: {array.shape}")
        if array.dtype != np.uint8:
            array = (np.clip(array, 0, 1) * 255).astype(np.uint8)
        path = output / f"isaac-{int(second)}.png"
        Image.fromarray(array[:, :, :3]).save(path)
        images.append({"timeSeconds": second, "path": str(path), "shape": list(array.shape)})
    rep.orchestrator.wait_until_complete()
    annotator.detach()
    render_product.destroy()
    print("ISAAC_REFERENCE", json.dumps(images), flush=True)
    status = 0
except Exception as exc:
    import traceback
    traceback.print_exc()
    print("ISAAC_REFERENCE_ERROR", repr(exc), flush=True)
finally:
    app.close(exit_code=status)
