"""Compare browser poses with the independently authored fixture equations."""

import json
import math
import os
from pathlib import Path


root = Path(__file__).resolve().parents[1]
source = root / os.environ.get("WORKFLOW_BROWSER_JSON", "runs/v1/sort-workflow-browser.json")
target = root / os.environ.get("WORKFLOW_COMPARISON_JSON", "runs/v1/sort-workflow-comparison.json")
observed = json.loads(source.read_text(encoding="utf-8"))["samples"]


def between(time, begin, end):
    return max(0.0, min(1.0, (time - begin) / (end - begin)))


def interpolate(a, b, fraction):
    return a + (b - a) * fraction


def expected(time):
    belt = between(time, 0, 9)
    inspect = between(time, 9, 14)
    transfer = between(time, 14, 21)
    place = between(time, 21, 25)
    return_home = between(time, 25, 30)
    if time < 9:
        a = (interpolate(-2.3, -1.15, belt), -1, 0.5)
    elif time < 14:
        a = (-1.15, interpolate(-1, 0.6, inspect), interpolate(0.5, 1.05, inspect))
    elif time < 21:
        a = (interpolate(-1.15, 2.1, transfer), interpolate(0.6, 0.8, transfer), 1.05)
    else:
        a = (2.1, 0.8, interpolate(1.05, 0.47, place))
    b = (interpolate(-2.6, 1.6, between(time, 3, 27)), -1.1, 0.5)
    sweep = math.sin(math.pi * between(time, 9, 25))
    shoulder = interpolate(-42, 33, between(time, 9, 21))
    shoulder = interpolate(shoulder, -42, return_home)
    elbow = -35 + 40 * sweep
    wrist = 20 * math.sin(time / 30 * 2 * math.pi)
    theta = math.radians(shoulder)
    phi = math.radians(elbow)
    elbow_world = (1.7 * math.cos(theta), 0.7 + 1.7 * math.sin(theta), 1.5)
    wrist_world = (elbow_world[0] + 1.1 * math.cos(theta + phi),
                   elbow_world[1] + 1.1 * math.sin(theta + phi), 1.5)
    # The installed converter changes Z-up USD to Y-up glTF: (x, z, -y).
    viewer = lambda position: (position[0], position[2], -position[1])
    return {
        "/World/Products/PartA": (viewer(a), 0, 0),
        "/World/Products/PartB": (viewer(b), 0, 0),
        "/World/Sorter/Shoulder": (viewer((0, 0.7, 1.5)), shoulder, shoulder),
        "/World/Sorter/Shoulder/Elbow": (viewer(elbow_world), elbow, shoulder + elbow),
        "/World/Sorter/Shoulder/Elbow/Wrist": (viewer(wrist_world), wrist,
                                                 shoulder + elbow + wrist),
    }


maximum_position = 0.0
maximum_orientation = 0.0
maximum_world_orientation = 0.0
maximum_scale = 0.0
worst_position = None
worst_orientation = None
for sample in observed:
    reference = expected(sample["time"])
    for node in sample["nodes"]:
        position, degrees, world_degrees = reference[node["id"]]
        error = math.dist(node["worldPosition"], position)
        if error > maximum_position:
            maximum_position, worst_position = error, (sample["time"], node["id"])
        radians = math.radians(degrees) / 2
        target_quaternion = (0, 0, math.sin(radians), math.cos(radians))
        actual = node["localQuaternion"]
        dot = min(1.0, abs(sum(a * b for a, b in zip(actual, target_quaternion))))
        angle_error = math.degrees(2 * math.acos(dot))
        if angle_error > maximum_orientation:
            maximum_orientation, worst_orientation = angle_error, (sample["time"], node["id"])
        world_radians = math.radians(world_degrees) / 2
        # Z-up to Y-up is a -90-degree X rotation at the converted scene root.
        root = (-math.sqrt(0.5), 0, 0, math.sqrt(0.5))
        rz = (0, 0, math.sin(world_radians), math.cos(world_radians))
        x, y, z, w = root
        a, b, c, d = rz
        target_world = (w*a + x*d + y*c - z*b,
                        w*b - x*c + y*d + z*a,
                        w*c + x*b - y*a + z*d,
                        w*d - x*a - y*b - z*c)
        world_dot = min(1.0, abs(sum(a * b for a, b in zip(
            node["worldQuaternion"], target_world))))
        maximum_world_orientation = max(maximum_world_orientation,
                                        math.degrees(2 * math.acos(world_dot)))
        maximum_scale = max(maximum_scale,
                            max(abs(value - 1) for value in node["worldScale"]))

result = {
    "samples": len(observed), "objectsPerSample": len(observed[0]["nodes"]),
    "maximumPositionErrorMeters": maximum_position,
    "maximumOrientationErrorDegrees": maximum_orientation,
    "maximumWorldOrientationErrorDegrees": maximum_world_orientation,
    "maximumScaleError": maximum_scale,
    "worstPosition": worst_position, "worstOrientation": worst_orientation,
    "positionToleranceMeters": 0.001, "orientationToleranceDegrees": 0.5,
    "status": "PASS" if maximum_position <= 0.001 and maximum_orientation <= 0.5
              and maximum_world_orientation <= 0.5 and maximum_scale <= 0.001 else "FAIL",
}
target.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
if result["status"] != "PASS":
    raise SystemExit(1)
