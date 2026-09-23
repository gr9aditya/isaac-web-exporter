# Isaac Web Exporter v1 (local candidate)

Export an Isaac Sim stage and its recorded transform motion to a self-hostable
browser package. The bundled Three.js player provides Start/Pause/Restart,
scrubbing, frame stepping, speed and loop controls, camera navigation, object
inspection, and a guided-demo editor. The recipient needs only static HTTP
hosting and a WebGL browser. Isaac, Docker, an RTX card, a live server, and an
LLM are not required at playback time. The recording does not run Isaac
physics, project controllers, sensors, or ROS in the browser.

This repository is local/private while its owner chooses a source license.
Do not publish the code or exported third-party assets without reviewing rights.
The v1 checklist and test evidence live in [V1_ACCEPTANCE.md](V1_ACCEPTANCE.md).

## Build and install

The tested exporter runs in Isaac Sim 6.1 (image digest and tool versions are
in [toolchain.lock.json](toolchain.lock.json)). Build tools require Python 3.12+
and Node/npm; recipients of a built package need neither Node nor Isaac.

```bash
python tools/build_release.py
```

The command stages a clean source copy, runs `npm ci` using
`web/player/package-lock.json`, builds Vite with relative URLs, and creates a
wheel under `dist/`. It checks for exactly one generated JavaScript and CSS
asset. The wheel includes the player, schemas, notices, and customization kit.
For editing the player locally, `python tools/build_player.py` also refreshes
the checked-in bundled template. Install the wheel into a compatible Isaac
Python environment; the exporter user does **not** need to build JavaScript:

```bash
/isaac-sim/python.sh -m pip install --no-deps /path/to/isaac_web_exporter-1.0.0-py3-none-any.whl
```

The remote Docker image in the lockfile is a reproducible development option,
not a runtime requirement for browser recipients. Do not install a separate
OpenUSD Python distribution into Isaac's environment.

## Export an owned example

Copy `tests/v1_sort_cell_guided.json` and change `bootstrap`, `experience` and
`output_dir` to paths visible inside your Isaac environment. The example
bootstrap `examples/sort_cell_workflow.py` authors a 30-second sorting scene;
its motion is scripted USD transform animation, not live physics. Its own
`fixture_common.py` must be alongside it. Use a **new** output directory—the
exporter refuses overwrite.

```bash
PYTHONPATH=/path/to/repo/src /isaac-sim/python.sh -m isaac_web_exporter.export \
  --config /path/to/repo/tests/v1_sort_cell_guided.json
python src/isaac_web_exporter/validate_package.py /path/to/output/package
python -m http.server 8000 --directory /path/to/output/package
```

Open `http://127.0.0.1:8000/`. You may instead install the wheel and use
`isaac-web-package-check /path/to/output/package`. The output also contains
`package.zip`, the disposable conversion stage, an unoptimized GLB when using
`quality_preset: compact`, a progress file, and an exporter report. Only
`package/` or its ZIP is needed by a recipient. Serve with HTTP, including
from a nested URL; direct `file://` loading is unsupported.

Three source forms share the core exporter:

- `bootstrap`: a Python module with `build(stage, app, config)`. It may return
  `{"on_step": callback}` to drive physics/controller updates. Capture is
  scoped to `capture_roots` and configured by duration, simulation rate,
  sample interval and FPS.
- `input_usd`: a saved USD with authored animation. Use `capture_roots: []`;
  the exporter preserves authored time samples rather than running physics.
- Already-loaded stage: call `run(config_path, app=app, stage=stage,
  on_step=callback)` from Isaac. The caller retains app/stage ownership. See
  `tests/loaded_stage_entry.py`.

Set `mode: static` for an unanimated scene. `quality_preset: compact` is an
opt-in, bounded simplification of linear transform keys. The standard preset
keeps all converter output keys. `camera` and `camera_bookmarks` use Y-up
viewer-space coordinates.

The Isaac extension in `extensions/isaac.web.exporter/` opens an **Isaac Replay
Exporter** panel with source, selected roots, duration, sample rate, quality,
output, static mode, preflight, presets, cancellation and local preview. Add
this extension folder to Isaac's extension search path and enable it. The panel
starts an isolated child Isaac export so Kit can continue repainting while it
records. The browser preview binds to `127.0.0.1` only.

## Package contract and customization

`scene.glb` is authoritative for geometry and recorded animation;
`manifest.json`, `scene-map.json`, `compatibility-report.json` and
`experience.json` are versioned metadata. The package ships readable schemas
and `LLM-HANDOFF.md`, plus three optional customization examples under
`customization/`. The default player works without an LLM. The public
`window.isaacReplay` API is documented in the package's customization guide.
Download an edited `experience.json` from the browser editor and replace that
file in the package to share a guided tour without re-exporting the GLB.

The v1 loader accepts unchanged `alpha-0.1` v0 packages for basic playback.
Their catalog covers only v0 captured objects and they have no packaged tour
metadata. Unknown schema versions fail. The offline validator checks relative
HTML resources, GLB integrity/hash, identities, sample times, schemas and
presentation references. Run it after customizing a package.

## Supported scope and troubleshooting

Supported motion is fixed-topology rigid/link transforms and authored USD
transform animation with static material bindings. Non-transform animated
properties, spawn/despawn, deformables, particles, animated material binding,
and arbitrary RTX/MDL appearance are outside v1. Missing visual dependencies,
required moving objects omitted by conversion, absent meshes/animation in
recorded mode, external GLB URLs and invalid metadata fail export/validation.
The compatibility report records approximations. A large scene may render
slowly on integrated graphics; the performance result in the acceptance file
applies to the owned 30-second sorting scene, not every factory.

If the panel preflight fails, check that the source path exists inside the
Isaac environment, that the output path is new, and that the running app is
Isaac 6.1. If conversion fails, inspect `report.json` and check that required
textures and referenced USD layers resolve. If a browser shows **Load failed**,
run the package validator, use HTTP rather than `file://`, check the browser
console, and verify all files from the ZIP were copied. A package with a
different schema version requires an explicit migration.

See [ROUTE_DECISION.md](ROUTE_DECISION.md) for why v1 uses GLB/Three.js rather
than USDZ/Web View, [V0_ACCEPTANCE.md](V0_ACCEPTANCE.md) for the earlier v0,
and [V1_IMPLEMENTATION_PLAN.md](V1_IMPLEMENTATION_PLAN.md) for all v1 gates.
