"""Exercise overwrite and missing-converter failure paths in real Isaac."""

import builtins
import hashlib
import json
from pathlib import Path

from isaacsim import SimulationApp


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


app = SimulationApp({"headless": True, "renderer": "RaytracedLighting"})
status = 1
try:
    from isaac_web_exporter.export import run

    existing = Path("/work/runs/v1-release-box/package/scene.glb")
    before = digest(existing)
    existing_config = Path("/work/runs/final-configs/release-box.json")
    overwrite_error = None
    try:
        run(existing_config, app=app)
    except FileExistsError as error:
        overwrite_error = str(error)
    after = digest(existing)

    config_path = Path("/work/runs/final-configs/converter-unavailable.json")
    original_import = builtins.__import__
    def unavailable(name, *args, **kwargs):
        if name == "omni.kit.asset_converter":
            raise ImportError("Simulated unavailable Isaac Asset Converter")
        return original_import(name, *args, **kwargs)

    builtins.__import__ = unavailable
    try:
        converted = run(config_path, app=app)
    finally:
        builtins.__import__ = original_import
    output = Path("/work/runs/v1-negative-converter-unavailable")
    report = json.loads((output / "report.json").read_text())
    result = {
        "overwriteError": overwrite_error,
        "priorPackageUnchanged": before == after,
        "converterRunSucceeded": converted,
        "converterError": report.get("errors", []),
        "falseSuccessPackage": (output / "package").exists(),
        "callerAppUsable": app.is_running(),
    }
    print("EXPORT_FAILURE_PROBE", json.dumps(result), flush=True)
    if not (overwrite_error and before == after and not converted and
            "Simulated unavailable Isaac Asset Converter" in str(report.get("errors")) and
            not result["falseSuccessPackage"] and result["callerAppUsable"]):
        raise RuntimeError(result)
    status = 0
finally:
    app.close(exit_code=status)
