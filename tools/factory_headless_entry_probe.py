"""Isolated, read-only factory runtime probe under the service's Kit entrypoint."""

import asyncio
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, "/project")


async def _run():
    import omni.kit.app
    manager = omni.kit.app.get_app().get_extension_manager()
    manager.set_extension_enabled_immediate("isaacsim.robot_motion.examples", True)
    from sim.factory.config import FactoryConfig, load_config
    from sim.factory.run_factory import run

    classifier = os.environ.get("FACTORY_PROBE_CLASSIFIER", "showcase")
    max_objects = int(os.environ.get("FACTORY_PROBE_MAX_OBJECTS", "1"))
    own_output = Path(f"/work/runs/factory-{classifier}-{max_objects}-probe/output")
    FactoryConfig.output_root = property(lambda self: own_output)
    try:
        result = await run(load_config("/project/sim/factory/config.yaml"),
                           classifier, max_objects=max_objects, cleanup=False)
        print("FACTORY_HEADLESS_PROBE", result["metrics"], flush=True)
    except BaseException as error:
        traceback.print_exc()
        print("FACTORY_HEADLESS_PROBE_ERROR", repr(error), flush=True)
        os._exit(1)
    os._exit(0)


asyncio.ensure_future(_run())
