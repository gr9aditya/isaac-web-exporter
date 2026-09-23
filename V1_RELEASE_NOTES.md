# Isaac Web Exporter v1 local candidate — release notes

**Status: incomplete until every gate in `V1_ACCEPTANCE.md` passes.** This
document describes the current local candidate and does not authorize push,
publication, or deployment.

The candidate exports owned Isaac Sim 6.1 scenes to a self-contained GLB and
Three.js browser package. It supports bootstrap modules, saved animated USD,
already-loaded stages, static mode, recorded transform animation, explicit
object identities, a complete object catalog, compact linear-key reduction,
and a local folder/ZIP. The player has transport, timeline, camera, selection,
responsive layout and guided-demo controls. An Isaac Kit panel provides
preflight, presets, export progress, cancellation and local preview. A
versioned customization kit contains three optional scripts.

The 30-second owned sorting workflow, duplicate-name twin fixture, static
gallery, Y-up centimeter fixture and falling box have exported and validated
in the isolated pinned Isaac image. The standard workflow has 10 draw calls,
120 triangles and no embedded image textures. Its compact preset reduces GLB
bytes from 105,468 to 54,168 while retaining all geometry accessor bytes and
staying within the motion tolerance. These figures describe only that
fixture. See `runs/v1/` and `V1_ACCEPTANCE.md` for current measured evidence.

The browser is a recording viewer, not an Isaac runtime. It does not support
deformables, particles, spawn/despawn, live physics/controllers, arbitrary
MDL/RTX appearance, or automatic replication of every project's launch
procedure. A bootstrap/adapter may be needed for a project. The source-code
license remains unselected; local/private use only. Private cheese-factory
and stock Isaac assets are not in the release samples.

The Isaac reference-image gate is currently open: isolated RTX/Xvfb captures
showed a black viewport, Replicator RGB was empty with a renderer-advance
error even after the documented async-render flag and user-settings reset, and
the pinned OpenUSD runtime has no CPU imaging plugin. Geometry and motion were
independently compared numerically; those tests do not substitute for the
required first/middle/final Isaac visual comparison.
