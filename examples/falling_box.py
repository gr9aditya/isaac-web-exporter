"""Fixture one: a single rigid box above a static floor."""

from pxr import Gf, UsdGeom, UsdPhysics
from isaacsim.core.experimental.prims import GeomPrim, RigidPrim
from fixture_common import box


def build(stage, app, config):
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    UsdGeom.Scope.Define(stage, "/World/Looks")
    floor = box(stage, "/World/Floor", (4, 4, 0.15), (0.45, 0.55, 0.65), (0, 0, -0.075))
    UsdPhysics.CollisionAPI.Apply(floor.GetPrim())
    box(stage, "/World/FallingBox", (0.5, 0.5, 0.5), (0.95, 0.2, 0.12), (0, 0, 2))
    GeomPrim(paths="/World/FallingBox", apply_collision_apis=True)
    RigidPrim(paths="/World/FallingBox")
    return {}
