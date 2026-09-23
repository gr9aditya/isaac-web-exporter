"""Build a reproducible local v1 wheel from a fresh source staging tree.

This avoids setuptools retaining hashed frontend files from an earlier build.
The staging tree is temporary and never includes ignored run artifacts.
"""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="isaac-web-exporter-build-") as temporary:
        stage = Path(temporary)
        ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info",
                                         "node_modules", "dist", "build", "player_dist")
        shutil.copytree(root / "src", stage / "src", ignore=ignore)
        shutil.copytree(root / "web" / "player", stage / "web" / "player", ignore=ignore)
        (stage / "tools").mkdir()
        shutil.copy2(root / "tools" / "build_player.py", stage / "tools" / "build_player.py")
        for name in ("pyproject.toml", "README.md"):
            shutil.copy2(root / name, stage / name)
        subprocess.run([sys.executable, "tools/build_player.py"], cwd=stage, check=True)
        subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-build-isolation",
                        "--no-deps", ".", "-w", "out"], cwd=stage, check=True)
        wheels = list((stage / "out").glob("isaac_web_exporter-1.0.0*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"Expected one v1 wheel, found {wheels}")
        with ZipFile(wheels[0]) as archive:
            names = archive.namelist()
            assets = [name for name in names if "/player_dist/assets/index-" in name]
            if len(assets) != 2 or not any(name.endswith(".js") for name in assets) or not any(
                    name.endswith(".css") for name in assets):
                raise RuntimeError(f"Wheel has stale or missing frontend assets: {assets}")
            required = ("schema_check.py", "schemas/manifest.v1.schema.json",
                        "package_files/LLM-HANDOFF.md",
                        "package_files/customization/examples/focused-tour.js")
            if any(not any(name.endswith(item) for name in names) for item in required):
                raise RuntimeError("Wheel is missing a required v1 source or package file")
        destination = root / "dist" / wheels[0].name
        destination.parent.mkdir(exist_ok=True)
        shutil.copy2(wheels[0], destination)
    result = {"wheel": str(destination),
              "bytes": destination.stat().st_size,
              "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
              "frontendAssets": assets}
    evidence = root / "runs" / "v1" / "release-build.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
