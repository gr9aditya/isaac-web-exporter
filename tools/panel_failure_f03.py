"""Verify the panel reports a failed child without claiming a package is ready."""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

from isaacsim import SimulationApp


app = SimulationApp({"headless": True, "renderer": "MinimalRendering",
                     "limit_cpu_threads": 2})
status = 1
panel = None
try:
    sys.path.insert(0, "/work/extensions/isaac.web.exporter")
    from isaac_web_exporter_panel import Extension

    output = Path("/work/runs/v1-f03-panel-failed-child")
    output.mkdir(exist_ok=False)
    (output / "report.json").write_text(json.dumps({
        "status": "failed", "errors": ["Injected converter failure"]
    }), encoding="utf-8")
    panel = Extension()
    panel.on_startup("isaac.web.exporter")
    panel._last_output = output
    panel._process = subprocess.Popen([sys.executable, "-c", "import sys; sys.exit(7)"])
    panel._task = asyncio.ensure_future(panel._watch_export())
    deadline = time.monotonic() + 30
    while not panel._task.done() and time.monotonic() < deadline:
        app.update()
    result = {"processExit": panel._process.poll(), "panelStatus": panel.status.text,
              "packageExists": (output / "package").exists(),
              "zipExists": (output / "package.zip").exists()}
    if (result["processExit"] != 7 or
            result["panelStatus"] != "Export failed: Injected converter failure" or
            result["packageExists"] or result["zipExists"]):
        raise RuntimeError(result)
    print("F03_FAILURE_STATUS_DONE", json.dumps(result), flush=True)
    status = 0
finally:
    if panel:
        panel.on_shutdown()
    app.close(exit_code=status)
