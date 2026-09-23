"""Create an owned reference-heavy USD fixture for panel conversion cancellation."""

from pathlib import Path

from isaacsim import SimulationApp

app = SimulationApp({"headless": True, "renderer": "MinimalRendering", "limit_cpu_threads": 2})
from pxr import Gf, Usd, UsdGeom


source = Path("/work/runs/v1-sort-cell-guided/recorded_scene.usda")
target = Path("/work/runs/v1-f03-conversion-stress-b.usda")
if target.exists():
    raise FileExistsError(target)
if not source.is_file():
    raise FileNotFoundError(source)

stage = Usd.Stage.CreateNew(str(target))
stage.SetMetadata("upAxis", "Z")
stage.SetStartTimeCode(0)
stage.SetEndTimeCode(900)
stage.SetTimeCodesPerSecond(30)
root = UsdGeom.Xform.Define(stage, "/World")
stage.SetDefaultPrim(root.GetPrim())
for index in range(400):
    cell = UsdGeom.Xform.Define(stage, f"/World/Cell_{index:04d}")
    cell.GetPrim().GetReferences().AddReference(str(source), "/World")
    cell.AddTranslateOp().Set(Gf.Vec3d((index % 20) * 7, (index // 20) * 7, 0))
stage.GetRootLayer().Save()
print(f"F03_STRESS_USD {target} {target.stat().st_size} bytes 400 references", flush=True)
app.close()
