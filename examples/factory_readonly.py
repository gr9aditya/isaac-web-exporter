"""Read-only factory scene probe; all output belongs to the exporter workspace.

This authors the real factory layout and robot, then drives one short conveyor
segment. It does not run camera initialization or the pick/place controller.
"""

import sys
from pathlib import Path


def build(stage, app, config):
    root = Path(config["project_root"]).resolve()
    if not (root / "sim" / "factory" / "scene.py").is_file():
        raise FileNotFoundError(f"Factory source missing at read-only mount: {root}")
    sys.path.insert(0, str(root))

    from sim.factory.config import load_config
    from sim.factory.scene import IsaacFactoryScene

    import omni.kit.app
    manager = omni.kit.app.get_app().get_extension_manager()
    manager.set_extension_enabled_immediate("isaacsim.robot_motion.examples", True)
    scene = IsaacFactoryScene(load_config(), classifier_mode="showcase")
    scene.setup_scene()
    app.update()
    belt = scene.config.section("belt")
    spawn = tuple(float(value) for value in belt["spawn_position"])
    scene.set_object("web-export-probe", "hard_cheese", spawn)
    speed = float(belt["speed_mps"])
    hz = float(config.get("simulation_hz", 60))

    def on_step(step, app):
        position = (spawn[0], spawn[1] + speed * step / hz, spawn[2])
        scene.move_object(position)

    return {"on_step": on_step}
