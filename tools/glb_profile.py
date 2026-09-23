"""Profile portable package bytes and estimated in-browser asset memory."""

import argparse
import io
import json
import struct
from pathlib import Path

from isaac_web_exporter.identity import read_glb


def profile(package):
    package = Path(package)
    glb = package / "scene.glb"
    gltf, tail = read_glb(glb)
    binary_length, kind = struct.unpack_from("<I4s", tail)
    if kind != b"BIN\0":
        raise ValueError("Expected embedded GLB binary chunk")
    binary = tail[8:8 + binary_length]
    images = []
    for index, item in enumerate(gltf.get("images", [])):
        view = gltf["bufferViews"][item["bufferView"]]
        start = view.get("byteOffset", 0)
        payload = binary[start:start + view["byteLength"]]
        dimensions = None
        try:
            from PIL import Image
            with Image.open(io.BytesIO(payload)) as decoded:
                dimensions = list(decoded.size)
        except (ImportError, OSError, ValueError):
            pass
        images.append({"index": index, "mimeType": item.get("mimeType"),
                       "compressedBytes": len(payload), "dimensions": dimensions,
                       "estimatedRGBABytes": dimensions[0] * dimensions[1] * 4
                       if dimensions else None})
    package_files = {path.relative_to(package).as_posix(): path.stat().st_size
                     for path in package.rglob("*") if path.is_file()}
    return {"package": str(package), "packageBytes": sum(package_files.values()),
            "glbBytes": glb.stat().st_size, "images": images,
            "estimatedTextureRGBABytes": sum(image["estimatedRGBABytes"] or 0
                                             for image in images),
            "binaryBufferBytes": len(binary), "meshCount": len(gltf.get("meshes", [])),
            "materialCount": len(gltf.get("materials", [])),
            "animationCount": len(gltf.get("animations", [])),
            "gpuMemoryEstimateNote": "RGBA texture and GLB binary estimates only; dedicated GPU memory unavailable from browser"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    print(json.dumps(profile(args.package), indent=2))


if __name__ == "__main__":
    main()
