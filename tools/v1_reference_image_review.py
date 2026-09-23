"""Measure matching scene silhouettes in Isaac and browser reference frames.

This is a geometry/framing aid, not a pixel-fidelity pass: RTX and WebGL use
different lighting, shadows, tone mapping, and material approximations.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def silhouette(path):
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.int16)
    background = rgb[0, 0]
    mask = np.max(np.abs(rgb - background), axis=2) > 10
    y, x = np.where(mask)
    if not len(x):
        raise ValueError(f"No scene pixels in {path}")
    return rgb, mask, {
        "size": [int(rgb.shape[1]), int(rgb.shape[0])],
        "background": background.tolist(),
        "boundingBox": [int(x.min()), int(y.min()), int(x.max()), int(y.max())],
        "scenePixelFraction": float(mask.mean()),
    }


parser = argparse.ArgumentParser()
parser.add_argument("isaac", type=Path)
parser.add_argument("browser", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()

reference = json.loads((args.isaac / "report.json").read_text(encoding="utf-8"))
browser = json.loads((args.browser / "report.json").read_text(encoding="utf-8"))
rows = []
source_images = []
browser_images = []
for source_frame, browser_frame in zip(reference["frames"], browser["frames"], strict=True):
    source_path = args.isaac / Path(source_frame["image"]).name
    browser_path = args.browser / Path(browser_frame["image"]).name
    source_rgb, source_mask, source = silhouette(source_path)
    browser_rgb, browser_mask, target = silhouette(browser_path)
    source_images.append(source_rgb)
    browser_images.append(browser_rgb)
    if source["size"] != target["size"]:
        raise ValueError(f"Different image sizes: {source_path} vs {browser_path}")
    intersection = np.logical_and(source_mask, browser_mask).sum()
    union = np.logical_or(source_mask, browser_mask).sum()
    rows.append({
        "isaacSeconds": source_frame["actualSeconds"],
        "browserSeconds": browser_frame["seconds"],
        "timeDifferenceSeconds": abs(source_frame["actualSeconds"] - browser_frame["seconds"]),
        "isaac": {"image": str(source_path), **source},
        "browser": {"image": str(browser_path), **target},
        "silhouetteIoU": float(intersection / union),
        "boundingBoxMaxEdgeDifferencePixels": max(abs(a - b) for a, b in zip(
            source["boundingBox"], target["boundingBox"])),
    })
motion = []
for index in range(1, len(rows)):
    source_change = np.max(np.abs(source_images[index] - source_images[index - 1]), axis=2) > 30
    browser_change = np.max(np.abs(browser_images[index] - browser_images[index - 1]), axis=2) > 30
    source_y, source_x = np.where(source_change)
    browser_y, browser_x = np.where(browser_change)
    if not len(source_x) or not len(browser_x):
        raise ValueError(f"Missing visual motion between frame {index - 1} and {index}")
    intersection = np.logical_and(source_change, browser_change).sum()
    union = np.logical_or(source_change, browser_change).sum()
    motion.append({
        "interval": [rows[index - 1]["isaacSeconds"], rows[index]["isaacSeconds"]],
        "isaacChangeBox": [int(source_x.min()), int(source_y.min()),
                           int(source_x.max()), int(source_y.max())],
        "browserChangeBox": [int(browser_x.min()), int(browser_y.min()),
                             int(browser_x.max()), int(browser_y.max())],
        "changedPixelIoU": float(intersection / union),
        "isaacChangedPixels": int(source_change.sum()),
        "browserChangedPixels": int(browser_change.sum()),
    })
result = {"sourceSha256": reference["sourceSha256"],
          "cameraUsd": reference["cameraUsd"], "comparisons": rows,
          "motion": motion,
          "interpretation": "Silhouette measures framing/geometry, not RTX-WebGL pixel color parity."}
args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
