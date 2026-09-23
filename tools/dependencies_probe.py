"""Inspect the installed OpenUSD dependency API in the isolated Isaac runtime."""

import json
from isaacsim import SimulationApp

app = SimulationApp({"headless": True})
status = 1
try:
    from pxr import Sdf, UsdUtils
    results = {}
    for label, path in {
        "box": "/work/runs/falling-box-final/recorded_scene.usda",
        "factory": "/work/runs/factory-conveyor-v5/recorded_scene.usda",
    }.items():
        value = UsdUtils.ComputeAllDependencies(Sdf.AssetPath(path))
        results[label] = {
            "type": type(value).__name__,
            "length": len(value),
            "layers": len(value[0]),
            "assets": [str(item) for item in value[1]][:20],
            "unresolved": [str(item) for item in value[2]][:30],
        }
    print("DEPENDENCY_PROBE", json.dumps(results), flush=True)
    status = 0
except Exception as exc:
    import traceback
    traceback.print_exc()
    print("DEPENDENCY_PROBE_ERROR", repr(exc), flush=True)
finally:
    app.close(exit_code=status)
