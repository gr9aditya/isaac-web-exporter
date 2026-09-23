"""Offline validation of a generated static playback package."""

import argparse
import hashlib
import json
import math
import struct
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

try:
    from isaac_web_exporter.experience import validate_experience
    from isaac_web_exporter.identity import animation_sample_times
    from isaac_web_exporter.schema_check import validate as validate_schema
except ModuleNotFoundError:
    # Permit the README's direct-script command before installation.
    from experience import validate_experience
    from identity import animation_sample_times
    from schema_check import validate as validate_schema


class ResourceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "script" and values.get("src"):
            self.references.append(values["src"])
        if tag == "link" and values.get("href") and values.get("rel") == "stylesheet":
            self.references.append(values["href"])


def check(package):
    """Return a structured result even for broken JSON or missing inputs."""
    try:
        return _check(package)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError,
            struct.error) as error:
        return {"status": "failed", "errors": [f"Invalid package: {error}"]}


def _check(package):
    package = Path(package).resolve()
    errors = []
    required = ("index.html", "manifest.json", "scene-map.json", "LLM-HANDOFF.md",
                "compatibility-report.json",
                "README.txt", "scene.glb", "THIRD_PARTY_LICENSES/three-MIT.txt")
    for relative in required:
        if not (package / relative).is_file():
            errors.append(f"Missing package file: {relative}")
    if errors:
        return {"status": "failed", "errors": errors}

    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    scene_map = json.loads((package / "scene-map.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(scene_map, dict):
        raise ValueError("Manifest and scene-map must be JSON objects")
    version = manifest.get("schemaVersion")
    if version not in ("alpha-0.1", "v1.0"):
        errors.append(f"Unsupported manifest schemaVersion: {version}")
    if scene_map.get("schemaVersion") != version:
        errors.append("Scene-map schemaVersion differs from manifest")
    for key in ("durationSeconds", "fps", "metersPerUnit"):
        value = manifest.get(key)
        if (not isinstance(value, (int, float)) or not math.isfinite(value)
                or value < 0 or (key != "durationSeconds" and value == 0)):
            errors.append(f"Manifest {key} must be a finite positive number")
    if version == "v1.0":
        for relative in ("customization/README.md",
                         "customization/examples/theme-captions.js",
                         "customization/examples/focused-tour.js",
                         "customization/examples/object-info-panel.js"):
            if not (package / relative).is_file():
                errors.append(f"Missing customization kit file: {relative}")
        for key in ("sourceUpAxis", "viewerUpAxis", "clipSampleTimes", "source"):
            if key not in manifest:
                errors.append(f"Manifest missing {key}")
        if manifest.get("sourceUpAxis") not in ("Y", "Z") or manifest.get("viewerUpAxis") != "Y":
            errors.append("Manifest axis convention is unsupported")
        if not isinstance(manifest.get("clipSampleTimes"), list):
            errors.append("Manifest clipSampleTimes must be an array")
        if not isinstance(scene_map.get("objects"), list):
            errors.append("Scene-map objects must be an array")
        for name in ("manifest", "scene-map", "compatibility-report", "experience"):
            schema = package / "schemas" / f"{name}.v1.schema.json"
            if not schema.is_file():
                errors.append(f"Missing package schema: {schema.name}")
            else:
                canonical = Path(__file__).resolve().parent / "schemas" / schema.name
                if schema.read_bytes() != canonical.read_bytes():
                    errors.append(f"Package schema differs from exporter contract: {schema.name}")
        if not any(error.startswith("Missing package schema") for error in errors):
            for name, data in (("manifest", manifest), ("scene-map", scene_map)):
                definition = json.loads((Path(__file__).resolve().parent / "schemas" /
                                         f"{name}.v1.schema.json").read_text(encoding="utf-8"))
                errors.extend(f"{name} {issue}" for issue in validate_schema(data, definition))
        if not manifest.get("experience"):
            errors.append("Manifest missing experience path")
    asset_name = manifest.get("asset")
    if not isinstance(asset_name, str) or not asset_name:
        errors.append("Manifest asset must be a local path")
        return {"status": "failed", "errors": errors}
    asset_path = (package / asset_name).resolve()
    if not asset_path.is_relative_to(package) or not asset_path.is_file():
        errors.append("Manifest asset path is missing or outside the package")
        return {"status": "failed", "errors": errors}
    glb = asset_path.read_bytes()
    if len(glb) < 20 or glb[:4] != b"glTF" or len(glb) != struct.unpack_from("<I", glb, 8)[0]:
        errors.append("Invalid GLB header or length")
        gltf = {}
    else:
        json_length, kind = struct.unpack_from("<I4s", glb, 12)
        if kind != b"JSON":
            errors.append("Missing GLB JSON chunk")
            gltf = {}
        else:
            gltf = json.loads(glb[20:20 + json_length])
    digest = hashlib.sha256(glb).hexdigest()
    if digest != manifest.get("assetSha256"):
        errors.append("GLB SHA-256 differs from manifest")
    if manifest.get("mode") not in ("recorded-playback", "static-scene"):
        errors.append("Unsupported playback mode")
    if not gltf.get("meshes"):
        errors.append("GLB lacks meshes")
    if manifest.get("mode") == "recorded-playback" and not gltf.get("animations"):
        errors.append("Recorded package lacks animation")
    if manifest.get("mode") == "static-scene" and gltf.get("animations"):
        errors.append("Static package unexpectedly has animation")
    external = [item["uri"] for group in ("buffers", "images")
                for item in gltf.get(group, [])
                if item.get("uri") and not item["uri"].startswith("data:")]
    if external:
        errors.append(f"GLB has external asset URIs: {external}")
    nodes = gltf.get("nodes", [])
    names = {node.get("name") for node in nodes}
    for animation in gltf.get("animations", []):
        for channel in animation.get("channels", []):
            index = channel.get("target", {}).get("node")
            if type(index) is not int or not 0 <= index < len(nodes):
                errors.append(f"Animation channel targets invalid node {index}")
    objects = scene_map.get("objects", [])
    if not isinstance(objects, list):
        errors.append("Scene-map objects must be an array")
        objects = []
    object_ids = [item.get("id") for item in objects if isinstance(item, dict)]
    if len(object_ids) != len(set(object_ids)) or len(object_ids) != len(objects):
        errors.append("Scene-map object IDs must be unique objects")
    for required_id in manifest.get("capturedRigidBodies", []):
        if required_id not in object_ids:
            errors.append(f"Required captured rigid body absent from catalog: {required_id}")
    if version == "v1.0":
        for item in objects:
            if not isinstance(item, dict):
                continue
            parent = item.get("parentId")
            if parent is not None and parent not in object_ids and parent != "/World":
                errors.append(f"Scene-map parent ID absent: {item.get('id')} -> {parent}")
            if not isinstance(item.get("sourcePrimPath"), str) or not item["sourcePrimPath"].startswith("/"):
                errors.append(f"Scene-map object has invalid sourcePrimPath: {item.get('id')}")
    for item in objects:
        if not isinstance(item, dict):
            continue
        if scene_map.get("schemaVersion") == "v1.0":
            indices = item.get("nodeIndices", [])
            if not isinstance(item.get("id"), str) or not item["id"]:
                errors.append("Scene-map object has an invalid ID")
            if not isinstance(item.get("displayName"), str):
                errors.append(f"Scene-map object missing displayName: {item.get('id')}")
            if not isinstance(indices, list) or not indices:
                errors.append(f"Scene-map object has no nodes: {item.get('id')}")
                indices = []
            for index in indices:
                if type(index) is not int or not 0 <= index < len(nodes):
                    errors.append(f"Scene-map node index invalid: {item.get('id')} {index}")
                elif nodes[index].get("extras", {}).get("isaacObjectId") != item.get("id"):
                    errors.append(f"Scene-map identity differs from GLB: {item.get('id')} {index}")
        elif item.get("node") not in names:
            errors.append(f"Scene-map node absent from GLB: {item.get('node')}")
    if version == "v1.0":
        times = manifest.get("clipSampleTimes", [])
        if isinstance(times, list):
            if len(times) != len(gltf.get("animations", [])):
                errors.append("Manifest clip count differs from GLB")
            else:
                actual_times = animation_sample_times(asset_path)
                for index, (declared, actual) in enumerate(zip(times, actual_times)):
                    if (not isinstance(declared, list) or any(
                            not isinstance(value, (int, float)) or not math.isfinite(value)
                            or value < 0
                            for value in declared)):
                        errors.append(f"Clip {index} sample times must be finite numbers")
                    elif declared != sorted(set(declared)):
                        errors.append(f"Clip {index} sample times must be sorted and unique")
                    elif len(declared) != len(actual) or any(
                            abs(a - b) > 0.001 for a, b in zip(declared, actual)):
                        errors.append(f"Clip {index} sample times differ from GLB")
        if gltf.get("animations") and isinstance(times, list) and abs(
                max((max(group, default=0) for group in times if isinstance(group, list)), default=0)
                - manifest.get("durationSeconds", 0)) > 0.001:
            errors.append("Manifest duration differs from GLB clips")
        animation_info = scene_map.get("animation", {})
        if not isinstance(animation_info, dict) or animation_info.get("durationSeconds") != manifest.get("durationSeconds"):
            errors.append("Scene-map animation duration differs from manifest")

    parser = ResourceParser()
    parser.feed((package / "index.html").read_text(encoding="utf-8"))
    for ref in parser.references:
        parsed = urlparse(ref)
        if parsed.scheme or ref.startswith("//") or ref.startswith("/"):
            errors.append(f"HTML uses non-relative resource: {ref}")
        elif not (package / parsed.path).resolve().is_relative_to(package):
            errors.append(f"HTML resource escapes package: {ref}")
        elif not (package / parsed.path).is_file():
            errors.append(f"HTML resource missing: {ref}")
    if version == "v1.0":
        referenced_assets = {urlparse(ref).path.lstrip("./") for ref in parser.references}
        for stale in (package / "assets").glob("index-*.*"):
            if stale.relative_to(package).as_posix() not in referenced_assets:
                errors.append(f"Unreferenced generated player asset: {stale.name}")
    report = json.loads((package / "compatibility-report.json").read_text(encoding="utf-8"))
    if version == "v1.0":
        definition = json.loads((Path(__file__).resolve().parent / "schemas" /
                                 "compatibility-report.v1.schema.json").read_text(encoding="utf-8"))
        errors.extend(f"compatibility-report {issue}" for issue in validate_schema(report, definition))
    if version == "v1.0" and report.get("schemaVersion") != "v1.0":
        errors.append("Compatibility report schemaVersion differs from manifest")
    if report.get("status") != "success":
        errors.append("Compatibility report is not successful")
    if version == "v1.0":
        channels = {
            (channel.get("target", {}).get("node"), channel.get("target", {}).get("path"))
            for animation in gltf.get("animations", [])
            for channel in animation.get("channels", [])
        }
        by_id = {item.get("id"): item for item in objects if isinstance(item, dict)}
        for source_path in report.get("authored_moving_paths", []):
            indices = by_id.get(source_path, {}).get("nodeIndices", [])
            if not any(index == node for index in indices for node, _ in channels):
                errors.append(f"Required authored motion missing from GLB: {source_path}")
        for source_path, capture in report.get("capture", {}).items():
            if not isinstance(capture, dict) or capture.get("unique_positions", 0) < 2:
                continue
            indices = by_id.get(source_path, {}).get("nodeIndices", [])
            if not any((index, "translation") in channels for index in indices):
                errors.append(f"Required rigid translation missing from GLB: {source_path}")
    if manifest.get("experience"):
        experience_path = (package / manifest["experience"]).resolve()
        if not experience_path.is_relative_to(package) or not experience_path.is_file():
            errors.append("Experience file is missing or outside the package")
        else:
            try:
                experience = json.loads(experience_path.read_text(encoding="utf-8"))
                if version == "v1.0":
                    definition = json.loads((Path(__file__).resolve().parent / "schemas" /
                                             "experience.v1.schema.json").read_text(encoding="utf-8"))
                    errors.extend(f"experience {issue}" for issue in validate_schema(experience, definition))
                validate_experience(
                    experience, [item.get("id") for item in scene_map.get("objects", [])],
                    [samples[-1] if samples else 0
                     for samples in manifest.get("clipSampleTimes", [])],
                )
            except (ValueError, KeyError, TypeError) as error:
                errors.append(f"Invalid experience: {error}")
    return {
        "status": "failed" if errors else "success", "errors": errors,
        "glbBytes": len(glb), "glbSha256": digest,
        "meshes": len(gltf.get("meshes", [])),
        "animations": len(gltf.get("animations", [])),
        "htmlResources": parser.references,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    result = check(args.package)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    main()
