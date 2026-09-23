"""Author and export an owned nonzero-start USD recording."""

import json
import sys
from pathlib import Path

from isaacsim import SimulationApp


app = SimulationApp({"headless": True, "renderer": "RaytracedLighting"})
status = 1
try:
    sys.path.insert(0, "/work/examples")
    import omni.usd
    import isaacsim.core.experimental.utils.stage as stage_utils
    from centimeter_yup_cell import build
    from isaac_web_exporter.export import run

    stage_utils.create_new_stage()
    stage = omni.usd.get_context().get_stage()
    build(stage, app, {"fps": 30, "duration_seconds": 2})
    for prim in stage.Traverse():
        for attr in prim.GetAttributes():
            samples = [(time, attr.Get(time)) for time in attr.GetTimeSamples()]
            for time, _ in samples: attr.ClearAtTime(time)
            for time, value in samples: attr.Set(value, time + 300)
    stage.SetTimeCodesPerSecond(30)
    stage.SetFramesPerSecond(30)
    stage.SetStartTimeCode(300)
    stage.SetEndTimeCode(360)
    source = Path("/work/runs/v1-offset-source.usda")
    stage.Export(str(source))
    success = run(Path("/work/runs/final-configs/offset-saved.json"), app=app)
    manifest = json.loads(Path(
        "/work/runs/v1-release-offset-saved/package/manifest.json").read_text()) if success else {}
    result = {"success": success, "sourceStart": stage.GetStartTimeCode(),
              "sourceEnd": stage.GetEndTimeCode(),
              "manifestStart": manifest.get("startTimeCode"),
              "manifestEnd": manifest.get("endTimeCode"),
              "duration": manifest.get("durationSeconds"),
              "sampleStart": manifest.get("clipSampleTimes", [[None]])[0][0],
              "sampleEnd": manifest.get("clipSampleTimes", [[None]])[0][-1]}
    print("OFFSET_CLIP_RESULT", json.dumps(result), flush=True)
    if not (success and result["sourceStart"] == result["manifestStart"] == 300 and
            result["sourceEnd"] == result["manifestEnd"] == 360 and
            result["duration"] == 2 and abs(result["sampleStart"]) < 0.001 and
            abs(result["sampleEnd"] - 2) < 0.001):
        raise RuntimeError(f"Offset clip normalization failed: {result}")
    status = 0
finally:
    app.close(exit_code=status)
