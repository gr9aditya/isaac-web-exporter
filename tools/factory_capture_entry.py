"""Capture the actual read-only factory run as fixed-topology USD motion.

This runs only in an isolated Isaac container. It wraps the project's async
update boundary to observe poses; it never edits the project checkout.
"""

import asyncio
import json
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, "/project")
sys.path.insert(0, "/work/src")


class Capture:
    def __init__(self, output):
        self.output = output
        self.output.mkdir(parents=True, exist_ok=True)
        self.ready = False
        self.frames = 0
        self.next_sample = 0
        self.rigs = None
        self.paths = []
        self.tracks = {}
        self.items = []

    def begin(self):
        if self.ready:
            return
        import omni.usd
        from pxr import UsdPhysics
        from isaacsim.core.experimental.prims import RigidPrim

        stage = omni.usd.get_context().get_stage()
        self.paths = [str(prim.GetPath()) for prim in stage.Traverse()
                      if prim.HasAPI(UsdPhysics.RigidBodyAPI)
                      and (str(prim.GetPath()).startswith("/World/Franka") or
                           str(prim.GetPath()) == "/World/ActiveObject")]
        if "/World/ActiveObject" not in self.paths or len(self.paths) < 3:
            raise RuntimeError(f"Expected robot and active object rigid bodies: {self.paths}")
        if not stage.Export(str(self.output / "base.usda")):
            raise RuntimeError("Factory stage snapshot failed")
        self.rigs = RigidPrim(paths=self.paths)
        self.tracks = {path: [] for path in self.paths}
        self.ready = True
        if self.rigs is not None:
            self.sample()
        print("FACTORY_CAPTURE_BEGIN", json.dumps({"paths": self.paths}), flush=True)

    def sample(self):
        positions, orientations = self.rigs.get_world_poses()
        position_values = positions.numpy()
        orientation_values = orientations.numpy()
        if len(position_values) != len(self.paths):
            raise RuntimeError("Batched rigid pose count differs from selected paths")
        for index, path in enumerate(self.paths):
            self.tracks[path].append((
                self.frames,
                [float(value) for value in position_values[index]],
                [float(value) for value in orientation_values[index]],
            ))

    def tick(self, steps):
        if not self.ready:
            return
        self.frames += int(steps)
        if self.frames >= self.next_sample:
            self.sample()
            self.next_sample = self.frames + 12  # about 5 Hz at 60 physics Hz
            if len(self.tracks[self.paths[0]]) % 20 == 0:
                print("FACTORY_CAPTURE_PROGRESS", self.frames, flush=True)

    def item(self, scene, object_id, class_name):
        if not self.ready or not object_id.startswith("object-"):
            return
        texture = scene._carrier_texture.GetInput("file").Get()
        texture_path = getattr(texture, "path", str(texture))
        matrix = scene._carrier_piece_transform.Get()
        self.items.append({"id": object_id, "class": class_name,
                           "frame": self.frames, "texture": texture_path,
                           "pieceMatrix": [[float(matrix[row][column])
                                            for column in range(4)] for row in range(4)]})
        print("FACTORY_CAPTURE_ITEM", object_id, class_name, self.frames, flush=True)

    def finish(self, result):
        from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

        if not self.ready or not self.items:
            raise RuntimeError("No factory poses or items captured")
        if self.rigs is not None:
            self.sample()
        raw = {"frames": self.frames, "paths": self.paths, "tracks": self.tracks,
               "items": self.items, "metrics": result["metrics"],
               "records": result["records"]}
        (self.output / "raw-capture.json").write_text(
            json.dumps(raw), encoding="utf-8")
        def pose_matrix(pos, quat):
            matrix = Gf.Matrix4d().SetRotate(
                Gf.Rotation(Gf.Quatd(quat[0], Gf.Vec3d(*quat[1:]))))
            matrix.SetTranslateOnly(Gf.Vec3d(*pos))
            return matrix
        stage = Usd.Stage.Open(str(self.output / "base.usda"))
        stage.SetTimeCodesPerSecond(60)
        stage.SetFramesPerSecond(60)
        stage.SetStartTimeCode(0)
        stage.SetEndTimeCode(self.frames)
        cache = UsdGeom.XformCache(Usd.TimeCode.Default())
        for path, track in self.tracks.items():
            if path == "/World/ActiveObject":
                continue  # Model mode hides this collision body; clones carry visuals.
            prim = stage.GetPrimAtPath(path)
            if not prim:
                raise RuntimeError(f"Missing robot link in stage snapshot: {path}")
            parent_world = cache.GetParentToWorldTransform(prim)
            ancestor = prim.GetParent()
            while ancestor and str(ancestor.GetPath()) != "/":
                if str(ancestor.GetPath()) in self.tracks:
                    break
                ancestor = ancestor.GetParent()
            ancestor_path = str(ancestor.GetPath()) if ancestor else None
            if ancestor_path not in self.tracks:
                ancestor_path = None
            if ancestor_path:
                ancestor_base = cache.GetLocalToWorldTransform(ancestor)
                fixed_offset = parent_world * ancestor_base.GetInverse()
            xform = UsdGeom.Xformable(prim)
            scale_ops = [op for op in xform.GetOrderedXformOps()
                         if op.GetOpType() == UsdGeom.XformOp.TypeScale]
            scale = scale_ops[0].Get() if len(scale_ops) == 1 else None
            xform.ClearXformOpOrder()
            translate = xform.AddTranslateOp(opSuffix="factoryReplay")
            orient = xform.AddOrientOp(opSuffix="factoryReplay")
            if scale is not None:
                xform.AddScaleOp(opSuffix="factoryReplay").Set(scale)
            for index, (frame, pos, quat) in enumerate(track):
                if ancestor_path:
                    _, ancestor_pos, ancestor_quat = self.tracks[ancestor_path][index]
                    dynamic_parent = fixed_offset * pose_matrix(ancestor_pos, ancestor_quat)
                else:
                    dynamic_parent = parent_world
                local = Gf.Transform(pose_matrix(pos, quat) * dynamic_parent.GetInverse())
                local_quat = local.GetRotation().GetQuat()
                local_orientation = Gf.Quatf(local_quat.GetReal(),
                                              Gf.Vec3f(local_quat.GetImaginary()))
                if index == 0:
                    translate.Set(local.GetTranslation())
                    orient.Set(local_orientation)
                translate.Set(local.GetTranslation(), frame)
                orient.Set(local_orientation, frame)

        source_carrier = stage.GetPrimAtPath("/World/InspectionCarrier")
        if not source_carrier:
            raise RuntimeError("Model carrier visual missing from snapshot")
        UsdGeom.Imageable(source_carrier).MakeInvisible()
        UsdGeom.Xform.Define(stage, "/World/RecordedItems")
        active = self.tracks["/World/ActiveObject"]
        for index, item in enumerate(self.items):
            path = f"/World/RecordedItems/Item{index:03d}"
            if not Sdf.CopySpec(stage.GetRootLayer(), "/World/InspectionCarrier",
                                stage.GetRootLayer(), path):
                raise RuntimeError(f"Could not clone factory visual: {path}")
            root = stage.GetPrimAtPath(path)
            UsdGeom.Imageable(root).MakeVisible()
            cheese = stage.GetPrimAtPath(path + "/Cheese")
            plate = stage.GetPrimAtPath(path + "/Plate")
            UsdShade.MaterialBindingAPI(cheese).Bind(
                UsdShade.Material(stage.GetPrimAtPath(path + "/CheeseMaterial")))
            UsdShade.MaterialBindingAPI(plate).Bind(
                UsdShade.Material(stage.GetPrimAtPath(path + "/PlateMaterial")))
            piece = UsdGeom.Xformable(cheese)
            for op in piece.GetOrderedXformOps():
                if op.GetOpType() == UsdGeom.XformOp.TypeTransform:
                    op.Set(Gf.Matrix4d(*[value for row in item["pieceMatrix"] for value in row]))
                    break
            for child in Usd.PrimRange(root):
                if child.IsA(UsdShade.Shader):
                    shader = UsdShade.Shader(child)
                    if str(shader.GetIdAttr().Get()) == "UsdUVTexture":
                        shader.GetInput("file").Set(Sdf.AssetPath(item["texture"]))
            xform = UsdGeom.Xformable(root)
            xform.ClearXformOpOrder()
            translate = xform.AddTranslateOp(opSuffix="factoryReplay")
            parked = Gf.Vec3d(15 + index, 0, 0)
            translate.Set(parked)
            start = item["frame"]
            end = self.items[index + 1]["frame"] if index + 1 < len(self.items) else self.frames + 1
            for frame, pos, _ in active:
                value = (Gf.Vec3d(pos[0], pos[1], pos[2] - 0.02575)
                         if start <= frame < end else parked)
                translate.Set(value, frame)

        # Isaac's built-in ground and Franka assets include MDL-only materials.
        # The strict v1 glTF path requires a PreviewSurface for every bound mesh.
        # Replace those bindings in the exported snapshot only; the project and
        # live Isaac stage remain untouched.
        converted_materials = []
        for prim in stage.Traverse():
            if not prim.IsA(UsdGeom.Gprim):
                continue
            material, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
            if not material:
                continue
            shaders = [str(UsdShade.Shader(child).GetIdAttr().Get())
                       for child in material.GetPrim().GetChildren()
                       if child.IsA(UsdShade.Shader)]
            if "UsdPreviewSurface" in shaders:
                continue
            material_path = str(material.GetPath())
            if material_path in converted_materials:
                continue
            preview = UsdShade.Shader.Define(stage, material_path + "/WebPreview")
            preview.CreateIdAttr("UsdPreviewSurface")
            preview.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
                Gf.Vec3f(0.68, 0.69, 0.70))
            preview.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.82)
            material.CreateSurfaceOutput().ConnectToSource(
                preview.ConnectableAPI(), "surface")
            for child in list(material.GetPrim().GetChildren()):
                if child.IsA(UsdShade.Shader) and str(
                        UsdShade.Shader(child).GetIdAttr().Get()) != "UsdPreviewSurface":
                    child.SetActive(False)
            converted_materials.append(material_path)
        print("FACTORY_CAPTURE_MATERIAL_FALLBACK", json.dumps(converted_materials), flush=True)

        recorded = self.output / "recorded_scene.usda"
        if not stage.GetRootLayer().Export(str(recorded)):
            raise RuntimeError("Could not save full factory recording")
        summary = {"frames": self.frames, "durationSeconds": self.frames / 60,
                   "sampleCount": len(active), "rigidPaths": self.paths,
                   "items": self.items, "metrics": result["metrics"],
                   "records": result["records"]}
        (self.output / "capture-summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8")
        print("FACTORY_CAPTURE_DONE", json.dumps({
            "frames": self.frames, "samples": len(active),
            "items": len(self.items), "durationSeconds": self.frames / 60,
            "recorded": str(recorded)}), flush=True)


async def _run():
    import omni.kit.app
    import isaacsim.core.experimental.utils.app as app_utils
    from sim.factory.config import FactoryConfig, load_config
    from sim.factory import run_factory
    from sim.factory.scene import IsaacFactoryScene

    manager = omni.kit.app.get_app().get_extension_manager()
    manager.set_extension_enabled_immediate("isaacsim.robot_motion.examples", True)
    max_objects = int(os.environ.get("FACTORY_CAPTURE_OBJECTS", "1"))
    tag = os.environ.get("FACTORY_CAPTURE_TAG", str(max_objects))
    output = Path(f"/work/runs/factory-model-capture-{tag}")
    capture = Capture(output)
    FactoryConfig.output_root = property(lambda self: output / "runtime-output")
    original_wait = run_factory._wait_frames
    async def observed_wait(scene, app_utilities, count):
        capture.begin()
        return await original_wait(scene, app_utilities, count)
    run_factory._wait_frames = observed_wait
    original_update = app_utils.update_app_async
    async def observed_update(*args, **kwargs):
        result = await original_update(*args, **kwargs)
        steps = kwargs.get("steps", args[0] if args else 1)
        capture.tick(steps)
        return result
    app_utils.update_app_async = observed_update
    original_set_object = IsaacFactoryScene.set_object
    def observed_set_object(scene, object_id, class_name, position, **kwargs):
        result = original_set_object(scene, object_id, class_name, position, **kwargs)
        capture.item(scene, object_id, class_name)
        return result
    IsaacFactoryScene.set_object = observed_set_object
    try:
        result = await run_factory.run(load_config("/project/sim/factory/config.yaml"),
                                       "model", max_objects=max_objects,
                                       cleanup=False)
        capture.finish(result)
    except BaseException as error:
        traceback.print_exc()
        print("FACTORY_CAPTURE_ERROR", repr(error), flush=True)
        os._exit(1)
    os._exit(0)


if os.environ.get("FACTORY_CAPTURE_OFFLINE") != "1":
    asyncio.ensure_future(_run())
