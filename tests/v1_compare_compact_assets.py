"""Prove the compact preset left geometry, materials and identities intact."""

import hashlib
import json
import struct
from pathlib import Path

from isaac_web_exporter.identity import read_glb


root = Path(__file__).resolve().parents[1]
standard = root / "runs/v1/from-panel-package/scene.glb"
compact = root / "runs/v1/from-isaac-compact/scene.glb"
g1, tail1 = read_glb(standard)
g2, tail2 = read_glb(compact)


def binary(tail):
    length, kind = struct.unpack_from("<I4s", tail)
    assert kind == b"BIN\0"
    return tail[8:8 + length]


def accessors_for_meshes(gltf):
    indices = set()
    for mesh in gltf["meshes"]:
        for primitive in mesh["primitives"]:
            indices.update(primitive.get("attributes", {}).values())
            if "indices" in primitive:
                indices.add(primitive["indices"])
            for target in primitive.get("targets", []):
                indices.update(target.values())
    return sorted(indices)


def accessor_digest(gltf, data, index):
    accessor = gltf["accessors"][index]
    view = gltf["bufferViews"][accessor["bufferView"]]
    component_size = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}[accessor["componentType"]]
    components = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[accessor["type"]]
    element_size = component_size * components
    stride = view.get("byteStride", element_size)
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    payload = b"".join(data[start + number * stride:start + number * stride + element_size]
                       for number in range(accessor["count"]))
    return hashlib.sha256(payload).hexdigest()


mesh_indices = accessors_for_meshes(g1)
checks = {
    "meshDefinitionsEqual": g1["meshes"] == g2["meshes"],
    "materialDefinitionsEqual": g1.get("materials") == g2.get("materials"),
    "nodeDefinitionsEqual": g1["nodes"] == g2["nodes"],
    "meshAccessorBytesEqual": all(
        accessor_digest(g1, binary(tail1), index) ==
        accessor_digest(g2, binary(tail2), index) for index in mesh_indices),
    "extensionsUnchanged": g1.get("extensionsUsed") == g2.get("extensionsUsed"),
}
result = {"checks": checks, "meshAccessors": len(mesh_indices),
          "standardBytes": standard.stat().st_size, "compactBytes": compact.stat().st_size,
          "status": "PASS" if all(checks.values()) else "FAIL"}
target = root / "runs/v1/compact-asset-comparison.json"
target.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
if result["status"] != "PASS":
    raise SystemExit(1)
