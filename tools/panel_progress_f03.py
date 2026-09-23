"""Exercise the five-button Kit panel and complete an isolated USD export.

Run in an owned Isaac Sim 6.1 container with a visible X display. The exported
package and JSON report are written under /work/runs, never into source assets.
"""

import asyncio
import json
import os
import sys
import time
import traceback
import zipfile
from pathlib import Path

from isaacsim import SimulationApp


app = SimulationApp({"headless": False, "renderer": "MinimalRendering",
                     "limit_cpu_threads": 2})
panel = None
status = 1
try:
    import omni.kit.app

    sys.path.insert(0, "/work/extensions/isaac.web.exporter")
    from isaac_web_exporter_panel import Extension

    manager = omni.kit.app.get_app().get_extension_manager()
    manager.set_extension_enabled_immediate("omni.kit.ui_test", True)
    import omni.kit.ui_test as ui_test

    panel = Extension()
    panel.on_startup("isaac.web.exporter")
    for _ in range(8):
        app.update()
    buttons = ui_test.find_all("Isaac Replay Exporter//Frame/**/Button[*]")
    if len(buttons) != 5:
        raise RuntimeError(f"Expected five panel buttons without Cancel, found {len(buttons)}")

    def click(index):
        current = ui_test.find_all("Isaac Replay Exporter//Frame/**/Button[*]")
        if len(current) != 5:
            raise RuntimeError(f"Panel button count changed: {len(current)}")
        print("F03_CLICK_BEGIN", index, flush=True)
        action = asyncio.ensure_future(current[index].click())
        deadline = time.monotonic() + 20
        while not action.done() and time.monotonic() < deadline:
            app.update()
        if not action.done():
            raise TimeoutError(f"Panel button {index} did not respond")
        action.result()
        print("F03_CLICK_END", index, panel.status.text, flush=True)

    output = Path(os.environ.get("F03_OUTPUT", "/work/runs/v1-f03-panel-progress-1"))
    if output.exists():
        raise FileExistsError(f"Refusing to reuse output: {output}")
    panel.source.model.set_value("/work/runs/v1-sort-cell-guided/recorded_scene.usda")
    panel.output.model.set_value(str(output))
    panel.duration.model.set_value(30.0)
    panel.fps.model.set_value(30)
    panel.quality.model.set_value("compact")
    click(0)
    if not panel.status.text.startswith("Preflight passed"):
        raise RuntimeError(f"Preflight failed: {panel.status.text}")
    click(3)
    print("F03_EXPORT_STARTED", panel.status.text, flush=True)

    started = time.monotonic()
    last_log = started
    observed = []
    while time.monotonic() - started < 240:
        app.update()
        now = time.monotonic()
        if now - last_log >= 8:
            state = {"elapsed": round(now - started, 1), "status": panel.status.text,
                     "progress": panel.progress.model.get_value_as_float(),
                     "returnCode": panel._process.poll()}
            observed.append(state)
            print("F03_PANEL_PROGRESS", json.dumps(state), flush=True)
            last_log = now
        if panel._process.poll() is not None and panel.status.text.startswith("Ready:"):
            break

    from isaac_web_exporter.validate_package import check

    validation = check(output / "package")
    child_report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    result = {"status": "PASS", "uiButtons": len(buttons),
              "panelStatus": panel.status.text,
              "progress": panel.progress.model.get_value_as_float(),
              "returnCode": panel._process.poll(),
              "childReportStatus": child_report.get("status"),
              "validationStatus": validation.get("status"),
              "packageExists": (output / "package" / "index.html").is_file(),
              "zipExists": zipfile.is_zipfile(output / "package.zip"),
              "observed": observed}
    if (result["childReportStatus"] != "success" or
            result["validationStatus"] != "success" or
            not result["panelStatus"].startswith("Ready:")
            or result["progress"] != 1.0 or not result["packageExists"]
            or not result["zipExists"]):
        result["status"] = "FAIL"
        raise RuntimeError(f"Panel export did not finish cleanly: {result}")
    panel.output.model.set_value(str(output) + "-next")
    click(0)
    result["postExportPreflightClick"] = panel.status.text
    if not result["postExportPreflightClick"].startswith("Preflight passed"):
        raise RuntimeError(f"Panel unusable after export: {result}")
    report = Path("/work/runs/v1-f03-panel-progress-report.json")
    report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("F03_PANEL_DONE", json.dumps(result), flush=True)
    status = 0
except BaseException as error:
    traceback.print_exc()
    print("F03_PANEL_ERROR", repr(error), flush=True)
finally:
    if panel:
        panel.on_shutdown()
    app.close(exit_code=status)
