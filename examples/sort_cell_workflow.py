"""Owned 30-second scripted sorting demo with fixed topology.

The transforms are authored USD animation, not Isaac physics/controller output.
This is an acceptance fixture for a complete browser workflow and nested motion.
"""

import math

from pxr import Gf, UsdGeom
from fixture_common import box


def interpolate(a, b, fraction):
    return a + (b - a) * fraction


def between(t, begin, end):
    return max(0.0, min(1.0, (t - begin) / (end - begin)))


def build(stage, app, config):
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    UsdGeom.Scope.Define(stage, "/World/Looks")

    box(stage, "/World/Floor", (8, 5, 0.1), (0.32, 0.39, 0.45), (0, 0, -0.05))
    box(stage, "/World/Conveyor", (5.5, 0.8, 0.22), (0.18, 0.28, 0.34), (0, -1, 0.22))
    box(stage, "/World/InspectionStation", (0.8, 0.9, 0.65),
        (0.18, 0.65, 0.75), (-1.2, 0.6, 0.325))
    box(stage, "/World/OutputBin", (1.4, 1.1, 0.28),
        (0.21, 0.57, 0.40), (2.1, 0.8, 0.14))

    sorter = UsdGeom.Xform.Define(stage, "/World/Sorter")
    sorter.AddTranslateOp().Set(Gf.Vec3d(0, 0.7, 0.75))
    box(stage, "/World/Sorter/Base", (0.75, 0.75, 1.5),
        (0.16, 0.38, 0.70), (0, 0, 0))
    shoulder = UsdGeom.Xform.Define(stage, "/World/Sorter/Shoulder")
    shoulder.AddTranslateOp().Set(Gf.Vec3d(0, 0, 0.75))
    shoulder_op = shoulder.AddRotateZOp()
    box(stage, "/World/Sorter/Shoulder/UpperLink", (1.7, 0.22, 0.22),
        (0.82, 0.83, 0.87), (0.85, 0, 0))
    elbow = UsdGeom.Xform.Define(stage, "/World/Sorter/Shoulder/Elbow")
    elbow.AddTranslateOp().Set(Gf.Vec3d(1.7, 0, 0))
    elbow_op = elbow.AddRotateZOp()
    box(stage, "/World/Sorter/Shoulder/Elbow/LowerLink", (1.1, 0.18, 0.18),
        (0.76, 0.78, 0.82), (0.55, 0, 0))
    wrist = UsdGeom.Xform.Define(stage, "/World/Sorter/Shoulder/Elbow/Wrist")
    wrist.AddTranslateOp().Set(Gf.Vec3d(1.1, 0, 0))
    wrist_op = wrist.AddRotateZOp()
    box(stage, "/World/Sorter/Shoulder/Elbow/Wrist/Gripper", (0.38, 0.32, 0.35),
        (0.94, 0.68, 0.19), (0.15, 0, -0.11))

    payload_a = UsdGeom.Xform.Define(stage, "/World/Products/PartA")
    payload_b = UsdGeom.Xform.Define(stage, "/World/Products/PartB")
    a_op = payload_a.AddTranslateOp()
    b_op = payload_b.AddTranslateOp()
    box(stage, "/World/Products/PartA/Body", (0.34, 0.34, 0.34),
        (0.94, 0.27, 0.18), (0, 0, 0))
    box(stage, "/World/Products/PartB/Body", (0.28, 0.28, 0.28),
        (0.92, 0.54, 0.18), (0, 0, 0))

    fps = int(config.get("fps", 30))
    duration = float(config.get("duration_seconds", 30))
    for frame in range(round(fps * duration) + 1):
        t = frame / fps
        belt = between(t, 0, 9)
        inspect = between(t, 9, 14)
        transfer = between(t, 14, 21)
        place = between(t, 21, 25)
        return_home = between(t, 25, 30)

        if t < 9:
            a_position = (interpolate(-2.3, -1.15, belt), -1, 0.5)
        elif t < 14:
            a_position = (-1.15, interpolate(-1, 0.6, inspect),
                          interpolate(0.5, 1.05, inspect))
        elif t < 21:
            a_position = (interpolate(-1.15, 2.1, transfer),
                          interpolate(0.6, 0.8, transfer), 1.05)
        else:
            a_position = (2.1, 0.8, interpolate(1.05, 0.47, place))
        b_position = (interpolate(-2.6, 1.6, between(t, 3, 27)), -1.1, 0.5)
        a_op.Set(Gf.Vec3d(*a_position), frame)
        b_op.Set(Gf.Vec3d(*b_position), frame)

        sweep = math.sin(math.pi * between(t, 9, 25))
        shoulder_angle = interpolate(-42, 33, between(t, 9, 21))
        shoulder_angle = interpolate(shoulder_angle, -42, return_home)
        shoulder_op.Set(shoulder_angle, frame)
        elbow_op.Set(-35 + 40 * sweep, frame)
        wrist_op.Set(20 * math.sin(t / 30 * 2 * math.pi), frame)
        if frame == 0:
            # Asset Converter uses default opinions for GLB node transforms.
            # Time samples alone intermittently produced uninitialized values
            # for the two payload nodes in Isaac Sim 6.1.
            a_op.Set(Gf.Vec3d(*a_position))
            b_op.Set(Gf.Vec3d(*b_position))
            shoulder_op.Set(shoulder_angle)
            elbow_op.Set(-35 + 40 * sweep)
            wrist_op.Set(20 * math.sin(t / 30 * 2 * math.pi))
    return {}
