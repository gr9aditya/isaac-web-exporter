"""Show the real Kit panel on a dedicated Xvfb display for screenshot QA."""

import json
import asyncio
import sys
import time

from isaacsim import SimulationApp

app = SimulationApp({"headless": False, "renderer": "RaytracedLighting"})
try:
    sys.path.insert(0, "/work/extensions/isaac.web.exporter")
    from isaac_web_exporter_panel import Extension

    panel = Extension()
    panel.on_startup("isaac.web.exporter")
    panel.source.model.set_value("/work/examples/sort_cell_workflow.py")
    panel.output.model.set_value("/work/runs/v1-panel-visual")
    manager = __import__("omni.kit.app", fromlist=["get_app"]).get_app().get_extension_manager()
    manager.set_extension_enabled_immediate("omni.kit.ui_test", True)
    import omni.kit.ui_test as ui_test
    for _ in range(5):
        app.update()
    buttons = ui_test.find_all("Isaac Replay Exporter//Frame/**/Button[*]")
    print("UI_TEST_BUTTONS", [item.path for item in buttons], flush=True)
    if len(buttons) != 6:
        raise RuntimeError(f"Expected six export panel buttons, found {len(buttons)}")
    # The first button in the panel's declared row is Preflight. ui_test's
    # wildcard selector prints identical query paths for distinct widgets.
    preflight = buttons[0]
    click = asyncio.ensure_future(preflight.click())
    while not click.done():
        app.update()
    click.result()
    result = {"status": panel.status.text, "preflightClicked": True,
              "buttonCount": len(buttons)}
    if not panel.status.text.startswith("Preflight passed"):
        raise RuntimeError(f"Clicked panel preflight failed: {result}")
    print("PANEL_VISUAL", json.dumps(result), flush=True)
    started = time.monotonic()
    while time.monotonic() - started < 20:
        app.update()
    panel.on_shutdown()
finally:
    app.close()
