"""Render three source-USD reference frames with installed OpenUSD's CPU Hydra.

Run with Isaac Sim's python.sh, which supplies the exact pxr bindings used by the
exporter. The renderer is deliberately independent of the browser GLB.
"""

import argparse
import json
import math
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    from isaacsim import SimulationApp
    app = SimulationApp({"headless": True})
    from pxr import Gf, Usd, UsdAppUtils, UsdGeom
    args.output.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.Open(str(args.source))
    if stage is None:
        raise RuntimeError(f"USD stage could not be opened: {args.source}")
    eye = Gf.Vec3d(7, -9, 6)
    target = Gf.Vec3d(0, -0.5, 0.6)
    world = Gf.Matrix4d().SetLookAt(eye, target, Gf.Vec3d(0, 0, 1)).GetInverse()
    camera = UsdGeom.Camera.Define(stage, "/ReferenceCamera")
    camera.AddTransformOp().Set(world)
    camera.CreateHorizontalApertureAttr(20.955)
    camera.CreateVerticalApertureAttr(20.955 * 720 / 1280)
    camera.CreateFocalLengthAttr(20.955 / (2 * math.tan(math.radians(50) / 2)) * 720 / 1280)
    recorder = UsdAppUtils.FrameRecorder(gpuEnabled=False)
    print("RENDERERS", recorder.GetCurrentRendererId(), recorder.GetRendererAovs(), flush=True)
    recorder.SetImageWidth(1280)
    recorder.SetComplexity(1.0)
    results = []
    for second in (0, 15, 30):
        output = args.output / f"usd-source-{second}.png"
        ok = recorder.Record(stage, camera, Usd.TimeCode(second * 30), str(output))
        if not ok or not output.is_file():
            raise RuntimeError(f"CPU source reference failed at {second}s")
        results.append({"seconds": second, "path": str(output), "bytes": output.stat().st_size})
    print("USD_SOURCE_REFERENCE", json.dumps(results), flush=True)
    app.close()


if __name__ == "__main__":
    main()
