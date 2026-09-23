# Reusable capture-adapter checkpoint

This report predates the read-only factory integration probe. Its time estimate
below was made before that test; see `FACTORY_PROBE_REPORT.md` for the subsequent
verified result and remaining full-workflow gap.

## Outcome

A config-driven Isaac Sim adapter now exported three separate scenes through the
same `src/isaac_web_exporter/export.py` source: a falling box, a robotic inspection
cell, and Isaac's stock Franka robot. Each output was a static browser package
with recorded animation and the existing Start/Pause/Restart and camera controls.
The exporter did not touch the cheese-factory project. This is an **experimental
alpha for rigid and articulation-link transform playback**, not a general Isaac
project converter.

## Final verified runs

| Input | Capture and GLB | Browser verification |
|---|---|---|
| `examples/falling_box.json` | One discovered rigid body, 61 samples, one animation clip, two meshes | Edge + SwiftShader, static HTTP under `/falling-box-final/package/`; playback, Pause, Restart, camera drag, no external requests or page errors |
| `examples/inspection_cell.json` | Two discovered rigid bodies, 61 samples each; one clip also preserved authored pivot rotation and carrier translation; seven meshes | Same checks under `/inspection-cell-final/package/`; all four moving nodes changed in the browser |
| `examples/stock_franka.json` | Eleven discovered articulated links, 61 samples each; one clip, 22 channels, 51 meshes, 171 materials, 46,296,300-byte GLB | Same checks under `/stock-franka-final/package/`; arm/hand/finger transforms changed; visually inspected robot at initial and paused frames |

Exact capture/conversion results are in `runs/*-final/report.json`; browser test
measurements and screenshots are in `runs/*-final/browser-proof.json` and PNGs.
The three final packages passed browser tests on a SwiftShader software renderer
without external network requests. Browser control checks are end-to-end; visual
fidelity against an Isaac RTX reference was **not** established.

The negative configuration in `tests/negative_missing_body.json` requested two
rigid bodies from the one-box fixture. The adapter correctly wrote
`runs/negative-missing-body/report.json` with `status: failed`, created no success
package, and its isolated Docker process exited with status 1. This matters
because Isaac's fast shutdown otherwise masks a later `sys.exit(1)`; the adapter
passes the result directly to `SimulationApp.close(exit_code=...)`.

## What the adapter does

The JSON config selects an external bootstrap, capture roots, duration, sample
rate, viewer template and output directory. The bootstrap builds/loads a runtime
stage and can return an `on_step` callback to drive controllers. The exporter
discovers `UsdPhysics.RigidBodyAPI` prims, samples their Isaac world poses,
localizes each pose against its parent transform, writes explicit USD time samples,
and converts to GLB. It validates mesh/animation presence, expected moving-node
channels, external GLB URIs, and implausible node transforms before copying a
static player and writing manifest/compatibility metadata.

This validation caught two real false-success modes during development: native
Stage Recorder composition flattened to a static pose in checkpoint one, and
Asset Converter produced a huge bogus default node translation when an animated
transform had no explicit default opinion. The adapter uses explicit pose capture
and authors both the default and timed transform values. It also waits for the
converter task to complete by elapsed time rather than a small fixed update count.

## Limits that still matter

- Each project still needs an explicit bootstrap or integration hook. The adapter
  cannot infer a project's Python/ROS/controller startup procedure from a USD file.
- Pose localization assumes each captured rigid body's **parent transform stays
  static** during the recording. Franka's browser motion looked correct in this
  test, but moving-parent hierarchies need a specific regression fixture and fix.
- The stock Franka GLB had 171 materials, but material/texture fidelity was not
  compared with Isaac. MDL, remote textures, instancing, large scenes, and unusual
  asset references remain compatibility risks. Current dependency validation
  checks GLB external URIs; it is not a full source-asset audit.
- Browser playback has no live physics, controllers, sensors, or ROS. Skinning and
  deformables were not tested. Captured link transform animation is what was
  verified here.
- End-user testing used Edge with SwiftShader on the local workstation. It proves
  no RTX renderer is needed for these examples, not performance on every device.
- The stock Franka output contains a referenced NVIDIA asset. It remains a local
  technical test artifact, ignored by Git and not packaged for distribution here.

## Time estimate after this milestone

The core reusable capture-plus-player path now works for the tested subset. To
make it a reviewable v0 for a **specific user project**, budget roughly **4–8 more
hours of active GPT-6 Sol work** for that project's bootstrap, dependency/material
preflight, visual comparison, and final packaging checks. A project with complex
MDL, moving parent hierarchies, missing references, or large assets could require
**another 8–16+ hours**. These are uncertain work budgets, not delivery promises;
the actual project is the decisive test.

No remote repository was pushed and no existing user project was modified.
