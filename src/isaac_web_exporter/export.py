"""Small, config-driven Isaac Sim recorded-playback exporter (alpha experiment).

Run with Isaac's python.sh. A separate bootstrap module builds/starts a project;
this module discovers rigid bodies, samples poses, and packages an animated GLB.
"""

import argparse
import asyncio
import hashlib
import importlib.util
import inspect
import json
import math
import shutil
import struct
import sys
import time
import traceback
from pathlib import Path

from isaacsim import SimulationApp


def load_bootstrap(path):
    spec = importlib.util.spec_from_file_location("isaac_export_bootstrap", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load bootstrap: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    spec.loader.exec_module(module)
    if not callable(getattr(module, "build", None)):
        raise ValueError("Bootstrap must define build(stage, app, config)")
    return module.build


def glb_summary(path):
    data = path.read_bytes()
    if data[:4] != b"glTF":
        raise ValueError("Asset Converter output is not a GLB")
    length, chunk_type = struct.unpack_from("<I4s", data, 12)
    if chunk_type != b"JSON":
        raise ValueError("GLB JSON chunk is missing")
    gltf = json.loads(data[20:20 + length])
    nodes = gltf.get("nodes", [])
    channels = [
        {"node": nodes[channel["target"]["node"]].get("name"),
         "path": channel["target"]["path"]}
        for animation in gltf.get("animations", [])
        for channel in animation.get("channels", [])
    ]
    external = [
        item["uri"] for group in ("buffers", "images")
        for item in gltf.get(group, []) if item.get("uri") and not item["uri"].startswith("data:")
    ]
    node_anomalies = [
        {"node": node.get("name", str(index)), "property": key, "value": values}
        for index, node in enumerate(nodes)
        for key in ("translation", "rotation", "scale")
        if (values := node.get(key)) is not None
        and any(not math.isfinite(value) or abs(value) > 1e6 for value in values)
    ]
    return {
        "bytes": len(data), "meshes": len(gltf.get("meshes", [])),
        "materials": len(gltf.get("materials", [])),
        "animations": len(gltf.get("animations", [])),
        "channels": channels, "external_uris": external,
        "node_anomalies": node_anomalies,
    }


def tessellate_cubes(stage):
    """Turn USD analytic cubes into meshes in the disposable conversion stage."""
    from pxr import Gf, UsdGeom

    converted = []
    for prim in list(stage.Traverse()):
        if not prim.IsA(UsdGeom.Cube):
            continue
        size = UsdGeom.Cube(prim).GetSizeAttr().Get()
        half = float(size if size is not None else 2.0) / 2
        path = prim.GetPath()
        mesh = UsdGeom.Mesh.Define(stage, path)
        mesh.CreatePointsAttr([
            Gf.Vec3f(x * half, y * half, z * half)
            for x, y, z in ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
                            (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1))
        ])
        mesh.CreateFaceVertexCountsAttr([4] * 6)
        mesh.CreateFaceVertexIndicesAttr([
            0, 3, 2, 1, 4, 5, 6, 7, 0, 1, 5, 4,
            1, 2, 6, 5, 2, 3, 7, 6, 3, 0, 4, 7,
        ])
        mesh.CreateSubdivisionSchemeAttr("none")
        converted.append(str(path))
    return converted


def pose_matrix(Gf, pos, quat):
    matrix = Gf.Matrix4d().SetRotate(
        Gf.Rotation(Gf.Quatd(quat[0], Gf.Vec3d(*quat[1:]))))
    matrix.SetTranslateOnly(Gf.Vec3d(*pos))
    return matrix


def run(config_path, app=None, stage=None, on_step=None):
    """Export from a bootstrap, saved USD, or an already loaded Isaac stage.

    Supplying app and stage lets an Isaac extension call this without creating or
    closing another SimulationApp. The caller retains ownership of both objects.
    """
    config_path = config_path.resolve()
    config = json.loads(config_path.read_text())
    loaded_mode = stage is not None
    if loaded_mode and app is None:
        raise ValueError("A loaded stage requires its existing SimulationApp")
    output = Path(config["output_dir"]).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite output directory: {output}")
    output.mkdir(parents=True)
    report = {
        "schemaVersion": "alpha-0.1", "status": "started", "warnings": [],
        "errors": [], "capture": {}, "converter": {}, "glb": {},
    }
    owns_app = app is None
    if owns_app:
        app = SimulationApp({"headless": True, "renderer": "RaytracedLighting"})
    try:
        import omni.usd
        import omni.kit.asset_converter as converter
        from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade, UsdUtils
        from isaacsim.core.experimental.prims import RigidPrim
        import isaacsim.core.experimental.utils.app as app_utils
        import isaacsim.core.experimental.utils.stage as stage_utils

        input_usd = config.get("input_usd")
        if sum((bool(input_usd), bool(config.get("bootstrap")), loaded_mode)) != 1:
            raise ValueError("Specify one input: input_usd, bootstrap, or supplied app/stage")
        if loaded_mode:
            fps = float(config.get("fps", 30))
            start_time = 0.0
            duration = float(config.get("duration_seconds", 2))
            built = {}
        elif input_usd:
            if config.get("capture_roots", []):
                raise ValueError("input_usd preserves authored animation; physics capture needs a bootstrap")
            stage = Usd.Stage.Open(str(Path(input_usd).resolve()))
            if not stage:
                raise FileNotFoundError(f"Cannot open input_usd: {input_usd}")
            fps = float(stage.GetTimeCodesPerSecond())
            start_time = float(stage.GetStartTimeCode())
            duration = (float(stage.GetEndTimeCode()) - start_time) / fps
            built = {}
        else:
            bootstrap_path = Path(config["bootstrap"]).resolve()
            build = load_bootstrap(bootstrap_path)
            stage_utils.create_new_stage()
            stage = omni.usd.get_context().get_stage()
            fps = float(config.get("fps", 30))
            start_time = 0.0
            duration = float(config.get("duration_seconds", 2))
        simulation_hz = float(config.get("simulation_hz", 60))
        if fps <= 0 or simulation_hz <= 0 or duration <= 0:
            raise ValueError("fps, simulation_hz, and duration_seconds must be positive")
        updates = round(duration * simulation_hz)
        sample_every = int(config.get("sample_every_updates", 2))
        if sample_every < 1 or updates < 1:
            raise ValueError("Invalid capture step count")
        if not input_usd and not loaded_mode:
            stage.SetTimeCodesPerSecond(fps)
            stage.SetFramesPerSecond(fps)
            stage.SetStartTimeCode(0)
            stage.SetEndTimeCode(duration * fps)
            built = build(stage, app, config)
            if inspect.isawaitable(built):
                future = asyncio.ensure_future(built)
                deadline = time.monotonic() + float(config.get("bootstrap_timeout_seconds", 180))
                while not future.done() and time.monotonic() < deadline:
                    app.update()
                if not future.done():
                    raise TimeoutError("Asynchronous project bootstrap did not finish")
                built = future.result()
        built = built or {}
        on_step = on_step or built.get("on_step")
        if on_step is not None and not callable(on_step):
            raise ValueError("build() returned a non-callable on_step")
        # Project loaders such as BaseSample may replace the active stage.
        if not input_usd and not loaded_mode:
            stage = omni.usd.get_context().get_stage()
            stage.SetTimeCodesPerSecond(fps)
            stage.SetFramesPerSecond(fps)
            stage.SetStartTimeCode(0)
            stage.SetEndTimeCode(duration * fps)
        app.update()

        selected_roots = config.get("capture_roots", [] if input_usd else ["/World"])
        selected = [
            prim for prim in stage.Traverse()
            if prim.HasAPI(UsdPhysics.RigidBodyAPI)
            and any(str(prim.GetPath()) == root or str(prim.GetPath()).startswith(root + "/")
                    for root in selected_roots)
        ]
        paths = [str(prim.GetPath()) for prim in selected]
        if len({Path(path).name for path in paths}) != len(paths):
            raise ValueError("Captured rigid-body leaf names must be unique for GLB channel mapping")
        if not paths and not input_usd:
            report["warnings"].append("No rigid-body prims were discovered; authored animation only")
        if config.get("expected_rigid_bodies") is not None and len(paths) != config["expected_rigid_bodies"]:
            raise ValueError(f"Expected {config['expected_rigid_bodies']} rigid bodies, found {paths}")
        rigs = {path: RigidPrim(paths=path) for path in paths}
        base = output / "base.usda"
        stage.Export(str(base))

        tracks = {path: [] for path in paths}
        if paths or on_step:
            app_utils.play()
            app.update()
            for step in range(updates + 1):
                if on_step:
                    on_step(step, app)
                app.update()
                if step % sample_every == 0 or step == updates:
                    timecode = min(step / simulation_hz * fps, duration * fps)
                    for path, rig in rigs.items():
                        positions, orientations = rig.get_world_poses()
                        pos = [float(v) for v in positions.numpy()[0]]
                        quat = [float(v) for v in orientations.numpy()[0]]
                        tracks[path].append((timecode, pos, quat))
            app_utils.stop()
            app.update()

        export_stage = Usd.Stage.Open(str(base))
        if loaded_mode:
            export_stage.SetTimeCodesPerSecond(fps)
            export_stage.SetFramesPerSecond(fps)
            export_stage.SetStartTimeCode(start_time)
            export_stage.SetEndTimeCode(duration * fps)
        report["converted_analytic_cubes"] = tessellate_cubes(export_stage)
        xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
        for path, track in tracks.items():
            prim = export_stage.GetPrimAtPath(path)
            if not prim:
                raise ValueError(f"Rigid prim missing from base stage: {path}")
            parent = prim.GetParent()
            parent_world = xform_cache.GetParentToWorldTransform(prim)
            moving_ancestor = parent
            while moving_ancestor and str(moving_ancestor.GetPath()) != "/":
                if str(moving_ancestor.GetPath()) in tracks:
                    break
                moving_ancestor = moving_ancestor.GetParent()
            ancestor_path = str(moving_ancestor.GetPath()) if moving_ancestor else None
            if ancestor_path not in tracks:
                ancestor_path = None
            if ancestor_path:
                ancestor_base_world = xform_cache.GetLocalToWorldTransform(moving_ancestor)
                fixed_parent_offset = parent_world * ancestor_base_world.GetInverse()
            report.setdefault("localization", {})[path] = {
                "moving_ancestor": ancestor_path,
                "method": "sampled-ancestor" if ancestor_path else "static-parent",
            }
            xform = UsdGeom.Xformable(prim)
            scale_ops = [op for op in xform.GetOrderedXformOps()
                         if op.GetOpType() == UsdGeom.XformOp.TypeScale]
            if len(scale_ops) > 1:
                raise ValueError(f"Multiple scale ops need explicit handling: {path}")
            scale_value = scale_ops[0].Get() if scale_ops else None
            xform.ClearXformOpOrder()
            translate = xform.AddTranslateOp(opSuffix="replay")
            orient = xform.AddOrientOp(opSuffix="replay")
            if scale_value is not None:
                xform.AddScaleOp(opSuffix="replay").Set(scale_value)
            for index, (timecode, pos, quat) in enumerate(track):
                if ancestor_path:
                    _, ancestor_pos, ancestor_quat = tracks[ancestor_path][index]
                    ancestor_world = pose_matrix(Gf, ancestor_pos, ancestor_quat)
                    dynamic_parent_world = fixed_parent_offset * ancestor_world
                else:
                    dynamic_parent_world = parent_world
                local = Gf.Transform(pose_matrix(Gf, pos, quat) * dynamic_parent_world.GetInverse())
                local_quat = local.GetRotation().GetQuat()
                local_translation = local.GetTranslation()
                local_orientation = Gf.Quatf(local_quat.GetReal(), Gf.Vec3f(local_quat.GetImaginary()))
                if index == 0:
                    # Asset Converter reads the default opinion for GLB node transforms.
                    translate.Set(local_translation)
                    orient.Set(local_orientation)
                translate.Set(local_translation, timecode)
                orient.Set(local_orientation, timecode)
            xyz = [tuple(round(v, 5) for v in point[1]) for point in track]
            report["capture"][path] = {
                "samples": len(track), "unique_positions": len(set(xyz)),
                "first_position": track[0][1], "last_position": track[-1][1],
            }
            if len(set(xyz)) < 2:
                report["warnings"].append(f"{path}: no translation motion captured")
        recorded = output / "recorded_scene.usda"
        export_stage.GetRootLayer().Export(str(recorded))
        dependency_layers, dependency_assets, unresolved = UsdUtils.ComputeAllDependencies(
            Sdf.AssetPath(str(recorded)))
        report["source_dependencies"] = {
            "resolved_layers": len(dependency_layers),
            "resolved_assets": len(dependency_assets),
            "unresolved": [str(path) for path in unresolved],
        }
        required_suffixes = {".usd", ".usda", ".usdc", ".usdz", ".png", ".jpg",
                             ".jpeg", ".tif", ".tiff", ".exr", ".hdr", ".ktx", ".webp"}
        missing_visual = [str(path) for path in unresolved
                          if Path(str(path).split("?")[0]).suffix.lower() in required_suffixes]
        if missing_visual:
            raise RuntimeError(f"Unresolved required visual dependencies: {missing_visual}")
        if unresolved:
            report["warnings"].append(
                f"Unresolved nonvisual/unknown dependencies: {[str(path) for path in unresolved]}")

        # Warn about materials that the simple PreviewSurface proof cannot validate.
        shader_ids = sorted({
            str(UsdShade.Shader(prim).GetIdAttr().Get())
            for prim in export_stage.Traverse() if prim.IsA(UsdShade.Shader)
        })
        unknown_shaders = [name for name in shader_ids if name != "UsdPreviewSurface"]
        if unknown_shaders:
            report["warnings"].append(f"Non-PreviewSurface shaders need visual QA: {unknown_shaders}")

        context = converter.AssetConverterContext()
        context.ignore_animations = False
        context.embed_textures = True
        context.export_mdl_gltf_extension = False
        glb = output / "scene.glb"
        task = converter.get_instance().create_converter_task(str(recorded), str(glb), None, context)
        future = asyncio.ensure_future(task.wait_until_finished())
        started = time.monotonic()
        deadline = started + float(config.get("conversion_timeout_seconds", 180))
        while not future.done() and time.monotonic() < deadline:
            app.update()
        finished = future.done()
        ok = bool(future.result()) if finished else False
        report["converter"] = {
            "success": ok, "status": str(task.get_status()),
            "error": task.get_error_message(),
            "finished": finished,
            "elapsed_seconds": round(time.monotonic() - started, 2),
        }
        if not ok or not glb.exists():
            raise RuntimeError(f"Asset conversion failed or timed out: {report['converter']}")
        report["glb"] = glb_summary(glb)
        if report["glb"]["external_uris"]:
            raise RuntimeError(f"GLB has nonportable external URIs: {report['glb']['external_uris']}")
        if report["glb"]["node_anomalies"]:
            raise RuntimeError(f"GLB has implausible node transforms: {report['glb']['node_anomalies']}")
        if report["glb"]["meshes"] == 0:
            raise RuntimeError("GLB contains no meshes")
        if report["glb"]["animations"] == 0:
            raise RuntimeError("GLB contains no animation; refusing false success")
        for path, stats in report["capture"].items():
            if stats["unique_positions"] > 1 and not any(
                    c["node"] == Path(path).name and c["path"] == "translation"
                    for c in report["glb"]["channels"]):
                raise RuntimeError(f"Animated rigid body missing from GLB: {path}")

        viewer = Path(config["viewer_template"]).resolve()
        if not (viewer / "index.html").is_file():
            raise FileNotFoundError(f"Viewer template missing index.html: {viewer}")
        package = output / "package"
        shutil.copytree(viewer, package)
        shutil.copy2(glb, package / "scene.glb")
        manifest = {
            "schemaVersion": "alpha-0.1", "mode": "recorded-playback",
            "asset": "scene.glb", "durationSeconds": duration,
            "assetSha256": hashlib.sha256(glb.read_bytes()).hexdigest(),
            "fps": fps, "startTimeCode": start_time,
            "endTimeCode": float(export_stage.GetEndTimeCode()),
            "metersPerUnit": float(UsdGeom.GetStageMetersPerUnit(export_stage)),
            "sourceUpAxis": str(UsdGeom.GetStageUpAxis(export_stage)),
            "viewerUpAxis": "Y", "capturedRigidBodies": paths,
            "capture": {"roots": selected_roots, "simulationHz": simulation_hz,
                        "sampleEveryUpdates": sample_every},
            "source": {"application": "Isaac Sim", "version": omni.kit.app.get_app().get_app_version()},
        }
        if "camera" in config:
            camera = config["camera"]
            for key in ("position", "target"):
                values = camera.get(key)
                if not isinstance(values, list) or len(values) != 3 or not all(
                        isinstance(value, (int, float)) and math.isfinite(value) for value in values):
                    raise ValueError(f"camera.{key} must be three finite viewer-space numbers")
            manifest["camera"] = camera
        (package / "manifest.json").write_text(json.dumps(manifest, indent=2))
        (package / "scene-map.json").write_text(json.dumps({
            "schemaVersion": "alpha-0.1", "objects": [
                {"id": path, "node": Path(path).name, "role": "recorded-rigid-body",
                 "recording": report["capture"][path]}
                for path in paths],
            "animation": {"durationSeconds": duration},
        }, indent=2))
        (package / "LLM-HANDOFF.md").write_text(
            "# Browser scene handoff\n\n"
            "`scene.glb` is the source of truth for geometry, hierarchy, materials,\n"
            "object placement and the recorded animation clip. The player loads\n"
            "it directly; preserve its node names when changing viewer code.\n\n"
            "`manifest.json` gives playback duration, axes, units, capture settings\n"
            "and the GLB SHA-256. `scene-map.json` maps Isaac prim paths to GLB\n"
            "node names and lists captured motion endpoints. `compatibility-report.json`\n"
            "records conversion limits. Custom experiences can use Three.js and\n"
            "GLTFLoader to reuse the exact scene and clip. This is recorded motion,\n"
            "not live Isaac physics or controller behavior. Keep the package assets\n"
            "local for self-hosting and review content licenses before sharing.\n"
        )
        (package / "README.txt").write_text(
            "Isaac recorded-playback export (experimental alpha)\n\n"
            "Serve this directory over static HTTP, e.g. python -m http.server 8000.\n"
            "Open that URL in a browser. Start, Pause, Restart, orbit drag, right-drag\n"
            "pan, and scroll zoom are available. Browser playback does not run Isaac\n"
            "physics or project controllers. Read compatibility-report.json for\n"
            "capture and conversion findings. Review source-asset permissions\n"
            "before distributing a package containing third-party content.\n"
        )
        report["status"] = "success"
        (package / "compatibility-report.json").write_text(json.dumps(report, indent=2))
    except Exception as error:
        report["status"] = "failed"
        report["errors"].append(repr(error))
        traceback.print_exc()
    finally:
        (output / "report.json").write_text(json.dumps(report, indent=2))
        print("EXPORT_RESULT", json.dumps(report), flush=True)
        # Isaac's default fast shutdown can terminate the process from close().
        # Pass the status there so a failed export also fails the CLI process.
        if owns_app:
            app.close(exit_code=0 if report["status"] == "success" else 1)
    return report["status"] == "success"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    sys.exit(0 if run(args.config) else 1)


if __name__ == "__main__":
    main()
