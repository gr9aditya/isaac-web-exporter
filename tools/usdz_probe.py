"""Package the working time-sampled fixture with Isaac's OpenUSD runtime."""

import json
import argparse
from pathlib import Path

from isaacsim import SimulationApp

app = SimulationApp({"headless": True})
status = 1
try:
    from pxr import Sdf, Usd, UsdUtils

    parser = argparse.ArgumentParser()
    parser.add_argument('source', nargs='?', default='/work/runs/falling-box-final/recorded_scene.usda')
    parser.add_argument('output', nargs='?', default='/work/runs/usdz-probe')
    parser.add_argument('--inspect-prim', default='/World/FallingBox')
    args = parser.parse_args()
    source = Path(args.source)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    destination = output / 'scene.usdz'
    created = bool(UsdUtils.CreateNewUsdzPackage(Sdf.AssetPath(str(source)), str(destination)))
    stage = Usd.Stage.Open(str(destination)) if created else None
    prim = stage.GetPrimAtPath(args.inspect_prim) if stage else None
    info = {
        'created': created,
        'bytes': destination.stat().st_size if destination.exists() else 0,
        'reopened': bool(stage),
        'start': stage.GetStartTimeCode() if stage else None,
        'end': stage.GetEndTimeCode() if stage else None,
        'samples': prim.GetAttribute('xformOp:translate:replay').GetNumTimeSamples() if prim else None,
        'source': str(source),
    }
    (output / 'report.json').write_text(json.dumps(info, indent=2))
    print('USDZ_PROBE', json.dumps(info), flush=True)
    status = 0 if created and stage and info['samples'] else 1
except Exception as exc:
    import traceback
    traceback.print_exc()
    print('USDZ_PROBE_ERROR', repr(exc), flush=True)
finally:
    app.close(exit_code=status)
