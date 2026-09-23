"""Mutation tests against a real built v1 package (given as an argument)."""

import argparse
import hashlib
import json
import shutil
import struct
import tempfile
from pathlib import Path

from isaac_web_exporter.identity import read_glb
from isaac_web_exporter.validate_package import ResourceParser, check


parser = argparse.ArgumentParser()
parser.add_argument("package", type=Path)
args = parser.parse_args()
source = args.package.resolve()
results = []


def load_json(package, name):
    return json.loads((package / name).read_text(encoding="utf-8"))


def save_json(package, name, data):
    (package / name).write_text(json.dumps(data, indent=2), encoding="utf-8")


def clean_stale_assets(package):
    html = ResourceParser()
    html.feed((package / "index.html").read_text(encoding="utf-8"))
    referenced = {name.lstrip("./") for name in html.references}
    for candidate in (package / "assets").glob("index-*.*"):
        if candidate.relative_to(package).as_posix() not in referenced:
            candidate.unlink()


def mutate_glb(package, change):
    path = package / "scene.glb"
    gltf, tail = read_glb(path)
    change(gltf)
    encoded = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    encoded += b" " * (-len(encoded) % 4)
    rebuilt = b"glTF" + struct.pack("<II", 2, 20 + len(encoded) + len(tail))
    rebuilt += struct.pack("<I4s", len(encoded), b"JSON") + encoded + tail
    path.write_bytes(rebuilt)
    manifest = load_json(package, "manifest.json")
    manifest["assetSha256"] = hashlib.sha256(rebuilt).hexdigest()
    save_json(package, "manifest.json", manifest)


cases = {
    "missing_scene": lambda package: (package / "scene.glb").unlink(),
    "truncated_scene": lambda package: (package / "scene.glb").write_bytes(b"glTF"),
    "tampered_scene": lambda package: (package / "scene.glb").write_bytes(
        (package / "scene.glb").read_bytes()[:-1] + b"X"),
    "invalid_manifest_schema": lambda package: (lambda data: (
        data.__setitem__("schemaVersion", "v99"), save_json(package, "manifest.json", data)))(
            load_json(package, "manifest.json")),
    "invalid_identity": lambda package: (lambda data: (
        data["objects"][0]["nodeIndices"].__setitem__(0, 99999),
        save_json(package, "scene-map.json", data)))(load_json(package, "scene-map.json")),
    "unknown_tour_object": lambda package: (lambda data: (
        data["chapters"][0].__setitem__("objectId", "/World/Absent"),
        save_json(package, "experience.json", data)))(load_json(package, "experience.json")),
    "invalid_tour_time": lambda package: (lambda data: (
        data["chapters"][0].__setitem__("startSeconds", 99999),
        save_json(package, "experience.json", data)))(load_json(package, "experience.json")),
    "escaped_scene_path": lambda package: (lambda data: (
        data.__setitem__("asset", "../scene.glb"), save_json(package, "manifest.json", data)))(
            load_json(package, "manifest.json")),
    "external_html_resource": lambda package: (package / "index.html").write_text(
        (package / "index.html").read_text(encoding="utf-8").replace(
            "</head>", '<script src="https://example.invalid/remote.js"></script></head>'), encoding="utf-8"),
    "corrupt_manifest_json": lambda package: (package / "manifest.json").write_text(
        "{ invalid", encoding="utf-8"),
    "external_glb_texture": lambda package: mutate_glb(package, lambda gltf: gltf.setdefault(
        "images", []).append({"uri": "https://example.invalid/texture.png"})),
    "invalid_channel": lambda package: mutate_glb(package, lambda gltf: gltf["animations"][0][
        "channels"][0]["target"].__setitem__("node", 99999)),
    "missing_moving_channel": lambda package: mutate_glb(package, lambda gltf: [
        animation.__setitem__("channels", [channel for channel in animation["channels"]
            if gltf["nodes"][channel["target"]["node"]].get("extras", {}).get(
                "isaacObjectId") != "/World/Products/PartA"])
        for animation in gltf["animations"]]),
    "invalid_manifest_type": lambda package: (lambda data: (
        data.__setitem__("fps", "thirty"), save_json(package, "manifest.json", data)))(
            load_json(package, "manifest.json")),
    "mutated_schema_contract": lambda package: (package / "schemas" /
        "manifest.v1.schema.json").write_text("{}", encoding="utf-8"),
    "invalid_camera_transition": lambda package: (lambda data: (
        data["chapters"][0].__setitem__("transitionSeconds", -2),
        save_json(package, "experience.json", data)))(load_json(package, "experience.json")),
    "missing_customization_file": lambda package: (package / "customization" /
        "examples" / "focused-tour.js").unlink(),
    "corrupt_compatibility_report": lambda package: (package /
        "compatibility-report.json").write_text("[]", encoding="utf-8"),
}

with tempfile.TemporaryDirectory(prefix="isaac-negative-") as temporary:
    baseline = Path(temporary) / "baseline"
    shutil.copytree(source, baseline)
    clean_stale_assets(baseline)
    normal = check(baseline)
    if normal["status"] != "success":
        raise RuntimeError(f"Baseline package is invalid: {normal}")
    for name, mutate in cases.items():
        target = Path(temporary) / name
        shutil.copytree(baseline, target)
        mutate(target)
        checked = check(target)
        results.append({"case": name, "status": checked["status"],
                        "errors": checked["errors"]})
        if checked["status"] != "failed" or not checked["errors"]:
            raise RuntimeError(f"Mutation was not rejected: {name}: {checked}")

output = Path("runs/v1/negative-packages.json")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps({"baseline": str(source), "cases": results}, indent=2), encoding="utf-8")
print(json.dumps({"status": "PASS", "cases": len(results)}))
