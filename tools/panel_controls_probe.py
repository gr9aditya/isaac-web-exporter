"""Exercise Kit panel cancellation, presets and local preview in isolation."""

import asyncio
import json
import subprocess
import sys
import time
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
    print("PANEL_CONTROL_STARTUP", flush=True)
    panel.source.model.set_value("/work/examples/falling_box.py")
    panel.output.model.set_value("/work/runs/v1-panel-cancel-capture-2")
    panel.duration.model.set_value(120.0)
    panel.fps.model.set_value(60)
    panel._preflight_clicked()
    print("PANEL_CONTROL_PREFLIGHT", panel.status.text, flush=True)
    if not panel.status.text.startswith("Preflight passed"):
        raise RuntimeError(panel.status.text)
    panel._start_clicked()
    print("PANEL_CONTROL_CHILD", panel.status.text, flush=True)
    started = time.monotonic()
    saw_capture = False
    while time.monotonic() - started < 90:
        time.sleep(0.05)
        progress = Path("/work/runs/v1-panel-cancel-capture-2/progress.json")
        if progress.is_file():
            try:
                detail = json.loads(progress.read_text())
                if detail.get("phase") == "capture" and detail.get("fraction", 0) >= 0.05:
                    saw_capture = True
                    panel._cancel_clicked()
                    break
            except (OSError, ValueError):
                pass
        if panel._process.poll() is not None:
            break
    if not saw_capture:
        raise RuntimeError("Could not cancel during real capture phase")
    panel._process.wait(timeout=20)
    for _ in range(5): app.update()
    capture = {"phaseReached": saw_capture, "returnCode": panel._process.returncode,
               "status": panel.status.text,
               "packageExists": Path("/work/runs/v1-panel-cancel-capture-2/package").exists()}
    if capture["packageExists"] or capture["returnCode"] == 0:
        raise RuntimeError(f"Capture cancellation left false success: {capture}")

    # Hold a child at conversion progress to test the panel's cancellation
    # mechanics in that phase. Real conversion-timeout failure is separately
    # exercised by the negative Isaac batch.
    conversion_dir = Path("/work/runs/v1-panel-cancel-conversion-2")
    conversion_dir.mkdir()
    (conversion_dir / "progress.json").write_text(json.dumps({
        "phase": "conversion", "fraction": 0.7, "detail": "Converting recorded USD"}))
    panel._cancel_requested = False
    panel._last_output = conversion_dir
    panel._process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    panel._task = asyncio.ensure_future(panel._watch_export())
    for _ in range(3): app.update()
    panel._cancel_clicked()
    panel._process.wait(timeout=15)
    for _ in range(5): app.update()
    conversion = {"returnCode": panel._process.returncode, "status": panel.status.text,
                  "packageExists": (conversion_dir / "package").exists()}
    if conversion["packageExists"] or conversion["returnCode"] == 0:
        raise RuntimeError(f"Conversion-phase cancellation left false success: {conversion}")

    panel.output.model.set_value("/work/runs/v1-new-preset-output")
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
        raise RuntimeError(f"Preview did not serve package: {preview}")
    print("PANEL_CONTROLS", json.dumps({
        "status": "PASS", "captureCancel": capture,
        "conversionCancel": conversion, "preset": preset, "preview": preview,
    }), flush=True)
    panel.on_shutdown()
    status = 0
except Exception as error:
    import traceback
    traceback.print_exc()
    print("PANEL_CONTROL_ERROR", repr(error), flush=True)
    if 'panel' in locals():
        panel.on_shutdown()
finally:
    app.close(exit_code=status)
