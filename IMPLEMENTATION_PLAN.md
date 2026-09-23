# Reusable Isaac Sim browser exporter — feasibility and implementation plan

Planning date: 2026-09-22. The original review stopped at investigation and
planning. The user subsequently authorized implementation of the scoped v0.
`V0_ACCEPTANCE.md` tracks the gates below against final tests, and
`ROUTE_DECISION.md` records why the tested implementation uses GLB rather than
the initial USDZ/Web View hypothesis. The recommendations below remain the
original planning record, not a description of the final architecture.

## Recommendation

Use an **independent exporter repository** and an export-only adapter running in the existing Isaac version. First test **Stage Recorder → portable USD with recorded time samples → USDZ → a pinned USD Web View frontend**. Reuse the viewer's checked-in WASM for the initial proof. Do not commit the product architecture until a short capture works in a real browser on a non-RTX machine.

This is the fastest plausible route to the first demonstration because it avoids writing a USD reader, animation renderer or USD-to-glTF translator. It is not yet a proven end-to-end route. The current viewer has a failed visual-regression check, incomplete native build provenance and rendering limitations. A narrow **USD-to-GLB conversion using the already installed Asset Converter** is the first fallback to compare if the USD route fails or performs poorly.

Estimated effort for one experienced developer: roughly **one day for a narrowly scoped proof**, **4–7 working days total for a reusable alpha if that proof passes**, and **1–3 additional weeks or more** if arbitrary MDL fidelity, Fabric-dependent capture or large-scene performance becomes mandatory. These are planning estimates, not measured timings or delivery promises.

## Verified facts

The [environment evidence](./ENVIRONMENT_EVIDENCE.md) records exact paths and observations. The running image is Isaac 6.1.0, detailed build `6.1.0-rc.26+release.49347.2d230af4.gl`; Kit is 110.3.0, OpenUSD 25.11, Python 3.12.13. Cached components include Stage Recorder core 110.0.14 and Asset Converter 6.0.5. Official [Isaac 6.1 release notes](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/overview/release_notes.html) corroborate Kit 110.3.0, and the [Kit registry](https://docs.omniverse.nvidia.com/kit/docs/kit-registry-reference/latest/110/shared.html) lists the recorder version.

The current container mounts the cheese-factory project writable at `/workspace`. Future development should use a separate container from the same image digest, with independent workspace/output/config/cache mounts; do not alter the existing service. `/home/ubuntu/isaac-web-exporter` was available but has not been created.

The candidate viewer's [lockfile](https://github.com/usd-wg/usd-wg-webview/blob/b050c3731d1854a5980b6b4fe55ec1725dc18f51/package-lock.json) pins Three.js 0.185.0 development commit `16e7674dbcda5137e48953959bdf5275f834642a`, Spark 2.1.0, Vite 5.4.21 and TypeScript 5.9.3; upstream CI uses Node 22. Its committed WASM namespace is consistent with OpenUSD 26.05, whereas Isaac uses 25.11. These processes exchange USD files, not native libraries, so a matching C++ ABI is unnecessary across the browser boundary. File/schema/material compatibility still needs real fixtures. Do not install the browser SDK or an arbitrary new USD Python wheel into Isaac's runtime. The viewer package is a private 0.0.0 application with no published releases at inspection time, not a stable SDK release.

| Area | Verified capability | Limitation or untested boundary |
|---|---|---|
| Recording | Installed `StartRecording`/`StopRecording` API; time-sampled animation output. | Cached API presence is not a successful recording. Fabric/physics writeback must be checked. |
| Packaging | OpenUSD 25.11 has dependency discovery and USDZ localization APIs. | Packaging does not translate MDL or guarantee that every external resource is present. |
| Viewer | Current source has USD/WASM loading, animation controls, camera navigation, mesh/skinning/point-instancer paths and PreviewSurface materials. | Neither this Isaac build nor its recordings have been tested with it here. |
| Materials | Installed USD–MDL converter; optional Distill and Bake has official documentation. | `omni.mdl.distill_and_bake` was not found in inspected extension directories. The installed `omni.mdl.usd_converter` is a different extension. |
| GLB alternative | Installed Asset Converter exposes animation and embedded-texture options. | Actual export of Stage Recorder output remains untested. |

## Proposed data flow and responsibilities

```text
Developer's NVIDIA workstation
  stage file OR explicit project bootstrap OR loaded runtime stage
    → wait for scene/assets/controllers to be ready
    → capture supported visible motion in Isaac
    → snapshot composed scene + animation into an isolated export copy
    → normalize geometry/materials; collect and validate dependencies
    → portable USDZ + static viewer + manifest/report/licenses

End user's computer
  ordinary static HTTP hosting → browser JS/WASM → scene + recorded playback
```

The recipient needs browser graphics support and sufficient CPU/RAM, but no Isaac Sim, Docker, RTX GPU or simulation server. Start with the viewer's WebGL path and PreviewSurface materials to avoid making MaterialX/WebGPU a v0 requirement. Test integrated graphics explicitly; no universal mobile or GPU-free performance claim is justified.

### Capture adapter: small amount of new code

Support three inputs: an existing USD stage, an explicit Python bootstrap callable that constructs and runs a project, and an already-loaded stage in Isaac. A USD file alone cannot reconstruct arbitrary Python/ROS/controller setup. Reusability means stable adapter interfaces and configuration, not automatic discovery of every project's launch procedure.

Reuse the installed Stage Recorder API directly; do not add Isaac Lab solely for its recording wrapper. Capture after runtime scene construction and asset loading. Expose capture roots, duration and sample rate rather than assuming `/World` or factory-specific paths. Prefer simulation-time sampling after each appropriate step, with an explicit frame/time contract; validate timing against the installed recorder modes.

The [Stage Recorder documentation](https://docs.omniverse.nvidia.com/extensions/latest/ext_animation_stage-recorder.html) describes animation changes layered above the original hierarchy. [Isaac Lab's recording guide](https://isaac-sim.github.io/IsaacLab/main/source/how-to/record_animation.html) warns that Fabric may bypass USD writes and documents an OVD alternative. Start with USD writeback enabled for capture. Distinguish physics writeback from merely enabling the Fabric scene delegate; the installed recorder's tests mention the latter, which does not establish the former. Detect empty/unchanging captures and fail visibly.

Skip recording for static scenes; preserve existing authored animation. Existing USD time samples may not be re-recorded by Stage Recorder. For Fabric-dependent projects, consider OVD baking onto the original visual stage, after validating installed OmniPVD 110.3.2. It is a fallback, not a second mandatory v0 backend. [OVD baking documentation](https://docs.omniverse.nvidia.com/kit/docs/omni_physics/110.1/extensions/ux/source/omni.physx.pvd/docs/dev_guide/physx_visual_debugger.html).

### Scene normalization and packaging: the main exporter work

Create an independent composed export stage containing runtime objects, selected variants, loaded payloads and relevant session/anonymous-layer opinions. Put the recording above the base stage at matching prim paths. A root-layer file copy alone can lose runtime composition. Preserve time range, `timeCodesPerSecond`, units and up axis. Disable/remove simulation behavior only in the export copy so native playback checks cannot fight the recording.

For v0, freeze topology and the object population. Preserve instancing where the viewer handles it and expand only when necessary. Convert analytic shapes to meshes: source inspection of the viewer's [unified driver](https://github.com/usd-wg/usd-wg-webview/blob/b050c3731d1854a5980b6b4fe55ec1725dc18f51/native/usd-webview-bindings/src/unifiedDriver.cpp) shows mesh and point-instancer paths, not a general analytic-primitive renderer. An Isaac Cube is therefore a useful compatibility test, not an assumed success.

Test native USD instanceable references separately from `PointInstancer`: the inspected ordinary stage traversal does not establish instance-proxy mesh support. Allow expansion in the export copy when required, while reporting resulting size growth. This check belongs in the first gate because robot assets can contain native instances.

Keep PreviewSurface materials. Add a deliberately narrow OmniPBR-to-PreviewSurface mapping and material overrides, reporting approximations per material. Unsupported MDL gets a clear fallback material plus warning, or a strict-mode export failure. Do not silently present a black or missing material as supported.

Resolve source URLs/Nucleus/custom paths while still in the Isaac resolver environment, localize assets, and author package-relative paths. Use [OpenUSD 25.11 dependency discovery](https://github.com/PixarAnimationStudios/OpenUSD/blob/v25.11/pxr/usd/usdUtils/dependencies.h) and [CreateNewUsdzPackage](https://github.com/PixarAnimationStudios/OpenUSD/blob/v25.11/pxr/usd/usdUtils/usdzPackage.h), with `editLayersInPlace=False`. The default protects source layers; directory dependencies still require special handling. Do not use the more restrictive ARKit package variant by default. Flattening may simplify a selected composition but does not embed texture pixels; USDZ is an aligned, uncompressed ZIP, not a material converter. [USDZ specification](https://openusd.org/release/spec_usdz.html).

After packaging, reopen from a clean location and reject unresolved required dependencies. Check for source absolute paths, Nucleus URLs and remote resources. The same checks apply if the final asset is GLB. Report unsupported schemas and behavior separately from fatal missing visual assets.

### Browser runtime: reuse most code, build a thin product wrapper

Inspected candidate: [USD Web View commit b050c373](https://github.com/usd-wg/usd-wg-webview/tree/b050c3731d1854a5980b6b4fe55ec1725dc18f51). The repo already checks in a 19.7 MB OpenUSD WASM binary and MaterialX runtime. First use its lockfile and committed artifacts; a native rebuild is not an assumed prerequisite. Build a small wrapper for automatic local scene loading, Start/Pause/Restart, loading/errors, recorded-playback label and manifest camera selection. Reuse navigation and animation logic.

Define controls: Start resumes the paused playhead; Pause freezes it; Restart seeks to the authored start and resumes. Initially show the first frame paused; stop at the end unless looping is explicitly selected. Restart must not rerun Isaac or reset the viewer's freely navigated camera.

Bundle runtime JS/WASM, textures and any environment image locally. Fix absolute runtime URLs for hosting under a subdirectory. Require ordinary HTTP hosting rather than double-clicking `file://`. Vite development configuration includes isolation headers, but the inspected generated runtime did not establish that every production deployment requires them; test plain static hosting, correct WASM MIME and subpath behavior before specifying server requirements.

The [current upstream CI run](https://github.com/usd-wg/usd-wg-webview/actions/runs/32314546304) passed units but failed visual regression. A [previous green run](https://github.com/usd-wg/usd-wg-webview/actions/runs/31218770946) used `9478c296a239ea28c56295c41df6b4593cecebf2`; do not blindly roll back and lose later fixes. Determine which candidate passes our fixtures, then lock its source and binary hashes. Native SDK [build notes](https://github.com/usd-wg/usd-wg-webview/blob/b050c3731d1854a5980b6b4fe55ec1725dc18f51/docs/wasm-sdk.md) do not fully establish reproducible provenance; native rebuilding/patching is a schedule risk.

The viewer's [geometry strategy](https://github.com/usd-wg/usd-wg-webview/blob/b050c3731d1854a5980b6b4fe55ec1725dc18f51/docs/material-geometry-strategy.md) describes per-frame geometry emission even for transform changes. Large factory playback may therefore need optimization. Source review also raises an untested visibility-update concern; exclude spawn/despawn and animated visibility from promised v0 support until validated.

## Alternatives and decision rule

| Route | When it is quicker | What can make it slower |
|---|---|---|
| USDZ + pinned USD Web View | First proof with ordinary meshes, portable materials and USD transform samples; no conversion layer. | WASM build repair, renderer bugs, geometry traffic per animation frame, unsupported primitive/material behavior. |
| Installed Asset Converter → GLB + Three.js | Small fixed scenes whose baked rigid animation converts correctly; potentially simpler/lighter playback. | Conversion can lose composition, instancing, lights or animation semantics; material portability still required. |
| Adobe USD file-format plugins → GLB | Later if the installed converter is inadequate and its feature set fits. | Native build and USD ABI compatibility; avoid injecting arbitrary plugin binaries into Isaac. |
| New parser/renderer or Isaac fork | No near-term advantage for this requirement. | Substantial unrelated engineering and maintenance. |

The [installed converter's documented capabilities](https://docs.omniverse.nvidia.com/extensions/latest/ext_asset-converter.html) include GLB, rigid/skeletal animations and embedded textures. It explicitly limits export materials and does not promise arbitrary MDL baking. Leave animation enabled and the proprietary MDL glTF extension disabled. Spend at most a short diagnostic spike on this alternative before deciding the v0 format; do not build two production backends concurrently.

[Adobe's glTF plugin](https://github.com/adobe/USD-Fileformat-plugins/tree/2026.07/gltf) is a later option. Its 2026.07 material changes and native dependencies add risk; [OpenUSD Exchange SDK](https://github.com/NVIDIA-Omniverse/usd-exchange) is optional authoring/validation help, not an exporter replacement. No live physics tier belongs in v0.

## What is quick, and what expands the schedule

Estimates below are components of the total, not independently additive commitments.

| Work | Planning effort | Caveat |
|---|---:|---|
| Reused navigation and Start/Pause/Restart wrapper | Half a day | Assumes working pinned viewer; restart semantics still need a browser check. |
| Capture and export one small stock scene | Half to one day | Assumes USD receives changing motion samples and simple materials. |
| Reusable stage/bootstrap adapter, dependency packaging, manifest/report | Two to four days | Session layers, remote assets, roots and timing must work on a second project. |
| Static hosting verification, two fixtures, documentation | One to two days | Must include actual non-RTX hardware and blocked external network requests. |
| A narrow set of material mappings | Half to two days | Appearance will differ from RTX; report it. |
| Arbitrary MDL, UDIM, procedural textures, glass, SSS | Several days to weeks; no blanket success promise | Baker absent; documented limitations and contradictory normal-map guidance. |
| Fabric/OVD integration, deformables/particles, spawn/despawn | Additional multi-day investigations | Capture and web rendering both need support. |
| Large factories, decimation/LOD, animation optimization, mobile support | One or more weeks as needed | Model/texture size and current viewer frame updates may dominate. |

The MDL [versioned API](https://docs.omniverse.nvidia.com/kit/docs/omni.mdl.distill_and_bake/latest/Overview.html) uses `distill_async()`, has output-path spelling differences from older examples, and lists limitations. The [general scripting page](https://docs.omniverse.nvidia.com/extensions/latest/ext_material/ext_mdl-distill-and-bake/scripting.html) additionally flags UDIM, procedural textures and SSS. Installation and a Kit 110.3 compatibility test are prerequisites to making it a required exporter dependency. Prefer a controlled material subset for speed.

## Repository home and suggested structure

Use your new independent repository. Keep Isaac as a version-pinned tool dependency. Use a pinned vendor/submodule reference plus a small patch set for the viewer only if needed. An Isaac fork is warranted only for a demonstrated upstream defect that cannot be handled through supported extension APIs; it is not the product home.

```text
isaac-web-exporter/
  README.md
  pyproject.toml
  src/isaac_web_exporter/
    cli.py
    isaac_adapter/       # loaded stage, bootstrap hooks, capture
    usd_pipeline/       # composition, geometry, materials, dependencies
    package.py
    report.py
  web/                  # small viewer wrapper and locked frontend deps
  third_party/          # pinned viewer reference, patches, license records
  schemas/              # manifest and compatibility-report schemas
  examples/             # stock fixture adapters + their configuration
  tests/                # packaging/timing checks and browser acceptance
  docs/                 # setup, hosting, supported features, evidence
  toolchain.lock.json   # image digest, Kit/USD/extensions, viewer/artifact pins
  .gitignore            # exports/, recordings/, caches/, downloaded assets
```

The CLI/module is the first entry point. A polished Isaac extension UI is later convenience, sharing the same core. Output packages contain `index.html`, local runtime/assets, `scene.usdz` (or the chosen GLB), `manifest.json`, `compatibility-report.json`, notices and hosting instructions. Manifest fields should include schema/tool/source versions, mode `recorded`, time range/FPS, camera, units/up axis, dependency hashes and capture settings. Diagnostics should identify affected prim/material paths, severity and approximation. Asset provenance belongs in the report; exclude credentials and avoid shipping workstation-specific paths in public output.

## Acceptance gates before framework expansion

1. **Core proof:** prepare a separate runtime; record 5–10 seconds of a stock rigid-body sample with visible motion and portable material. Tessellate analytic shapes in its export copy. Confirm multiple changing time samples and the correct duration before testing the viewer. Prove camera navigation and control semantics from the packaged static site.
2. **Route decision:** if capture is correct but the viewer fails, identify loading/material/animation/performance failure precisely. Try the installed GLB converter on the same normalized fixture. Choose the simplest passing route; do not repair a whole native toolchain before checking this alternative.
3. **Reusable alpha:** export a second unrelated articulation scene through configuration/bootstrap hooks without modifying exporter source. A stock Franka example is reachable for technical testing; use an expressly redistributable asset for deliverable fixtures. Verify a runtime-created stage as well as a saved-stage input.
4. **Portability:** open the extracted package from another directory and under a URL subpath; block all external requests. Test Chromium on a machine without RTX/Isaac/Docker and a second intended browser. Capture several matching timestamps in Isaac and the viewer, including first/last and post-Restart frames. Check geometry, materials, scale, orientation and timing; record hardware/browser, load time, memory, package size and frame rate. A proposed initial target is 30 fps on the named test laptop for the small fixture, to be validated rather than promised globally.
5. **Handoff:** include a compatibility report with errors rather than false success, package/manifest checks and a missing-dependency negative test. Record artifact hashes and license notices. Keep recordings/caches/output out of source control. Publishing is a later user decision.

## Licensing findings and limits

[USD Web View](https://github.com/usd-wg/usd-wg-webview/blob/b050c3731d1854a5980b6b4fe55ec1725dc18f51/LICENSE) is BSD-3-Clause. [Three.js](https://github.com/mrdoob/three.js/blob/16e7674dbcda5137e48953959bdf5275f834642a/LICENSE) and [Spark](https://github.com/sparkjsdev/spark/blob/main/LICENSE) are MIT; [MaterialX 1.39.5](https://github.com/AcademySoftwareFoundation/MaterialX/blob/v1.39.5/LICENSE) is Apache-2.0. [OpenUSD](https://github.com/PixarAnimationStudios/OpenUSD/blob/v26.05/LICENSE.txt) uses Tomorrow Open Source Technology License 1.0, derived from Apache-2.0 with a different trademark section. The complete shipped dependency set needs preserved notices and recorded binary provenance; the viewer's top-level license alone does not cover every dependency or sample asset. Do not substitute Needle source without resolving its separate terms.

[Isaac source](https://github.com/isaac-sim/IsaacSim/blob/v6.1.0/LICENSE) is Apache-2.0, while Kit, extensions and assets have separate terms. Keep them on the export workstation, and ship only the permitted browser runtime and content. NVIDIA's [Isaac 6.1 FAQ](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/common/license-faq.html) distinguishes output distribution from simulator distribution but still states an Enterprise requirement for the latter. Its [general Omniverse page](https://docs.omniverse.nvidia.com/ov/latest/common/NVIDIA_Omniverse_License_Agreement.html), updated later, says redistribution is free under applicable terms. These pages conflict; this research does not claim to resolve entitlement for distributing proprietary components.

More directly relevant: [additional-materials terms](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/common/license-isaac-sim-additional.html) and individual model/texture licenses govern asset redistribution. An animated USDZ contains geometry and textures, unlike an ordinary rendered video. Conversion does not create new redistribution rights. Use owned/expressly redistributable fixture assets and retain per-asset notices; do not claim blanket clearance for every Isaac stock asset.

## Assumptions and untested ideas

**Planning assumptions:** short desktop-browser recordings; fixed topology/object population; rigid objects and articulation links; static material bindings; a selected variant state; approximate lighting/materials acceptable when reported; an explicit project bootstrap hook is acceptable. The developer has a licensed Isaac workstation, and the recipient can use a small static HTTP server or equivalent hosting.

**Not yet tested:** recording on this exact build; physics writeback settings; USD 25.11 output in the inspected viewer's newer WASM; portable package closure; MDL baker availability; GLB animation conversion; visibility updates; integrated-GPU performance; real-scene appearance and redistribution rights. No browser screenshot or functional demonstration was generated because this task was limited to planning.
