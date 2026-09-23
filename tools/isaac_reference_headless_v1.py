"""Render owned sort-cell USD reference frames with the working Kit entrypoint.

Run via ``runheadless.sh --exec`` in the pinned Isaac 6.1 image. The source USD
is opened read-only and never saved; output goes into a separate runs folder.
"""

import asyncio
import hashlib
import json
import math
import os
import traceback
from pathlib import Path


async def _run():
    import numpy as np
    from PIL import Image
    import omni.timeline
    import omni.usd
    from pxr import UsdLux
    from isaacsim.core.experimental.utils import app as app_utils
    from isaacsim.sensors.experimental.rtx import CameraSensor, RtxCamera
    from isaacsim.core.rendering_manager import ViewportManager
    import isaacsim.core.utils.stage as stage_utils

    source = Path("/work/runs/v1-sort-cell-guided/recorded_scene.usda")
    output = Path("/work/runs/v1-reference-headless-fresh")
    output.mkdir(parents=True, exist_ok=True)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    if not stage_utils.open_stage(str(source)):
        raise RuntimeError(f"Cannot open owned USD: {source}")
    stage = omni.usd.get_context().get_stage()
    UsdLux.DistantLight.Define(stage, "/World/ReferenceLight").CreateIntensityAttr(1800)

    # The package camera is Y-up: eye [7, 6, 9], target [0, .6, .5].
    # Isaac's stage is Z-up, and the browser conversion maps (x,y,z) to
    # (x,z,-y), giving the inverse camera coordinates below.
    eye = [7.0, -9.0, 6.0]
    target = [0.0, -0.5, 0.6]
    width, height = 1280, 720
    vertical_fov = 50.0
    horizontal_fov = math.degrees(2 * math.atan(
        math.tan(math.radians(vertical_fov) / 2) * width / height))
    authored = RtxCamera("/World/ReferenceCamera", tick_rate=30.0, positions=eye)
    authored.camera.set_clipping_ranges(0.05, 100.0)
    # Isaac's experimental API uses centimetre-scaled focal length.
    authored.camera.set_focal_lengths(
        2.0955 / (2 * math.tan(math.radians(horizontal_fov) / 2)))
    app_utils.stop(commit=True)
    await app_utils.update_app_async()
    # In the tested 6.1 runtime this constructor takes (rows, columns).
    # Confirm the resulting array shape before accepting any reference frame.
    sensor = CameraSensor(authored, resolution=(height, width), annotators=["rgb"])
    ViewportManager.set_camera_view(sensor.camera.paths[0], eye=eye, target=target)
    app_utils.play(commit=True)
    timeline = omni.timeline.get_timeline_interface()

    frames = []
    previous = None
    for requested in (0.0, 15.0, 29.0):
        timeline.set_current_time(requested)
        image = None
        actual = None
        changed = None
        for attempt in range(60):
            await app_utils.update_app_async()
            rgb, _ = sensor.get_data("rgb")
            if rgb is None:
                continue
            pixels = np.asarray(rgb.numpy())
            if pixels.size and pixels.ndim == 3 and pixels.shape[2] >= 3:
                if pixels.shape[:2] != (height, width):
                    raise RuntimeError(f"Unexpected camera array shape: {pixels.shape}")
                candidate = pixels[:, :, :3]
                if previous is not None:
                    changed = float(np.abs(candidate.astype(np.float32) -
                                           previous.astype(np.float32)).mean())
                if attempt % 10 == 0:
                    print("ISAAC_REFERENCE_WAIT", requested, attempt,
                          timeline.get_current_time(), changed, flush=True)
                if attempt >= 7 and (previous is None or changed > 0.75):
                    image = candidate.copy()
                    actual = timeline.get_current_time()
                    break
        if image is None:
            raise RuntimeError(f"RTX camera produced no fresh RGB at {requested}s")
        if image.dtype != np.uint8:
            image = (np.clip(image, 0, 1) * 255).astype(np.uint8)
        path = output / f"isaac-{requested:g}.png"
        Image.fromarray(image).save(path)
        entry = {"requestedSeconds": requested, "actualSeconds": actual,
                 "image": str(path), "shape": list(image.shape),
                 "changedFromPreviousMeanAbs": changed,
                 "pixelStdDev": float(image.std()),
                 "min": int(image.min()), "max": int(image.max())}
        frames.append(entry)
        print("ISAAC_REFERENCE_FRAME", json.dumps(entry), flush=True)
        if entry["pixelStdDev"] < 3:
            raise RuntimeError(f"Reference frame appears blank: {entry}")
        previous = image

    after = hashlib.sha256(source.read_bytes()).hexdigest()
    if after != before:
        raise RuntimeError("Source USD changed during reference capture")
    report = {"sourceSha256": before, "frames": frames,
              "cameraUsd": {"eye": eye, "target": target,
                            "verticalFovDegrees": vertical_fov},
              "renderer": "Isaac Sim 6.1 RTX via runheadless.sh"}
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("ISAAC_REFERENCE_DONE", json.dumps(report), flush=True)


async def _guarded():
    try:
        await _run()
    except BaseException as error:
        traceback.print_exc()
        print("ISAAC_REFERENCE_ERROR", repr(error), flush=True)
        os._exit(1)
    os._exit(0)


asyncio.ensure_future(_guarded())
