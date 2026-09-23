# Isaac Web Exporter v1 local release notes

**Status: ready locally; all 66 acceptance gates pass.** The public source
repository is not a published v1 release or a published factory browser package.

The candidate exports owned Isaac Sim 6.1 scenes to a self-contained GLB and
Three.js browser package. It supports bootstrap modules, saved animated USD,
already-loaded stages, static mode, recorded transform animation, explicit
object identities, a complete object catalog, compact linear-key reduction,
and a local folder/ZIP. The player has transport, timeline, camera, selection,
responsive layout and guided-demo controls. An Isaac Kit panel provides
preflight, presets, export progress and local preview. V1 has no in-panel
Cancel control. A
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

E06 passes:
the owned sort-cell fixture produced nonempty Isaac RTX camera frames at three
matched browser times. Geometry, framing, orientation and motion phase were
reviewed in all six images; `runs/v1/E06_VISUAL_REVIEW.md` records the evidence
and the RTX-versus-WebGL lighting difference. The revised five-button panel
has no Cancel control. In two fresh Isaac 6.1 Kit runs it showed conversion
progress, produced validated packages, reached Ready at 100%, and responded
to a clicked Preflight after export in 1.95 and 0.89 seconds. A synthetic
child failure was reported accurately without a package. These passing UI
runs used `limit_cpu_threads=2` on the shared eight-core RTX host, which also
runs an existing Isaac service. A separate unrestricted eight-thread run
stalled after export under that load; normal Kit UI responsiveness on a
similarly saturated host is not guaranteed. See `runs/v1/f03/README.md`.

The rebuilt local wheel is `dist/isaac_web_exporter-1.0.0-py3-none-any.whl`
(SHA-256 `7ea343692cf949aa46289ed0cf6c2a44cf513d9ac2a8b188d22541824ba0c443`).
Installed in the pinned Isaac image, it exported and validated the owned
recorded USD with exit code 0.
Seven owned example ZIPs and their hashes are listed in
`runs/v1/release-artifacts.json`. Rebuild with `python tools/build_release.py`
using the versions in `toolchain.lock.json`. The final built browser packages
passed the eight-case Edge suite, Firefox 156 playback, 480/1280 desktop
layouts and 19 malformed-package checks. A Git-archived clean checkout built
and validated independently; that walkthrough is agent-run, not outside
novice-user feedback.
