# v0 acceptance record — recorded-playback scope

This record maps the gates in `IMPLEMENTATION_PLAN.md` to the final local test
artifacts. The implemented v0 is a reusable exporter for fixed-topology rigid
and articulation-link transform playback, authored USD transform animation,
portable GLB conversion, and a self-hostable browser player. It does not imply
universal Isaac-project or RTX-material fidelity. Nothing was published.

## Gate results

| Plan gate | Result and evidence |
|---|---|
| 1. Core proof | **Pass.** A five-second self-authored falling-box simulation produced 151 pose samples, a self-contained animated GLB, and Start/Pause/Restart plus orbit/pan/zoom in the static player. `runs/v0-final-falling-box/report.json`, `package/`, `edge-nested.json`. |
| 2. Route decision | **Pass.** Isaac's USDZ packaging reopened with 61 samples and pinned USD Web View displayed distinct first/last frames offline. Factory USDZ packaging failed on `OmniPBR.mdl`; the GLB route passed the factory browser test. `ROUTE_DECISION.md`, `runs/usdz-probe-report.json`, `runs/usdz-webview-browser.json`. GLB is the sole v0 output format. |
| 3. Reusable alpha | **Pass for the stated subset.** The same exporter source handled the falling box, an unrelated inspection cell, stock Franka link motion, a saved USD with authored animation, an already-loaded Isaac stage, and a real factory scene through a separate bootstrap. The factory clip is deliberately limited to one conveyor object. `runs/v0-final-*/report.json`, `ALPHA_CHECKPOINT_REPORT.md`, `FACTORY_PROBE_REPORT.md`. |
| 4. Portability | **Pass for desktop Chromium software rendering, with visual-fidelity limits.** Final packages were copied to `runs/portable-host/nested/` and served by plain Python static HTTP. Edge and Chrome on SwiftShader passed the small fixture; Edge passed inspection, saved-stage, loaded-stage and factory packages. Browser tests blocked all external requests and found none. Isaac capture first/last poses matched browser-local GLB positions exactly for box, inspection payload and factory object (`tests/compare_capture.py`). Material factors in the small GLB match the authored PreviewSurface colors; factory object's GLB scale is 0.0515 on each axis, matching source. Browser screenshots show the relevant geometry and orientation. A headless Isaac RTX RGB reference attempt returned empty annotator data, so there is **no pixel-accurate RTX comparison**. |
| 5. Handoff | **Pass.** Every final package passes `validate_package.py`, including required files, local HTML resources, no external GLB URIs, animation/mesh presence, scene-map node names and GLB SHA-256. Tampering with a GLB makes validation fail. A bound missing-texture fixture made export exit 1 with no package; the missing-body negative test also failed as intended. The player license, manifest, compatibility report, hosting instructions and `LLM-HANDOFF.md` ship in each package. `toolchain.lock.json` records tested versions/hashes. |

## Measured final packages

| Input/output | Clip / GLB | Browser result |
|---|---|---|
| `runs/v0-final-falling-box` | 5 s; 2 meshes; 10,464-byte GLB; 151 samples | Edge and Chrome: 0 external requests/errors; approximately 1.0–1.2 s to ready; ~60 observed rAF fps on SwiftShader. |
| `runs/v0-final-inspection-cell` | 2 s; 7 meshes; 23,076-byte GLB; 61 samples per rigid body | Edge: static nested URL, controls/navigation and payload motion passed. |
| `runs/v0-final-saved-stage` | Authored 5 s clip; 2 meshes; 10,464-byte GLB | Edge: authored playback and controls passed, without physics capture. |
| `runs/v0-final-loaded-stage` | 2 s; 2 meshes; 7,216-byte GLB | Edge: in-process already-loaded stage capture and playback passed. |
| `runs/v0-final-factory-readonly` | 2 s; 159 meshes, 189 materials; 25,128,568-byte GLB; 61 active-object samples | Edge: object moved 0.4 m; controls/navigation passed, 0 external requests/errors; ~2.1 s to ready and ~8 observed rAF fps on SwiftShader. The robot and factory layout are static in this clip. |

The FPS figures are 1.5-second headless Edge/SwiftShader `requestAnimationFrame`
observations on this Windows workstation, not broad device guarantees. The two
tested browsers share Chromium; Firefox and Safari were not tested. The factory
rate makes large-scene optimization a follow-on concern. Numeric browser results,
screenshots and performance JSON live beside each ignored `runs/v0-final-*`
package.

## Validation and limits

The v0 can capture an explicit project bootstrap or an in-process loaded stage,
or preserve authored animation from an existing USD. A project still needs a
bootstrap/controller hook when Python constructs or moves its scene. Capture
does not infer that hook from a USD file. `UsdUtils.ComputeAllDependencies`
preflights source assets in Isaac's resolver environment; required missing
visual dependencies fail export. Generated GLBs are checked for external URIs.

Motion and appearance outside the tested subset need project-specific checks:
spawn/despawn, animated visibility, deformables, particles, arbitrary MDL graphs,
complex moving-parent hierarchies, native instances, and large-scene performance.
The factory report warns that non-PreviewSurface shader graphs need visual QA.
The attempted headless RTX reference capture in `tools/isaac_reference.py` did
not produce RGB data; therefore the current visual evidence is source/GLB
geometry and material values plus browser screenshots, not an Isaac RTX image
diff. This is a known quality limit, not a claim of equivalent rendering.

The cheese-factory project was mounted read-only for every factory test. Its
`git status --short` remained empty and HEAD stayed
`bb1cae1d8a410237dd646dd74325145a78a3a715`. The factory and stock Franka
packages were kept local because asset redistribution rights have not been
established; the exported packages were not published or pushed.
