# Isaac Web Exporter v1 local candidate — release notes

**Status: incomplete until every gate in `V1_ACCEPTANCE.md` passes.** This
document describes the current local candidate. The public source repository
is not a v1 release or a published factory browser package.

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
license remains unselected; no general use license is granted. Private cheese-factory
and stock Isaac assets are not in the release samples.

The local candidate is **not v1-ready** while F03 remains blocked. E06 now
passes: the owned sort-cell fixture produced nonempty Isaac RTX camera frames
at three matched browser times via the working headless Kit entrypoint.
Geometry, framing, orientation and motion phase were reviewed in all six
images; `runs/v1/E06_VISUAL_REVIEW.md` records the evidence and the substantial
RTX-versus-WebGL lighting difference. F03 still requires real capture and
conversion cancellation in an interactive Kit session. The visible panel
reflected live child capture and conversion progress, but its Kit update loop
stalled after the Cancel clicks were issued. Button callback, final cancelled
status and post-cancel usability remain unverified. Synthetic cancellation and
independent interrupted capture passed. See `runs/v1/f03/README.md`.

The tested local wheel is `dist/isaac_web_exporter-1.0.0-py3-none-any.whl`
(SHA-256 `cc5a118448ac3fb956b8003a5117a6765c734e04875d1e4d07db6ceaf250ee33`).
Seven owned example ZIPs and their hashes are listed in
`runs/v1/release-artifacts.json`. Rebuild with `python tools/build_release.py`
using the versions in `toolchain.lock.json`. The final built browser packages
passed the eight-case Edge suite, Firefox 156 playback, 480/1280 desktop
layouts and 19 malformed-package checks. A Git-archived clean checkout built
and validated independently; that walkthrough is agent-run, not outside
novice-user feedback.
