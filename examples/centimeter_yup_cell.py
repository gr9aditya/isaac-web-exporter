"""Owned Y-up centimeter fixture with nested rotation-only motion."""

from pxr import Gf, UsdGeom
from fixture_common import box


def build(stage, app, config):
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 0.01)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    UsdGeom.Scope.Define(stage, "/World/Looks")
    box(stage, "/World/Floor", (300, 10, 220), (0.35, 0.42, 0.5), (0, -5, 0))
    cell = UsdGeom.Xform.Define(stage, "/World/Cell")
    cell.AddTranslateOp().Set(Gf.Vec3d(50, 0, -35))
    cell.AddRotateYOp().Set(20)
    shoulder = UsdGeom.Xform.Define(stage, "/World/Cell/Shoulder")
    shoulder.AddTranslateOp().Set(Gf.Vec3d(0, 85, 0))
    shoulder_rotation = shoulder.AddRotateYOp()
    box(stage, "/World/Cell/Shoulder/Body", (80, 12, 12),
        (0.9, 0.5, 0.15), (40, 0, 0))
    tool = UsdGeom.Xform.Define(stage, "/World/Cell/Shoulder/Tool")
    tool.AddTranslateOp().Set(Gf.Vec3d(80, 0, 0))
    tool_rotation = tool.AddRotateYOp()
    box(stage, "/World/Cell/Shoulder/Tool/Gripper", (25, 20, 20),
        (0.14, 0.7, 0.8), (12, 0, 0))
    fps = int(config.get("fps", 30))
    duration = float(config.get("duration_seconds", 2))
    for frame in range(round(fps * duration) + 1):
        fraction = frame / (fps * duration)
        shoulder_value = 60 * fraction
        tool_value = -30 * fraction
        shoulder_rotation.Set(shoulder_value, frame)
        tool_rotation.Set(tool_value, frame)
        if frame == 0:
            shoulder_rotation.Set(shoulder_value)
            tool_rotation.Set(tool_value)
    return {}
