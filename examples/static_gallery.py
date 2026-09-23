"""Owned fixed scene for explicit static package acceptance."""

from pxr import UsdGeom
from fixture_common import box


def build(stage, app, config):
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    UsdGeom.Scope.Define(stage, "/World/Looks")
    box(stage, "/World/Table", (3, 2, 0.15), (0.28, 0.42, 0.56), (0, 0, -0.075))
    box(stage, "/World/Left/Part", (0.45, 0.45, 0.45), (0.87, 0.25, 0.19), (-0.7, 0, 0.25))
    box(stage, "/World/Right/Part", (0.45, 0.45, 0.45), (0.20, 0.76, 0.50), (0.7, 0, 0.25))
    return {}
