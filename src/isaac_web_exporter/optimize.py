"""Opt-in, decoder-free GLB animation simplification with measured error.

The standard package remains the reference. Compact mode removes only LINEAR
keyframes whose reconstructed transform stays within fixed v1 tolerances at
every original key time. Geometry, materials, topology and node indices remain
unchanged. Unknown GLB extensions or accessor layouts fail closed.
"""

import json
import math
import struct
from collections import Counter
from pathlib import Path

from isaac_web_exporter.identity import read_glb


TOLERANCE = {"translation": 0.0001, "rotation": 0.005, "scale": 0.0001}
COMPONENTS = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}


def _angle_error(left, right):
    dot = min(1.0, abs(sum(a * b for a, b in zip(left, right))))
    return math.degrees(2 * math.acos(dot))


def _interpolate(left, right, fraction, kind):
    if kind == "rotation":
        dot = sum(a * b for a, b in zip(left, right))
        if dot < 0:
            right = tuple(-value for value in right)
            dot = -dot
        dot = min(1.0, dot)
        if dot > 0.9995:
            mixed = [a + (b - a) * fraction for a, b in zip(left, right)]
        else:
            angle = math.acos(dot)
            sine = math.sin(angle)
            a = math.sin((1 - fraction) * angle) / sine
            b = math.sin(fraction * angle) / sine
            mixed = [a * x + b * y for x, y in zip(left, right)]
        length = math.sqrt(sum(value * value for value in mixed))
        return tuple(value / length for value in mixed)
    return tuple(a + (b - a) * fraction for a, b in zip(left, right))


def _error(actual, estimated, kind):
    if kind == "rotation":
        return _angle_error(actual, estimated)
    if kind == "scale":
        return max(abs(a - b) / max(abs(a), 0.000001)
                   for a, b in zip(actual, estimated))
    return math.dist(actual, estimated)


def _simplify(times, values, kind):
    if len(times) <= 2:
        return list(range(len(times))), 0.0
    keep = {0, len(times) - 1}
    segments = [(0, len(times) - 1)]
    maximum = 0.0
    while segments:
        begin, end = segments.pop()
        biggest = 0.0
        split = None
        span = times[end] - times[begin]
        if span <= 0:
            raise ValueError("Animation key times must increase")
        for index in range(begin + 1, end):
            fraction = (times[index] - times[begin]) / span
            estimate = _interpolate(values[begin], values[end], fraction, kind)
            error = _error(values[index], estimate, kind)
            if error > biggest:
                biggest, split = error, index
        if biggest > TOLERANCE[kind]:
            keep.add(split)
            segments.extend(((begin, split), (split, end)))
        else:
            maximum = max(maximum, biggest)
    return sorted(keep), maximum


def _accessor_values(gltf, binary, index):
    accessor = gltf["accessors"][index]
    if accessor.get("componentType") != 5126 or accessor.get("sparse"):
        raise ValueError("Compact mode supports dense FLOAT animation accessors only")
    count = COMPONENTS.get(accessor.get("type"))
    if count is None:
        raise ValueError("Compact mode supports SCALAR/VEC3/VEC4 animation accessors only")
    view = gltf["bufferViews"][accessor["bufferView"]]
    if view.get("buffer", 0) != 0:
        raise ValueError("Compact mode supports one embedded GLB buffer")
    step = view.get("byteStride", count * 4)
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    result = []
    for number in range(accessor["count"]):
        offset = start + number * step
        if offset + count * 4 > len(binary):
            raise ValueError("Animation accessor extends past the GLB binary")
        result.append(struct.unpack_from("<" + "f" * count, binary, offset))
    return result


def compact_animation_glb(path):
    path = Path(path)
    original_bytes = path.stat().st_size
    gltf, tail = read_glb(path)
    if gltf.get("extensionsUsed") or len(gltf.get("buffers", [])) != 1:
        raise ValueError("Compact mode cannot safely edit extended or multi-buffer GLBs")
    if len(tail) < 8:
        raise ValueError("GLB lacks binary data")
    size, kind = struct.unpack_from("<I4s", tail)
    if kind != b"BIN\0" or size + 8 > len(tail):
        raise ValueError("GLB binary chunk is invalid")
    binary = tail[8:8 + size]
    use_count = Counter()
    for animation in gltf.get("animations", []):
        for sampler in animation.get("samplers", []):
            use_count[sampler["input"]] += 1
            use_count[sampler["output"]] += 1
    new_content = {}
    changes = []
    for animation in gltf.get("animations", []):
        channels = animation.get("channels", [])
        for sampler_index, sampler in enumerate(animation.get("samplers", [])):
            related = [channel for channel in channels if channel["sampler"] == sampler_index]
            if len(related) != 1 or sampler.get("interpolation", "LINEAR") != "LINEAR":
                continue
            kind = related[0]["target"].get("path")
            if kind not in TOLERANCE or any(use_count[sampler[key]] != 1
                                            for key in ("input", "output")):
                continue
            times = [item[0] for item in _accessor_values(gltf, binary, sampler["input"])]
            values = _accessor_values(gltf, binary, sampler["output"])
            if len(times) != len(values) or len(times) < 3:
                continue
            selected, maximum = _simplify(times, values, kind)
            if len(selected) == len(times):
                continue
            for accessor_index, source in ((sampler["input"], times),
                                           (sampler["output"], values)):
                accessor = gltf["accessors"][accessor_index]
                components = COMPONENTS[accessor["type"]]
                chosen = [source[index] for index in selected]
                payload = b"".join(struct.pack("<" + "f" * components,
                                                *(value if components > 1 else (value,)))
                                   for value in chosen)
                view_index = len(gltf["bufferViews"])
                gltf["bufferViews"].append({"buffer": 0, "byteLength": len(payload)})
                new_content[view_index] = payload
                accessor["bufferView"] = view_index
                accessor.pop("byteOffset", None)
                accessor["count"] = len(selected)
                if components == 1:
                    accessor["min"] = [chosen[0]]
                    accessor["max"] = [chosen[-1]]
                else:
                    accessor.pop("min", None)
                    accessor.pop("max", None)
            changes.append({"path": kind, "nodeIndex": related[0]["target"]["node"],
                            "before": len(times), "after": len(selected),
                            "maximumErrorAtOriginalSamples": maximum})
    if not changes:
        return {"preset": "compact", "beforeBytes": original_bytes,
                "afterBytes": original_bytes, "changes": []}
    referenced = {item["bufferView"] for item in gltf.get("accessors", [])
                  if "bufferView" in item}
    referenced.update(item["bufferView"] for item in gltf.get("images", [])
                      if "bufferView" in item)
    rebuilt = bytearray()
    remap = {}
    views = []
    for old_index in sorted(referenced):
        view = gltf["bufferViews"][old_index]
        content = new_content.get(old_index)
        if content is None:
            start = view.get("byteOffset", 0)
            content = binary[start:start + view["byteLength"]]
            if len(content) != view["byteLength"]:
                raise ValueError("Referenced GLB bufferView is truncated")
        rebuilt.extend(b"\0" * (-len(rebuilt) % 4))
        current = {**view, "byteOffset": len(rebuilt)}
        views.append(current)
        remap[old_index] = len(views) - 1
        rebuilt.extend(content)
    for accessor in gltf.get("accessors", []):
        if "bufferView" in accessor:
            accessor["bufferView"] = remap[accessor["bufferView"]]
    for image in gltf.get("images", []):
        if "bufferView" in image:
            image["bufferView"] = remap[image["bufferView"]]
    gltf["bufferViews"] = views
    gltf["buffers"][0]["byteLength"] = len(rebuilt)
    rebuilt.extend(b"\0" * (-len(rebuilt) % 4))
    encoded = json.dumps(gltf, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    encoded += b" " * (-len(encoded) % 4)
    total = 12 + 8 + len(encoded) + 8 + len(rebuilt)
    result = b"glTF" + struct.pack("<II", 2, total)
    result += struct.pack("<I4s", len(encoded), b"JSON") + encoded
    result += struct.pack("<I4s", len(rebuilt), b"BIN\0") + rebuilt
    path.write_bytes(result)
    return {"preset": "compact", "beforeBytes": original_bytes,
            "afterBytes": len(result), "changes": changes}
