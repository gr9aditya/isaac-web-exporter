"""Determine whether this isolated Xvfb/Isaac build renders a stock cube."""

from pathlib import Path
import time
from isaacsim import SimulationApp

app = SimulationApp({"headless": False, "renderer": "RaytracedLighting"})
try:
    from PIL import ImageGrab
    import omni.usd
    from omni.kit.viewport.utility import get_active_viewport, frame_viewport_prims
    from pxr import Gf, UsdGeom, UsdLux
    import isaacsim.core.experimental.utils.stage as stage_utils

    stage_utils.create_new_stage()
    stage = omni.usd.get_context().get_stage()
    UsdGeom.Xform.Define(stage, "/World")
    cube = UsdGeom.Cube.Define(stage, "/World/DiagnosticCube")
    cube.CreateSizeAttr(2)
    cube.CreateDisplayColorAttr([Gf.Vec3f(0.9, 0.1, 0.1)])
    light = UsdLux.DistantLight.Define(stage, "/World/DiagnosticLight")
    light.CreateIntensityAttr(3000)
    viewport = get_active_viewport()
    viewport.camera_path = "/OmniverseKit_Persp"
    frame_viewport_prims(viewport, prims=["/World/DiagnosticCube"])
    for index in range(200):
        app.update()
        time.sleep(0.1)
        if index % 50 == 0:
            print("CUBE_RENDER_WAIT", index, flush=True)
    target = Path("/work/runs/v1-diagnostic-cube.png")
    ImageGrab.grab(xdisplay=":97").save(target)
    print("ISAAC_CUBE_SCREENSHOT", target, flush=True)
finally:
    app.close()
