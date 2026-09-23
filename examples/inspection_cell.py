"""Fixture two: two rigid payloads plus authored arm and carrier animation."""

from pxr import Gf, UsdGeom, UsdPhysics
from isaacsim.core.experimental.prims import GeomPrim, RigidPrim
from fixture_common import box


def build(stage, app, config):
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    UsdGeom.Scope.Define(stage, "/World/Looks")
    floor = box(stage, "/World/Floor", (6, 5, 0.15), (0.29, 0.34, 0.40), (0, 0, -0.075))
    UsdPhysics.CollisionAPI.Apply(floor.GetPrim())
    box(stage, "/World/Robot/Base", (0.65, 0.65, 1.1), (0.18, 0.37, 0.77), (-1.6, 0, 0.55))
    pivot = UsdGeom.Xform.Define(stage, "/World/Robot/Pivot")
    pivot.AddTranslateOp().Set(Gf.Vec3d(-1.6, 0, 1.15))
    turn = pivot.AddRotateZOp()
    box(stage, "/World/Robot/Pivot/Arm", (1.8, 0.20, 0.20), (0.22, 0.63, 0.86), (0.9, 0, 0))
    box(stage, "/World/Robot/Pivot/Tool", (0.22, 0.35, 0.50), (0.95, 0.75, 0.18), (1.8, 0, -0.18))
    carrier = UsdGeom.Xform.Define(stage, "/World/Carrier")
    travel = carrier.AddTranslateOp()
    travel.Set(Gf.Vec3d(0.45, -1.25, 0))
    box(stage, "/World/Carrier/Tray", (0.72, 0.72, 0.12), (0.35, 0.70, 0.45), (0, 0, 0.55))
    for tick in range(61):
        turn.Set(-40 + 80 * tick / 60, tick)
        travel.Set(Gf.Vec3d(0.45 + 0.9 * tick / 60, -1.25, 0), tick)
    for path, size, color, center in [
        ("/World/PayloadA", (0.32, 0.32, 0.32), (0.90, 0.20, 0.22), (0.55, 0.55, 2.0)),
        ("/World/PayloadB", (0.44, 0.26, 0.28), (0.93, 0.54, 0.12), (1.45, 0.45, 2.6)),
    ]:
        box(stage, path, size, color, center)
        GeomPrim(paths=path, apply_collision_apis=True)
        RigidPrim(paths=path)
    return {}
