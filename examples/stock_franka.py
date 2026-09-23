"""Technical compatibility test using Isaac's stock Franka asset; do not redistribute it."""

from pxr import Gf, UsdGeom, UsdPhysics
import isaacsim.core.experimental.utils.stage as stage_utils
from isaacsim.core.experimental.prims import Articulation
from isaacsim.storage.native import get_assets_root_path
from fixture_common import box


def build(stage, app, config):
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    UsdGeom.Scope.Define(stage, "/World/Looks")
    ground = box(stage, "/World/Floor", (4, 4, 0.1), (0.4, 0.43, 0.48), (0, 0, -0.05))
    UsdPhysics.CollisionAPI.Apply(ground.GetPrim())
    root = get_assets_root_path()
    if not root:
        raise RuntimeError("Isaac stock asset root is unavailable")
    asset = root + "/Isaac/Robots_Multiphysics/FrankaRobotics/FrankaPanda/franka/franka.usda"
    stage_utils.add_reference_to_stage(usd_path=asset, path="/World/Franka",
                                       variants=[("Gripper", "alternatefinger"), ("Mesh", "quality")])
    robot = Articulation("/World/Franka")
    robot.set_default_state(dof_positions=[0.0] * 9)

    def on_step(step, app):
        if step == 10:
            robot.set_dof_position_targets([0.4, -0.5, 0.1, -1.5, 0.3, 1.3, 0.4, 0.0, 0.0])

    return {"on_step": on_step}
