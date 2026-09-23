"""Derive a two-clip browser fixture from the real Isaac sorting package."""

import copy
import hashlib
import json
import shutil
import struct
from pathlib import Path

from isaac_web_exporter.identity import read_glb
from isaac_web_exporter.validate_package import check


source = Path("runs/v1/v1-final-guided/package")
target = Path("runs/v1/two-clips")
if target.exists():
    raise FileExistsError(target)
shutil.copytree(source, target)
glb = target / "scene.glb"
gltf, tail = read_glb(glb)
alternate = copy.deepcopy(gltf["animations"][0])
alternate["name"] = "Alternate recording"
gltf["animations"].append(alternate)
encoded = json.dumps(gltf, separators=(",", ":")).encode()
encoded += b" " * (-len(encoded) % 4)
rebuilt = b"glTF" + struct.pack("<II", 2, 20 + len(encoded) + len(tail))
rebuilt += struct.pack("<I4s", len(encoded), b"JSON") + encoded + tail
glb.write_bytes(rebuilt)
manifest_path = target / "manifest.json"
manifest = json.loads(manifest_path.read_text())
manifest["assetSha256"] = hashlib.sha256(rebuilt).hexdigest()
manifest["clipSampleTimes"].append(copy.deepcopy(manifest["clipSampleTimes"][0]))
manifest_path.write_text(json.dumps(manifest, indent=2))
validated = check(target)
print(json.dumps(validated, indent=2))
if validated["status"] != "success":
    raise RuntimeError("Synthetic second clip failed package validation")
