"""Make a local compact comparison package from an existing validated package."""

import hashlib
import json
import os
import shutil
from pathlib import Path

from isaac_web_exporter.identity import animation_sample_times
from isaac_web_exporter.optimize import compact_animation_glb
from isaac_web_exporter.validate_package import check


source = Path("runs/v1/from-panel-package")
target = Path(os.environ.get("COMPACT_TARGET", "runs/v1/compact-preview"))
if target.exists():
    raise FileExistsError(target)
shutil.copytree(source, target)
glb = target / "scene.glb"
optimization = compact_animation_glb(glb)
manifest_path = target / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["assetSha256"] = hashlib.sha256(glb.read_bytes()).hexdigest()
manifest["clipSampleTimes"] = animation_sample_times(glb)
manifest["qualityPreset"] = "compact"
manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
report_path = target / "compatibility-report.json"
report = json.loads(report_path.read_text(encoding="utf-8"))
report["optimization"] = optimization
report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
validation = check(target)
print(json.dumps({"optimization": optimization, "validation": validation}, indent=2))
if validation["status"] != "success":
    raise SystemExit(1)
