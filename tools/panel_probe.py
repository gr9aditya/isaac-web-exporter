"""Exercise the actual Kit panel in an isolated Isaac Sim process."""

import json
import sys
import time
from pathlib import Path

from isaacsim import SimulationApp

app = SimulationApp({"headless": True, "renderer": "RaytracedLighting"})
try:
    sys.path.insert(0, "/work/extensions/isaac.web.exporter")
    from isaac_web_exporter_panel import Extension

    panel = Extension()
    panel.on_startup("isaac.web.exporter")
    panel.source.model.set_value("/work/examples/sort_cell_workflow.py")
    panel.output.model.set_value("/work/runs/v1-panel-probe")
    panel.duration.model.set_value(30.0)
    panel.fps.model.set_value(30)
    panel._preflight_clicked()
    preflight = panel.status.text
    print("PANEL_PREFLIGHT", preflight, flush=True)
    if not preflight.startswith("Preflight passed"):
        raise RuntimeError(preflight)
    panel._start_clicked()
    print("PANEL_STARTED", panel._process.pid if panel._process else None, flush=True)
    started = time.monotonic()
    last_heartbeat = started
    while panel._process and panel._process.poll() is None and time.monotonic() - started < 180:
        app.update()
        if time.monotonic() - last_heartbeat > 10:
            print("PANEL_HEARTBEAT", round(time.monotonic() - started), panel.status.text, flush=True)
            last_heartbeat = time.monotonic()
    print("PANEL_AFTER_LOOP", panel._process.poll() if panel._process else None, flush=True)
    result = {
        "preflight": preflight,
        "status": panel.status.text,
        "progress": panel.progress.model.get_value_as_float(),
        "processReturnCode": panel._process.returncode if panel._process else None,
        "packageExists": Path("/work/runs/v1-panel-probe/package/index.html").is_file(),
        "zipExists": Path("/work/runs/v1-panel-probe/package.zip").is_file(),
    }
    print("PANEL_RESULT", json.dumps(result), flush=True)
    if not result["packageExists"] or not result["zipExists"]:
        raise RuntimeError(result)
    panel.on_shutdown()
finally:
    app.close()
