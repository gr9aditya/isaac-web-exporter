"""Exercise panel presets, local preview and synthetic conversion cancellation."""

import asyncio
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

from isaacsim import SimulationApp


app = SimulationApp({"headless": True, "renderer": "RaytracedLighting"})
status = 1
try:
    sys.path.insert(0, "/work/extensions/isaac.web.exporter")
    import isaac_web_exporter_panel
    panel = isaac_web_exporter_panel.Extension()
    panel.on_startup("isaac.web.exporter")
    panel.source.model.set_value("/work/examples/falling_box.py")
    panel.output.model.set_value("/work/runs/v1-panel-preset-output")
    panel.duration.model.set_value(7.0)
    panel.quality.model.set_value("compact")
    panel._save_preset()
    saved = panel.status.text
    panel.duration.model.set_value(2.0)
    panel.quality.model.set_value("standard")
    panel._load_preset()
    preset = {"saved": saved, "loaded": panel.status.text,
              "duration": panel.duration.model.get_value_as_float(),
              "quality": panel.quality.model.get_value_as_string()}
    if preset["duration"] != 7 or preset["quality"] != "compact":
        raise RuntimeError(f"Preset roundtrip failed: {preset}")
    opened = []
    isaac_web_exporter_panel.webbrowser.open = opened.append
    panel._last_output = Path("/work/runs/v1-material-guided")
    panel._preview_clicked()
    if not opened or not opened[0].startswith("http://127.0.0.1:"):
        raise RuntimeError("Preview did not bind to localhost")
    with urllib.request.urlopen(opened[0], timeout=5) as response:
        preview = {"url": opened[0], "httpStatus": response.status,
                   "hasPlayer": b"Isaac Replay Studio" in response.read()}
    if preview["httpStatus"] != 200 or not preview["hasPlayer"]:
        raise RuntimeError(f"Preview failed: {preview}")

    conversion_dir = Path("/work/runs/v1-panel-synthetic-conversion")
    conversion_dir.mkdir()
    (conversion_dir / "progress.json").write_text(json.dumps({
        "phase": "conversion", "fraction": 0.7, "detail": "Converting recorded USD"}))
    panel._last_output = conversion_dir
    panel._process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    panel._task = asyncio.ensure_future(panel._watch_export())
    panel._cancel_clicked()
    panel._process.wait(timeout=10)
    conversion = {"returnCode": panel._process.returncode,
                  "cancelRequested": panel._cancel_requested,
                  "packageExists": (conversion_dir / "package").exists()}
    if conversion["returnCode"] == 0 or not conversion["cancelRequested"] or conversion["packageExists"]:
        raise RuntimeError(f"Synthetic conversion cancel failed: {conversion}")
    print("PANEL_PRESETS", json.dumps({"status": "PASS", "preset": preset,
                                        "preview": preview, "conversionCancel": conversion}), flush=True)
    panel.on_shutdown()
    status = 0
except Exception as error:
    import traceback
    traceback.print_exc()
    print("PANEL_PRESETS_ERROR", repr(error), flush=True)
finally:
    app.close(exit_code=status)
