"""Preserve source prim identities in an Asset Converter GLB.

The converter preserves the USD hierarchy in tested fixtures, but does not
provide a stable source-path field. Reconcile by complete ancestor path, then
embed the result into standard glTF node extras. This module has no Isaac import
so its GLB mechanics can be checked on a normal development machine.
"""

import json
import struct
from collections import defaultdict
from pathlib import Path


def read_glb(path):
    data = Path(path).read_bytes()
    if len(data) < 20 or data[:4] != b"glTF" or struct.unpack_from("<I", data, 8)[0] != len(data):
        raise ValueError("Invalid GLB header or length")
    json_size, kind = struct.unpack_from("<I4s", data, 12)
    if kind != b"JSON" or 20 + json_size > len(data):
        raise ValueError("Missing or truncated GLB JSON chunk")
    return json.loads(data[20:20 + json_size]), data[20 + json_size:]


def node_source_paths(gltf, source_paths):
    """Return node index -> source path, matched by full hierarchy suffix."""
    nodes = gltf.get("nodes", [])
    source_paths = set(source_paths)
    mapping = {}
    seen = set()

    def visit(index, ancestry, ancestor_source=None):
        if index in seen:
            return
        seen.add(index)
        node = nodes[index]
        segments = ancestry + [node.get("name", "")]
        source = ancestor_source
        if all(segments):
            matches = ["/" + "/".join(segments[start:]) for start in range(len(segments))]
            candidates = [path for path in matches if path in source_paths]
            if candidates:
                source = max(candidates, key=lambda path: (path.count("/"), len(path)))
        if source:
            mapping[index] = source
        for child in node.get("children", []):
            if child < 0 or child >= len(nodes):
                raise ValueError(f"GLB node {index} has invalid child {child}")
            visit(child, segments, source)

    for scene in gltf.get("scenes", []):
        for root in scene.get("nodes", []):
            visit(root, [])
    return mapping


def animation_sample_times(path):
    """Read distinct key times for each GLB animation, in seconds."""
    gltf, tail = read_glb(path)
    if len(tail) < 8:
        return [[] for _ in gltf.get("animations", [])]
    size, kind = struct.unpack_from("<I4s", tail, 0)
    if kind != b"BIN\0" or size + 8 > len(tail):
        raise ValueError("Missing or truncated GLB binary chunk")
    binary = tail[8:8 + size]
    groups = []
    for animation in gltf.get("animations", []):
        times = set()
        for sampler in animation.get("samplers", []):
            accessor = gltf["accessors"][sampler["input"]]
            if accessor.get("componentType") != 5126 or accessor.get("type") != "SCALAR":
                raise ValueError("Unsupported animation time accessor")
            view = gltf["bufferViews"][accessor["bufferView"]]
            stride = view.get("byteStride", 4)
            start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
            for index in range(accessor["count"]):
                offset = start + index * stride
                if offset + 4 > len(binary):
                    raise ValueError("Animation time accessor exceeds GLB binary chunk")
                times.add(struct.unpack_from("<f", binary, offset)[0])
        groups.append(sorted(times))
    return groups


def enrich_glb(path, source_paths, required_paths=()):
    """Add ID extras and return a complete object catalog for mapped prims."""
    path = Path(path)
    gltf, tail = read_glb(path)
    mapping = node_source_paths(gltf, source_paths)
    grouped = defaultdict(list)
    for index, source_path in mapping.items():
        gltf["nodes"][index].setdefault("extras", {})["isaacObjectId"] = source_path
        grouped[source_path].append(index)
    missing = sorted(set(required_paths) - set(grouped))
    if missing:
        raise ValueError(f"Moving source objects absent from converted GLB: {missing}")
    catalog = []
    for source_path, indices in sorted(grouped.items()):
        if source_path == "/World":
            continue
        catalog.append({
            "id": source_path,
            "displayName": source_path.rsplit("/", 1)[-1],
            "sourcePrimPath": source_path,
            "parentId": source_path.rsplit("/", 1)[0] or None,
            "nodeIndices": sorted(indices),
            "nodes": [gltf["nodes"][index].get("name", "") for index in sorted(indices)],
        })
    serialized = json.dumps(gltf, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    serialized += b" " * ((-len(serialized)) % 4)
    rewritten = b"glTF" + struct.pack("<II", 2, 20 + len(serialized) + len(tail))
    rewritten += struct.pack("<I4s", len(serialized), b"JSON") + serialized + tail
    path.write_bytes(rewritten)
    return catalog
