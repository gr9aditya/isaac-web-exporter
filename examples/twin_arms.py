"""Owned test: two rigid prims share the leaf name 'Arm'."""

from pxr import UsdGeom, UsdPhysics
from isaacsim.core.experimental.prims import GeomPrim, RigidPrim
from fixture_common import box


def build(stage, app, config):
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    UsdGeom.Scope.Define(stage, "/World/Looks")
    floor = box(stage, "/World/Floor", (5, 4, 0.15), (0.42, 0.46, 0.51), (0, 0, -0.075))
    UsdPhysics.CollisionAPI.Apply(floor.GetPrim())
    for branch, x, color in [
        ("Left", -1.0, (0.84, 0.23, 0.18)),
        ("Right", 1.0, (0.18, 0.61, 0.88)),
    ]:
        path = f"/World/{branch}/Arm"
        box(stage, path, (0.5, 0.5, 0.5), color, (x, 0, 1.7))
        GeomPrim(paths=path, apply_collision_apis=True)
        RigidPrim(paths=path)
    return {}
