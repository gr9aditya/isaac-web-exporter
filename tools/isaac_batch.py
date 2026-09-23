"""Run several isolated exporter fixtures under one Isaac SimulationApp startup."""

import argparse
from pathlib import Path

from isaacsim import SimulationApp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("configs", nargs="+", type=Path)
    args = parser.parse_args()
    app = SimulationApp({"headless": True, "renderer": "RaytracedLighting"})
    try:
        from isaac_web_exporter.export import run

        failed = False
        for config in args.configs:
            print(f"BATCH_START {config}", flush=True)
            ok = run(config, app=app)
            print(f"BATCH_RESULT {config} {'PASS' if ok else 'FAIL'}", flush=True)
            failed |= not ok
        return 1 if failed else 0
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())
