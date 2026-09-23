"""Archive only exporter source needed by the isolated Isaac test container."""

from pathlib import Path
import tarfile


root = Path(__file__).resolve().parents[1]
target = root / "runs" / "v1" / "remote-source.tar.gz"
target.parent.mkdir(parents=True, exist_ok=True)


def include(info):
    components = Path(info.name).parts
    if "__pycache__" in components or "node_modules" in components:
        return None
    if info.name.endswith((".pyc", ".pyo")):
        return None
    return info


with tarfile.open(target, "w:gz") as archive:
    for relative in ["src", "extensions", "examples", "tests", "pyproject.toml",
                     "toolchain.lock.json", "tools/isaac_batch.py", "tools/panel_probe.py",
                     "tools/panel_controls_probe.py",
                     "tools/panel_presets_probe.py",
                     "tools/loaded_stage_v1.py",
                     "tools/offset_clip_probe.py",
                     "tools/panel_visual_probe.py", "tools/isaac_reference_v1.py",
                     "tools/isaac_viewport_reference.py", "tools/isaac_render_diagnostic.py"]:
        archive.add(root / relative, arcname=relative, filter=include)
print(target, target.stat().st_size)
