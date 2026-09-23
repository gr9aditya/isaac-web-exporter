# Isaac browser exporter: first feasibility checkpoint

## Result

A generated Isaac Sim rigid-body scene was captured as 61 explicit pose samples over
two seconds, written to time-sampled USD, converted with the installed Isaac Asset
Converter to an animated GLB, and played in a self-hostable static browser package.
The browser shows the box falling onto a floor and provides Start, Pause, Restart,
orbit, pan, and zoom. This is recorded playback; the browser does not simulate physics.

This proves the main chain on **one simple, generated fixture**, not a reusable
exporter for arbitrary Isaac projects. No cheese-factory project was modified.

## Verified local evidence

- The isolated Isaac container reported `6.1.0-rc.26+release.49347.2d230af4.gl`,
  Kit `110.3.0`, and USD `25.11`. The pinned image digest, Python procedure, and
  recorder/converter calls are in `proof.py` and `output/checkpoint-report.json`.
- The recorder returned `RECORDING_SUCCESS`. Its USD file has 49 transform samples
  for the falling box, as inspected in `output/recorder-inspection.json`.
- Explicit Isaac rigid-body pose capture yielded 61 samples, 19 position changes,
  and a first/last height of 1.97275/0.25 meters. The resulting
  `output/recorded_scene.usda` contains the animation. Asset Converter returned
  `OmniConverterStatus.OK` and produced `output/scene.glb` (7,784 bytes).
- GLB inspection found two meshes, two materials, and one clip with animated
  translation and rotation channels. The animation duration in Three.js was 2 s.
- Production Vite build completed. The static player passed an automated Edge
  browser test using SwiftShader software rendering. Start advanced the object,
  Pause held the time constant, Restart returned to the beginning, and camera drag
  changed the view. The test recorded zero external requests and zero page errors
  (`browser-proof.json`, `browser-proof.png`).
- The package has `manifest.json`, `scene-map.json`, a compatibility report, and a
  bundled Three.js MIT license notice. The browser bundle has no CDN dependency.

## Important failure and decision

The native Stage Recorder USD **did contain 49 samples**, but overlaying it above
the base USD exposed a stronger default `xformOp:translate`/orientation/scale at the
final pose. The composed stage returned the same final height at first and last
timecodes. Flattening did not rescue the animation. Asset Converter reported success
for both composed and flattened variants but wrote GLBs with **zero animation clips**
(`output/recorder-inspection.json`, `output/scene_from_recorder.glb`, and
`output/scene_flattened.glb`). Therefore a successful recorder or converter status
alone is insufficient. The working checkpoint uses explicit pose sampling and
time-sampled USD authoring. The recorder composition path remains a possible later
optimization only after a specific repair and regression test.

## Remaining uncertainty

The largest untested areas are extracting all animated prims generically; arbitrary
geometry and referenced assets; MDL-to-browser material fidelity; textures, lights,
cameras, and variants; animation timing for different simulation configurations;
large files; and a second unrelated project. The browser proof ran on a software
renderer, but a range of end-user devices/browsers was not tested. The sample's
simple PreviewSurface materials cannot predict difficult production materials.

## Working estimate after this checkpoint

For **GPT-6 Sol at medium effort**, budget **8–16 hours of active agent work** to
attempt a reusable alpha, in bounded sessions with review after each milestone.
That is a working-time estimate, not a guarantee of model usage or uninterrupted
wall-clock time. The corresponding engineering effort is roughly **24–40 hours**,
assuming the next unrelated scene uses ordinary USD meshes and supported materials.
If the actual project depends heavily on MDL graphs, complex instancing, or assets
that the converter drops, add **8–16+ agent hours** for conversion/fallback work.
The estimate remains low-confidence until a second independent project passes.

The fastest next sequence is: generic prim discovery and synchronized capture;
dependency/material preflight with explicit warnings; package generation; then one
unrelated project end-to-end. A robust visual-fidelity pass comes after that alpha.

## Reproduction and scope

`web/` contains the proof player and browser test. Run `npm install`, `npm run build`,
then serve `web/dist/` with any static HTTP server. `web/public/README.txt` documents
the exported package. `proof.py` and `inspect_usd.py` target the isolated Isaac
workstation/container and show how the USD/GLB evidence was made. The checkpoint
does not publish, deploy, or alter an existing Isaac project.
