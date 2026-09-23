"""Read-only one-item probe of the project's actual asynchronous factory run."""

import asyncio
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, "/project")
from isaacsim import SimulationApp


app = SimulationApp({"headless": True},
                    experience="/isaac-sim/apps/isaacsim.exp.full.streaming.kit")
status = 1
try:
    import omni.kit.app
    manager = omni.kit.app.get_app().get_extension_manager()
    manager.set_extension_enabled_immediate("isaacsim.robot_motion.examples", True)
    from sim.factory.config import FactoryConfig, load_config
    from sim.factory.run_factory import run

    own_output = Path("/work/runs/factory-runtime-probe/output")
    FactoryConfig.output_root = property(lambda self: own_output)
    configuration = load_config("/project/sim/factory/config.yaml")
    future = asyncio.ensure_future(run(configuration, "showcase", max_objects=1,
                                       cleanup=False))
    deadline = time.monotonic() + 600
    while not future.done() and app.is_running() and time.monotonic() < deadline:
        app.update()
    if not future.done():
        raise TimeoutError("Factory runtime did not complete within ten minutes")
    result = future.result()
    print("FACTORY_RUNTIME_PROBE", result["metrics"], flush=True)
    status = 0
except BaseException as error:
    traceback.print_exc()
    print("FACTORY_RUNTIME_PROBE_ERROR", repr(error), flush=True)
finally:
    app.close(exit_code=status)
