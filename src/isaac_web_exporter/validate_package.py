"""Offline validation of a generated static playback package."""

import argparse
import hashlib
import json
import struct
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


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

    manifest = json.loads((package / "manifest.json").read_text())
    scene_map = json.loads((package / "scene-map.json").read_text())
    asset_path = (package / manifest["asset"]).resolve()
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
    if manifest.get("mode") != "recorded-playback":
        errors.append("Unsupported playback mode")
    if not gltf.get("meshes") or not gltf.get("animations"):
        errors.append("GLB lacks meshes or animation")
    external = [item["uri"] for group in ("buffers", "images")
                for item in gltf.get(group, [])
                if item.get("uri") and not item["uri"].startswith("data:")]
    if external:
        errors.append(f"GLB has external asset URIs: {external}")
    names = {node.get("name") for node in gltf.get("nodes", [])}
    for item in scene_map.get("objects", []):
        if item["node"] not in names:
            errors.append(f"Scene-map node absent from GLB: {item['node']}")

    parser = ResourceParser()
    parser.feed((package / "index.html").read_text())
    for ref in parser.references:
        parsed = urlparse(ref)
        if parsed.scheme or ref.startswith("//") or ref.startswith("/"):
            errors.append(f"HTML uses non-relative resource: {ref}")
        elif not (package / parsed.path).is_file():
            errors.append(f"HTML resource missing: {ref}")
    report = json.loads((package / "compatibility-report.json").read_text())
    if report.get("status") != "success":
        errors.append("Compatibility report is not successful")
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
