# Read-only cheese-factory export probe

## Result

The experimental exporter produced a self-hostable browser package from the
project's real scene authoring code. The tested clip is **two seconds of one
cheese-colored object moving along the conveyor**. The factory layout and Franka
model are present, but this is not a recording of the project's full classification,
pick-and-place, or controller run.

The source project was mounted read-only at `/project` in an isolated Isaac Sim
6.1 container. The exporter, logs, and outputs lived under `/work`. After the
run, `git status --short` in the source project remained empty and HEAD was
`bb1cae1d8a410237dd646dd74325145a78a3a715`.

## Verified evidence

- `examples/factory_readonly.py` imports `sim.factory.scene.IsaacFactoryScene`,
  calls `setup_scene()`, adds one active object using `set_object()`, and moves it
  at the project's configured conveyor speed during capture. The corresponding
  config is `examples/factory_readonly.json`.
- The successful `runs/factory-conveyor-v5/report.json` records 61 samples of
  `/World/ActiveObject`, from approximately `(0.500, -0.650, 0.0558)` to
  `(0.500, -0.250, 0.0558)` in the source stage. The converter produced a
  25,128,568-byte GLB with 159 meshes, 189 materials, one animation, and two
  channels for the active object. It found no external GLB URIs or implausible
  node transforms.
- The static package is `runs/factory-conveyor-v5/package/`. Served over local
  HTTP, it loaded in Edge using SwiftShader software rendering. The browser
  check found one two-second clip, confirmed the object moved, Pause held time,
  Restart returned to zero, camera drag moved the camera, and observed no
  external requests or page errors. Screenshots and numeric results are in
  `runs/factory-conveyor-v5/browser-*.png` and `browser-proof.json`.
- The browser screenshot shows the layout, robot, bins, rails, and moving
  object. The optional camera preset in the package manifest avoids framing
  the oversized ground plane as the whole scene.

## Compatibility findings

The first attempt to invoke the project's asynchronous full sample loader ended
in a native Kit crash before the exporter could write a report. A synchronous
scene-authoring bootstrap worked. This narrows the demonstrated integration
surface to the real authored scene and an `on_step` conveyor callback; it does
not establish compatibility with the project's full asynchronous runtime.

The converter initially omitted the moving object because it was an analytic
`UsdGeom.Cube`. The exporter now converts analytic cubes to mesh geometry in a
**separate export stage**, preserving the project source, and retains a rigid
body's authored scale when replacing its pose operations. This converted 133
factory cubes and made the active object's translation and rotation channels
appear in the GLB. A later run captured only the active object so the visible
Franka remains in its authored static pose while this limited conveyor clip
plays.

The report still warns about shader types that need visual QA. This browser
render was inspected for basic geometry and color, not compared pixel-for-pixel
with an Isaac RTX image. Large ground geometry, materials, texture fidelity,
and browser performance on other devices remain open. The package includes
project/NVIDIA-derived assets and is retained locally as a technical test; it
has not been published or licensed for redistribution.

## Next engineering checkpoint

To record the *actual factory sequence*, integrate with its running controller
without the async Kit crash, drive the full classification/pick-and-place cycle,
and capture any object spawn/despawn or visibility events. The present rigid-pose
recorder does not represent lifecycle changes, sensors, ROS, or controller state.
That is the main remaining effort before calling the factory example a complete
showcase export.
