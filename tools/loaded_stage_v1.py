"""Verify caller-owned stage/app survival after successful and failed exports."""

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
    from sort_cell_workflow import build
    from isaac_web_exporter.export import run

    stage_utils.create_new_stage()
    stage = omni.usd.get_context().get_stage()
    build(stage, app, {"fps": 30, "duration_seconds": 30})
    before = stage.GetRootLayer().ExportToString()
    successful = run(Path("/work/runs/final-configs/loaded-stage.json"), app=app, stage=stage)
    after_success = stage.GetRootLayer().ExportToString()
    app.update()
    failed = run(Path("/work/runs/final-configs/loaded-stage-failure.json"),
                 app=app, stage=stage)
    after_failure = stage.GetRootLayer().ExportToString()
    app.update()
    result = {
        "successExport": successful,
        "failedExport": failed,
        "sourceUnchangedAfterSuccess": before == after_success,
        "sourceUnchangedAfterFailure": before == after_failure,
        "callerAppUsableAfterBoth": app.is_running(),
        "packageExists": Path("/work/runs/v1-release-loaded/package/index.html").is_file(),
        "failedPackageAbsent": not Path("/work/runs/v1-loaded-failure/package").exists(),
    }
    print("LOADED_STAGE_V1", json.dumps(result), flush=True)
    if not all((result["successExport"], not result["failedExport"],
                result["sourceUnchangedAfterSuccess"],
                result["sourceUnchangedAfterFailure"],
                result["callerAppUsableAfterBoth"], result["packageExists"],
                result["failedPackageAbsent"])):
        raise RuntimeError(f"Caller stage/app preservation failed: {result}")
    status = 0
finally:
    app.close(exit_code=status)
