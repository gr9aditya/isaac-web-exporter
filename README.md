# Isaac browser exporter v0

Export a fixed-topology Isaac Sim scene and recorded rigid-body motion to a
self-hostable browser package. The package contains an animated GLB, a local
Three.js player, Start/Pause/Restart controls, orbit/pan/zoom navigation, a
manifest, a scene map, an LLM handoff guide, a compatibility report, and the
player license notice.
End users need ordinary static HTTP hosting and WebGL; they do not need Isaac
Sim, Docker, a live GPU server, or an RTX GPU. Playback does not run physics,
controllers, sensors, or ROS.

This v0 is a **scoped recorded-playback exporter**, not a universal converter
for every Isaac schema or material. The format decision and evidence are in
`ROUTE_DECISION.md` and `V0_ACCEPTANCE.md`. Outputs in `runs/` are local test
artifacts excluded from Git.

## Build the local player template

Node.js and npm are needed only to build the player, not by the end user. From
this repository:

```bash
cd checkpoint1/web
npm ci
npm run build
cd ../..
mkdir -p viewer-template-v0/THIRD_PARTY_LICENSES
cp -r checkpoint1/web/dist/. viewer-template-v0/
cp checkpoint1/web/public/THIRD_PARTY_LICENSES/three-MIT.txt viewer-template-v0/THIRD_PARTY_LICENSES/
```

The source and lockfile pin Three.js 0.185.0 and Vite 6.3.0. The build emits
relative asset URLs, so a generated package can be hosted under a URL subpath.
`toolchain.lock.json` records the tested Isaac image and artifact hashes.

## Run the exporter in Isaac

Use the tested Isaac 6.1 image digest in `toolchain.lock.json`, mount this repo
as `/work`, and run with Isaac's `python.sh`. The config supplies paths *inside*
the container. Choose a fresh `output_dir`; the exporter refuses to overwrite an
existing directory.

```bash
PYTHONPATH=/work/src /isaac-sim/python.sh -m isaac_web_exporter.export \
  --config /work/tests/v0_falling_box.json
```

The three supported input forms are:

- **Project bootstrap:** `bootstrap` names a Python file defining
  `build(stage, app, config)`. It constructs/loads the scene and may return
  `{"on_step": callback}` to drive each simulation update. `capture_roots`,
  `duration_seconds`, `simulation_hz`, `fps`, and `sample_every_updates` control
  capture. `examples/falling_box.py`, `examples/inspection_cell.py`, and
  `examples/factory_readonly.py` show separate adapters using the same exporter.
- **Saved USD:** `input_usd` opens a stage whose animation is already authored.
  Set `capture_roots` to `[]`; this mode preserves time samples and does not
  start physics capture. `tests/v0_saved_stage.json` is a tested example.
- **Already-loaded stage:** code running inside Isaac can call
  `run(config_path, app=app, stage=stage, on_step=callback)`. The caller owns the
  supplied app and stage; the exporter does not close them. This mode exports
  an independent stage copy and leaves the caller's stage metadata alone.
  `tests/loaded_stage_entry.py` is a tested example.

The exporter discovers `UsdPhysics.RigidBodyAPI` prims under selected roots,
samples world poses, writes explicit timed transforms to an export copy,
tessellates analytic cubes there, checks source dependencies, and converts with
the installed Isaac Asset Converter. It rejects missing required visual assets,
missing animation/meshes, absent moving-object channels, external GLB resources,
implausible transforms, and duplicate captured leaf names. Warnings identify
material types that still need visual inspection. An optional config `camera`
contains viewer-space `position` and `target` arrays; use it when a large ground
plane defeats automatic framing.

## Serve and validate the result

Successful output contains `package/`, `base.usda`, `recorded_scene.usda`,
`scene.glb`, and `report.json`. Copy only `package/` to ordinary static hosting,
or test locally:

```bash
python -m http.server 8000 --directory /path/to/output/package
```

Open `http://localhost:8000/`; opening `index.html` using `file://` is not
supported. The package is independently validated with standard Python:

```bash
python src/isaac_web_exporter/validate_package.py /path/to/output/package
```

The validator checks required files, HTML-relative resources, an animated
self-contained GLB, scene-map nodes, the successful compatibility report, and
the asset SHA-256 in the manifest. The end user's browser makes no external
runtime requests in the tested fixtures.

## Supported scope and limits

Verified inputs include two independent self-authored scenes, stock Franka
link motion, an authored saved USD, an already-loaded stage, and a read-only
probe of the real cheese-factory scene. The factory package records only a
two-second conveyor object movement, with static layout and Franka; it does
not claim to reproduce classification or pick-and-place. See
`FACTORY_PROBE_REPORT.md`.

The v0 assumes fixed topology and object population, static material binding,
and rigid/link transform motion or existing USD transform animation. Animated
visibility, spawn/despawn, deformables, particles, ROS, live controllers, and
arbitrary MDL/RTX appearance are outside this scope. Native USD instances,
complex moving-parent hierarchies, and unusual textures need project-specific
checks. The factory example reached about 8 fps on a software renderer; large
scenes may need optimization. Browser results are not a pixel-accurate Isaac RTX
render.

The player includes Three.js's MIT notice. Exported geometry and textures may
have separate rights; conversion does not grant redistribution permission.
Stock Franka and cheese-factory packages remain local technical artifacts and
were not published. Review source-asset terms before distributing a package.

`IMPLEMENTATION_PLAN.md` records the original plan; `ROUTE_DECISION.md` explains
the tested deviation to GLB. `V0_ACCEPTANCE.md` maps its acceptance gates to
measured evidence and remaining limits.
