"""Verify real Kit panel progress and capture/conversion cancellation on Xvfb.

The parent is an interactive Isaac SimulationApp using the isolated :97 X
display. All button actions use Kit ui_test, while app.update keeps the UI
event loop active as separate Isaac export children run.
"""

import asyncio
import json
import os
import sys
import time
import traceback
from pathlib import Path

from isaacsim import SimulationApp


app = SimulationApp({"headless": False, "renderer": "MinimalRendering", "width": 800, "height": 600,
                     "limit_cpu_threads": 2})
status = 1
panel = None
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
    if len(buttons) != 6:
        raise RuntimeError(f"Expected six panel buttons, found {len(buttons)}")

    def click(index):
        print("F03_CLICK_BEGIN", index, flush=True)
        action = asyncio.ensure_future(buttons[index].click())
        deadline = time.monotonic() + 15
        while not action.done() and time.monotonic() < deadline:
            app.update()
            if index == 4 and panel._cancel_requested:
                print("F03_CANCEL_CALLBACK", panel.status.text, flush=True)
                return
        if not action.done():
            raise TimeoutError(f"Panel button {index} did not respond")
        action.result()
        print("F03_CLICK_END", index, panel.status.text, flush=True)

    def wait_for_phase(phase, output, timeout=420):
        started = time.monotonic()
        last_log = started
        while time.monotonic() - started < timeout:
            app.update()
            now = time.monotonic()
            if now - last_log >= 8:
                print("F03_HEARTBEAT", phase, round(now - started, 1),
                      panel.status.text, panel.progress.model.get_value_as_float(),
                      panel._process.poll(), flush=True)
                last_log = now
            progress = output / "progress.json"
            if progress.is_file():
                try:
                    data = json.loads(progress.read_text(encoding="utf-8"))
                    if data.get("phase") == phase:
                        # Wait for the UI watcher to reflect the child progress.
                        if panel.progress.model.get_value_as_float() >= data.get("fraction", 0) - 0.01:
                            print("F03_LIVE_PHASE", phase, json.dumps(data),
                                  panel.status.text, flush=True)
                            return data
                except (OSError, ValueError):
                    pass
            if panel._process.poll() is not None:
                raise RuntimeError(f"Export exited before {phase}: {panel.status.text}")
        raise TimeoutError(f"No responsive {phase} progress within {timeout}s")

    def wait_for_cancel(output):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            app.update()
            if panel._process.poll() is not None and "cancelled" in panel.status.text.lower():
                break
        result = {"status": panel.status.text,
                  "returnCode": panel._process.poll(),
                  "packageExists": (output / "package").exists(),
                  "zipExists": (output / "package.zip").exists()}
        if (result["returnCode"] is None or result["returnCode"] == 0 or
                result["packageExists"] or result["zipExists"] or
                "cancelled" not in result["status"].lower()):
            raise RuntimeError(f"Cancelled export left false success: {result}")
        return result

    capture_out = Path("/work/runs/v1-f03-real-capture-cancel-j")
    conversion_out = Path("/work/runs/v1-f03-real-conversion-cancel-j")
    scenario = os.environ.get("F03_SCENARIO", "both")
    for output in (capture_out, conversion_out):
        if output.exists():
            raise FileExistsError(f"Refusing to reuse test output: {output}")

    capture_progress = capture_cancel = None
    if scenario != "conversion":
        panel.source.model.set_value("/work/examples/falling_box.py")
        panel.output.model.set_value(str(capture_out))
        panel.duration.model.set_value(30.0)
        panel.fps.model.set_value(60)
        click(0)
        if not panel.status.text.startswith("Preflight passed"):
            raise RuntimeError(f"Capture preflight: {panel.status.text}")
        click(3)
        print("F03_CAPTURE_STARTED", panel.status.text, flush=True)
        capture_progress = wait_for_phase("capture", capture_out)
        click(4)
        capture_cancel = wait_for_cancel(capture_out)
        print("F03_CAPTURE_CANCEL", json.dumps(capture_cancel), flush=True)

    # A new preflight click proves the same Kit UI still handles interaction.
    panel.source.model.set_value("/work/runs/v1-f03-conversion-stress-b.usda")
    panel.output.model.set_value(str(conversion_out))
    panel.duration.model.set_value(30.0)
    panel.fps.model.set_value(30)
    panel.quality.model.set_value("compact")
    click(0)
    if not panel.status.text.startswith("Preflight passed"):
        raise RuntimeError(f"Post-cancel preflight: {panel.status.text}")
    click(3)
    print("F03_CONVERSION_STARTED", panel.status.text, flush=True)
    conversion_progress = wait_for_phase("conversion", conversion_out)
    click(4)
    conversion_cancel = wait_for_cancel(conversion_out)
    print("F03_CONVERSION_CANCEL", json.dumps(conversion_cancel), flush=True)

    result = {"status": "PASS" if scenario == "both" else "PARTIAL_PASS_CONVERSION",
              "uiButtons": len(buttons),
              "captureProgress": capture_progress, "captureCancel": capture_cancel,
              "conversionProgress": conversion_progress,
              "conversionCancel": conversion_cancel,
              "visualProbe": "/work/runs/v1-f03-panel-live-b.png"}
    Path("/work/runs/v1-f03-interactive-report-j.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8")
    print("F03_INTERACTIVE_DONE", json.dumps(result), flush=True)
    status = 0
except BaseException as error:
    traceback.print_exc()
    print("F03_INTERACTIVE_ERROR", repr(error), flush=True)
finally:
    if panel:
        panel.on_shutdown()
    app.close(exit_code=status)
