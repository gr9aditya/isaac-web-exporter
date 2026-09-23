"""Exercise the public in-process input using an already authored Isaac stage."""

from pathlib import Path
import sys

sys.path.insert(0, "/work/examples")
sys.path.insert(0, "/work/src")

from isaacsim import SimulationApp

app = SimulationApp({"headless": True, "renderer": "RaytracedLighting"})
status = 1
try:
    import omni.usd
    import isaacsim.core.experimental.utils.stage as stage_utils
    from falling_box import build
    from isaac_web_exporter.export import run

    stage_utils.create_new_stage()
    stage = omni.usd.get_context().get_stage()
    build(stage, app, {})
    status = 0 if run(Path("/work/tests/v0_loaded_stage.json"), app=app, stage=stage) else 1
finally:
    app.close(exit_code=status)
