# Second-scene test: robotic inspection cell

## Result

A second, independent synthetic Isaac Sim scene passed the recorded-playback path.
It contains a nested robot arm with authored pivot rotation, a translating carrier,
and two falling rigid-body payloads. The same static browser player from checkpoint
one played all four movements without a player source change. This is a controlled
fixture, not a user project or a production articulation.

## Evidence

- `test.py` builds the scene in a new isolated Isaac 6.1 container using only the
  exporter workspace mount. It did not open or modify the cheese-factory project.
- `output/test-report.json` records 61 pose samples for **each** rigid payload.
  Payload A moved from 1.97275 m to 0.16 m; B moved from 2.57275 m to 0.14 m.
- The installed Asset Converter returned `OmniConverterStatus.OK` and produced a
  23,036-byte GLB. Direct GLB inspection found **seven meshes, seven materials,
  and one animation clip** with channels for the arm pivot rotation, carrier
  translation, and translation/rotation of both payloads.
- The package served over local static HTTP. Automated Edge testing used SwiftShader
  software rendering and observed changed transforms for all four moving nodes.
  Start, Pause, Restart, and camera drag passed; no page errors or external network
  requests were recorded (`browser-proof.json`).
- `site/` is the same browser build as checkpoint one with `scene.glb` and metadata
  replaced. The included Three.js MIT notice remains in the package.

## What this changes in the estimate

This increases confidence that the **GLB plus small static player** route handles
multiple synchronized rigid and authored transform tracks. It does not lower the
**8–16 active GPT-6 Sol hours** budget for a reusable alpha much: `test.py` still
names the moving prims and builds the fixture explicitly. A real exporter must
discover/choose prims, adapt to a project's runtime setup, close file dependencies,
convert or flag complex materials, and fail clearly when motion or assets are lost.
Testing a real articulation and an unrelated user project could move the estimate.

This test used self-authored meshes and USD PreviewSurface materials. It says
nothing definitive about MDL, textures, remote references, skinning, deformables,
large scenes, or visual fidelity against Isaac RTX rendering.
