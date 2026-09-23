"""Retry USD authoring from durable raw factory poses without rerunning Isaac."""

import json
import os
import sys
from pathlib import Path

os.environ["FACTORY_CAPTURE_OFFLINE"] = "1"
sys.path.insert(0, "/work/tools")
from factory_capture_entry import Capture
output = Path(os.environ.get("FACTORY_CAPTURE_OUTPUT", sys.argv[1] if len(sys.argv) > 1 else ""))
raw = json.loads((output / "raw-capture.json").read_text(encoding="utf-8"))
capture = Capture(output)
capture.ready = True
capture.frames = raw["frames"]
capture.paths = raw["paths"]
capture.tracks = raw["tracks"]
capture.items = raw["items"]
try:
    capture.finish({"metrics": raw["metrics"], "records": raw["records"]})
except BaseException:
    import traceback
    traceback.print_exc()
    os._exit(1)
os._exit(0)
