# Isaac Web Exporter: from working replay to a reusable product

Planning date: 2026-09-23. Status: proposal for review, not implemented.

This roadmap builds on the accepted, working v0. It supplements the original
[implementation plan](IMPLEMENTATION_PLAN.md); it does not rewrite its history
or expand what [v0 acceptance](V0_ACCEPTANCE.md) claims. The proposed product
name, **Isaac Replay Studio**, is a working name only.

## 1. Product direction

Turn an Isaac run into an **interactive simulation report** that someone can
open, explore, explain and customize in an ordinary browser. The first audience
is an Isaac developer showing a robotics or automation workflow to someone who
does not have Isaac. Engineering review and training are later uses of the same
recording and player.

The intended experience is:

1. Open a working scene in Isaac and choose **Record for browser**.
2. Choose what to include, a duration, and a presentation preset.
3. Run the existing project while the exporter records supported state.
4. Inspect a preview and a readable compatibility report.
5. Export a folder or ZIP, then place it on ordinary static hosting.
6. The recipient plays, scrubs, navigates, selects objects and follows a tour.
7. Optionally, a developer or LLM customizes the presentation using a documented
   package contract. The default experience already works.

The developer still needs Isaac and its supported workstation environment to
capture a new simulation. The recipient needs a supported browser and sufficient
graphics capability. The browser displays recorded results; changing the camera,
annotation or playback speed does not calculate a new physics outcome.

## 2. What we have, and the gaps that matter

| Status | Evidence or implication |
|---|---|
| Verified locally: GLB export, bundled player, Start/Pause/Restart, orbit/pan/zoom | [README](README.md), [player source](checkpoint1/web/src/main.js), and [acceptance record](V0_ACCEPTANCE.md). |
| Verified locally: bootstrap, saved animated USD, already-loaded stage | Same exporter across independent examples; saved USD does not recreate Python project controllers. |
| Verified locally: simple articulation proof and a short factory recording | The final factory recording moves one object for two seconds. A complete robot workflow still needs a new acceptance test. |
| Verified locally: portability and negative validation tests | Static nested hosting, no external requests in tested fixtures, missing assets and tampered GLB rejected. |
| Verified limitation: factory ~25 MB and ~8 observed fps on SwiftShader | This is a software-renderer observation, not a normal laptop benchmark or proof of the bottleneck. |
| Code gap: captured objects map to GLB by leaf name | Duplicate captured names are rejected. The current scene map covers captured rigid bodies, not a complete semantic inventory. See [exporter](src/isaac_web_exporter/export.py). |
| Code gap: first animation clip only; no scrubber, selection or authored tour | These are new player work, not configuration switches already available. |
| Code gap: static-only exports are rejected by exporter/validator | Add an explicit static mode if scene-only sharing is promised. It is not currently part of supported v0 output. |
| Unverified: RTX image equivalence, integrated-GPU performance, Firefox/Safari | Keep these as explicit validation work. An unsuccessful RTX reference capture must not count as visual proof. |

## 3. The larger experience

### A. Replay Studio: the next visible milestone

Provide a useful review interface around the existing GLB:

- Timeline scrubbing, frame stepping at the recorded sample interval, playback
  speed, optional loop, and a visible duration.
- Object selection, search, highlight, isolate, and focus camera. Build these
  against durable object IDs, with display names kept separate.
- Camera bookmarks: overview, robot, work area, and author-defined views.
- Useful initial framing that can exclude oversized floors and hidden helpers.
- Loading progress, understandable error states, keyboard controls and a layout
  that remains usable in a small browser panel.
- A persistent recorded-playback label and a compact compatibility summary.

Selection and isolation change only the view. A reset-view control restores the
presentation; Restart resets playback without unexpectedly resetting the camera.
Seeking after the clip ends must work correctly, including at non-unit speed.

Three.js documents time seeking and speed scaling through AnimationMixer, so
reuse that runtime rather than build another animation engine. Exact control
semantics still require our tests against the pinned build.
[AnimationMixer documentation](https://threejs.org/docs/pages/AnimationMixer.html).

### B. Guided demonstrations: the strongest early differentiator

Add a small presentation editor that saves a separate `experience.json`:

- Chapters such as “Load”, “Inspect”, “Transfer”, and “Result”.
- Camera moves, captions and object highlights at authored timestamps.
- Clickable labels anchored to stable objects, following their recorded motion.
- A choice of **Explore**, **Guided demo**, and later **Engineering review**.
- A URL fragment containing the clip, timestamp and selected object, so a user
  can point someone to a moment in an already-hosted package.

Example: a 45-second robot recording becomes a self-guided demonstration. At the
inspection chapter, playback pauses, the camera frames the workpiece, and a
caption explains the recorded result. The visitor can leave the tour and orbit
freely at any point. The tour is authored presentation data, not a new simulation.

This is a product hypothesis: it should make exported runs more understandable
than the current minimal player. Validate that with a person unfamiliar with the
scene before expanding the editor.

### C. Engineering review: add evidence to the scene

Later, offer synchronized event and scalar-data tracks from explicit adapter
hooks. Examples are controller state, a recorded classification result, measured
joint position, a contact event, or a cycle counter when the source exposes it.

Use simulation timestamps, units, source identifiers and missing-data markers.
Seeking must reconstruct the display from the timestamp rather than repeatedly
firing accumulated events. Do not infer force, collision, success or root cause
from animation alone. An absent source measurement stays absent.

The first review feature should be clicking an event to jump to that moment.
Charts and comparisons follow once the clock and provenance contract is tested.

### D. Optional LLM customization

The LLM edits the experience, using the exact exported assets and animation.
Examples: “make a customer tour”, “highlight the gripper during pickup”, or “add
an explanation beside the inspection station”.

Ship a compact customization kit: schema, complete object catalog, camera
bookmarks, event descriptions, a readable player API, source template, examples,
and validation commands. Suggested API operations are `seek`, `play`, `pause`,
`focusObject`, `selectObject` and `setCamera`; these are proposed interfaces.

Prefer schema-validated JSON for ordinary changes. A custom-code template can
support advanced experiences, with the same package and playback tests run after
editing. Unsupported object IDs and timestamps should produce actionable errors.
No API key or remote model is required in a delivered package. A model-based
explanation must distinguish recorded evidence from interpretation.

## 4. Technical architecture

Keep this independent repository and the GLB/Three.js route. Reuse the installed
Isaac converter and existing capture code. Add small modules around proven
interfaces; do not introduce another conversion backend without a failing case
that justifies it. [Route evidence](ROUTE_DECISION.md).

```text
Isaac project / loaded stage / saved animated USD
    -> preflight + explicit capture adapter
    -> isolated recorded scene + provenance
    -> GLB conversion + identity reconciliation
    -> optional optimization + revalidation
    -> manifest + object catalog + optional events/experience
    -> bundled player + report + folder/ZIP
    -> ordinary static HTTP hosting
```

The product has four reusable parts:

1. **Capture core:** version checks, inputs, timing, lifecycle, project callbacks,
   and a normalized recording/report. Record failures and cancellation clearly.
2. **Package builder:** conversion, dependency checks, identities, optimization,
   notices, schemas, output validation and archive creation.
3. **Player:** exact playback, navigation, selection and presentation features.
4. **Authoring surfaces:** first CLI/config, then an Isaac extension calling the
   same core. An optional browser editor changes presentation data only.

Proposed repository organization, migrated incrementally with passing fixtures:

```text
src/isaac_web_exporter/
  capture/           # stage and bootstrap adapters, timing, lifecycle
  conversion/        # independent USD copy, converter, identity mapping
  packaging/         # manifest, ZIP, dependencies, reports, validation
  cli.py
web/
  player/            # move proven checkpoint1/web here
  editor/            # small experience editor, added only when needed
extensions/
  isaac.web.exporter/ # optional Isaac/Kit UI, same Python core
schemas/             # versioned package and presentation contracts
examples/            # owned fixtures and separate project adapters
tests/               # export, playback, negatives and performance fixtures
docs/                # installation, compatibility, hosting, evidence
tools/               # repeatable build and release checks
```

Keep generated recordings, vendor experiments and outputs outside tracked source.
Preserve v0 package loading when the package schema advances.

### Identity is the key prerequisite

Use source prim path plus an asset namespace as the starting identity, with
explicit overrides when identities must survive source restructuring. Carry or
reconcile that identity through the converter into GLB node metadata and the
catalog. Converter preservation of custom metadata is an experiment, not an
assumption; deterministic names in the export copy are a fallback to test.

Support repeated names in separate robots, all selectable static objects, and
one-to-many mappings where conversion splits a source object. Validate mapping
after any optimization. Do not merge independently animated or inspectable parts
unless their identity and behavior can be preserved.

### Optimize measured bottlenecks

Collect draw calls, triangle counts, texture dimensions, load time, frame times
and available memory estimates before selecting an optimization. Compare
identical camera paths and timestamps. A smaller download does not establish a
higher frame rate.

Try unused-resource removal and deduplication first. Then evaluate texture
resizing, static batching/instancing, animation-key reduction and geometry
compression. Make lossy changes opt-in and show the measured quality/size tradeoff.
Recheck node IDs, channels and intermediate poses after every transformation.

glTF Transform documents inspection and these optimization families. Three.js
documents Meshopt/KTX2 integration; ship any required decoders locally and verify
their compatibility with our locked version. No compression ratio or frame-rate
improvement is promised before a fixture benchmark.
[glTF Transform CLI](https://gltf-transform.dev/cli),
[Three.js GLTFLoader](https://threejs.org/docs/pages/GLTFLoader.html).

### Make export usable out of the box

Provide a reproducible build and an exporter distribution with a prebuilt player,
so every exporter user does not need to install Node or copy build directories.
Add preflight diagnostics, saved presets, progress, cancellation, local preview
and ZIP creation. Keep local-machine paths in private diagnostics rather than
public manifests; package source-asset notices and provenance appropriately.

The Isaac panel should offer: input/selection, duration/sample rate, quality,
Record, Export, Preview, and the report. Register capture with supported update
callbacks; do not assume the existing blocking command can run unmodified inside
an interactive Kit window. Test cancellation and stage/app ownership carefully.
Kit's documented extension mechanism provides the UI integration route, but the
complete panel has not been tested in our pinned Isaac build.
[Kit extension documentation](https://docs.omniverse.nvidia.com/kit/docs/kit-manual/latest/guide/extensions_advanced.html).

## 5. Delivery sequence and rough effort

These are **incremental active engineering hours from today's v0**, including
implementation and focused verification. They are planning ranges for one agent
with developer review, not measured model runtimes or guaranteed elapsed hours.
Machine access, external feedback and hardware availability can add elapsed time.
Re-estimate after each gate; capture and material surprises may exceed the ranges.

| Milestone | Deliverable and acceptance gate | Rough hours |
|---|---|---:|
| 1. Reproducible foundation | Freeze a local v0 baseline; move player into `web/player`; single build/export/validate path; locked dependencies and owned sample; fresh checkout works without ignored build files. | 8–16 |
| 2. Replay Studio preview | Timeline, speed/loop, tested seeking, camera bookmarks, better framing, scene tree and basic selection. Prototype durable identities and validate two repeated names. Existing playback and v0 packages keep working. | 16–28 |
| 3. Real workflow and identity hardening | One 30–60 s multi-object articulated workflow plus an unrelated project; complete object catalog; nested motion, rotation-only motion, duplicate names and static mode. Compare intermediate world poses, not only endpoints. | 24–48 |
| 4. Performance and visual quality | Profile representative scenes on a named integrated-GPU laptop; implement measured optimizations and material diagnostics; check image references at selected times. Retain an unoptimized reference. | 16–32 |
| 5. Turnkey authoring and guided demo | Thin Isaac panel with preflight/progress/cancel, preview/ZIP; a simple chapter/camera/caption editor. A new user exports an owned sample without source edits or chat guidance. | 16–32 |
| 6. Customization and beta hardening | Versioned experience schema/API, optional editable template, three validated customization examples, distribution/notices, install instructions and wider browser checks. | 16–32 |

**First visible upgrade:** milestones 1–2, about **24–44 active hours**.
**Proposed reusable beta:** milestones 1–6, about **96–188 active hours** before
contingency. This is substantially broader than the completed minimal v0.
Telemetry, comparison and the experimental ideas below are outside these totals.

Use short feasibility gates rather than spend the entire budget on an uncertain
feature. In milestone 3, first prove full articulated capture and converter ID
preservation. In milestone 4, first identify the actual rendering bottleneck. If
either fails, report the failing fixture and revised scope before expanding UI.

The factory may be a read-only workflow fixture through an adapter in this repo.
If its full process requires unsupported spawn/despawn or visibility, expose that
as a separate capture requirement. Do not simplify the process silently and then
describe it as a full recording. Use an owned fixed-population workflow to prove
the reusable beta independently.

## 6. Beta acceptance: what “complete” will mean

- A new user follows the documented install and exports the owned reference
  workflow without modifying exporter code. Custom projects may still need an
  explicit controller/bootstrap hook; that is an advertised interface.
- Two independent projects pass through the same core, including one 30–60 s
  articulated run with multiple moving objects. Source workspaces remain unchanged.
- Pause, Restart, seek, step, speed changes, end-of-clip behavior and camera
  independence pass a common browser suite. Report source-vs-browser translation
  and rotation errors at intermediate samples and interpolation points.
- Object selection, captions and camera targets remain correct after conversion,
  optimization, re-export and duplicate-name fixtures.
- A copied ZIP extraction works under a nested static URL with external network
  requests blocked. All runtime assets and any compression decoders are local.
- Test Chromium and Firefox on a named desktop configuration, and Chromium on a
  named integrated-GPU laptop. Safari/mobile remain unsupported until tested.
- Proposed reference target: median at least 30 fps and p95 frame time at most
  50 ms during a 60 s run at a fixed 1280×720 viewport on that laptop. Measure cold
  load separately under stated network/cache conditions. Targets are not achieved
  claims; gate the chosen supported scene budget on real measurements.
- Visual review checks shape, orientation, textures, lighting approximations and
  material fallbacks against valid Isaac reference frames. Pixel equivalence is
  not required; known differences are listed by affected object/material.
- Missing assets, unsupported required features, invalid customization data and
  cancelled conversion produce a clear report, never a false successful package.
- Owned examples, required notices, version pins and release instructions are
  ready. Any external publication remains a separate user decision.

## 7. Bigger ideas worth keeping beyond beta

| Idea | User value | Main dependency / uncertainty |
|---|---|---|
| Failure capsule | Attach a short replay, metadata and timestamped observations to a bug report; a colleague opens it without Isaac. | Provenance, privacy-aware export selection, and useful recorded events. Not enough to rerun the simulator by itself. |
| Compare two runs | Synchronized playback or ghost overlays show different trajectories and timings. | Stable shared IDs, world alignment and an explicit time/event alignment rule. The difference does not establish causation. |
| Click a chart, inspect the moment | Joint or task-state plots seek and focus the 3D view. | Explicit recorded telemetry with the same simulation clock. |
| Automated demo director | Suggest camera shots, chapters and captions from object motion and authored events. | Heuristics/LLM output needs preview and approval; occlusion and semantic errors are likely initially. |
| Training walkthrough | Guided chapters, object questions and recorded success/failure branches. | Content authoring; each branch is an existing clip, not a newly simulated outcome. |
| CI replay artifacts | A simulation test produces a portable review package for each selected run. | Reliable headless capture, storage budgets and export failure handling. |
| Shareable scene reader | Drag a package into a locally hosted reader, without manually starting a server for every package. | Browser archive/asset handling and memory constraints need a prototype. This does not imply universal `file://` support. |

These are untested product ideas. Prioritize failure capsules and event-driven
review after the beta because they reuse recording, IDs and the timeline. Test
interest with real reviewers before building accounts, collaboration services or
a hosted platform.

Defer arbitrary MDL/RTX parity, general particles/deformables, unrestricted
spawn/despawn, automatic reconstruction of every controller, and live browser
physics. Each changes the technical scope substantially. A live physics tier
would need its own behavior contract and plan.

## 8. Recommended immediate work order

Start with milestones 1–2: a reproducible foundation and a visibly better replay
experience. Keep the exact same GLB recording path while improving its packaging,
identity contract and player. Review that result before committing the larger
capture, performance and authoring budget.

Nothing in this document authorizes publishing, modifies the cheese-factory
project, or claims the proposed capabilities already exist.
