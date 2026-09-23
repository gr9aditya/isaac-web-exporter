# Isaac Web Exporter v1 — implementation brief and completion checklist

Date: 2026-09-23  
Status: implementation in progress; see `V1_ACCEPTANCE.md` for verified gates.
Starting point: working, user-reviewed v0 in this independent repository.

## Copy this instruction to the implementation agent

> Implement `V1_IMPLEMENTATION_PLAN.md` in this repository. Complete the full
> mandatory checklist, maintain the acceptance evidence, and continue through
> implementation, testing, fixes and handoff until v1 is ready locally. Do not
> stop after planning, a prototype, a milestone, or passing only part of the
> checklist. Mark an item complete only when its acceptance criteria are verified.
> Do not silently reduce scope, replace a required test with a weaker one, or
> label skipped/blocked tests as passes. Keep the cheese-factory project read-only.
> Do not push, publish or deploy externally. If a genuine external blocker prevents
> completion, finish independent work, preserve the incomplete checklist, and
> report the exact blocker and what is needed to resume; do not claim v1 is ready.

This is an execution brief when explicitly invoked by the user. Creating or
reading this document alone does not start implementation. Routine implementation
decisions do not need milestone-by-milestone approval. Keep the user informed with
concise progress updates and preserve progress across context/session handoffs.
For v1 execution, this brief defines scope and stopping criteria; the roadmap's
suggestion to review after the first two milestones is not a mandatory pause.

## 1. Product goal and fixed v1 scope

**An Isaac developer can record a supported project, export a self-contained
browser package, preview it, and give it to someone who can explore the recording
without Isaac, Docker, a live GPU server, an RTX GPU, or an LLM.**

The v1 experience includes:

1. Reusable export from a project bootstrap, a saved USD, or an already-loaded
   Isaac stage, with an explicit static mode for scenes without animation.
2. A polished player with Start/Pause/Restart, seek, frame stepping, speed,
   optional looping, camera navigation/bookmarks, and object inspection.
3. A simple guided-demo editor for chapters, captions, camera views and labels.
4. An Isaac export panel with preflight, progress, cancellation, preview and ZIP.
5. A documented package contract and optional LLM customization kit.
6. Repeatable installation, validation, browser tests and a local release bundle.

The supported motion subset remains fixed topology and object population, static
material bindings, rigid bodies, articulated-link transforms, and authored USD
transform animation. A project whose Python controls build or drive the scene may
need a documented adapter. Reusability does not mean automatically discovering
every project's launch procedure.

Playback and guided chapters show recorded results. They do not execute Isaac
physics, controllers, sensors, ROS or arbitrary project code in the browser.
Export developers need the tested Isaac environment; recipients need a supported
browser and static HTTP hosting. Do not require direct `file://` loading.

### Explicitly beyond v1

Telemetry charts, synchronized comparison of two runs, automated LLM narration,
account systems, hosted collaboration, live browser physics, arbitrary MDL/RTX
parity, deformables, particles, general spawn/despawn, animated material binding,
and guaranteed mobile/Safari support are future work. Tour markers are included;
a general sensor/event capture system is not. Do not add these to the mandatory
checklist or use them to postpone the agreed v1 delivery.

## 2. Starting evidence and repository rules

Read these local files before coding:

- [README.md](README.md): current commands and supported inputs.
- [V0_ACCEPTANCE.md](V0_ACCEPTANCE.md): measured v0 behavior and known limits.
- [ROUTE_DECISION.md](ROUTE_DECISION.md): tested GLB/Three.js decision.
- [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md): broader product direction.
- [ENVIRONMENT_EVIDENCE.md](ENVIRONMENT_EVIDENCE.md) and
  [toolchain.lock.json](toolchain.lock.json): environment and pinned dependencies.
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md): historical v0 plan, not a
  reason to revert the successful implementation to USDZ.

Current local workspace:
`C:/Users/adity/Documents/ChatGPT/isaac-web-exporter 2`.

Current source entry points:

- `src/isaac_web_exporter/export.py`
- `src/isaac_web_exporter/validate_package.py`
- `checkpoint1/web/src/main.js`
- `examples/`, `tests/`, `tools/`

At handoff, v0 uses Isaac 6.1, Kit 110.3.0, OpenUSD 25.11, Asset Converter 6.0.5,
Three.js 0.185.0 and Vite 6.3.0. These are recorded observations, not proof that the
remote workstation is still reachable. Recheck access, versions and mounts. Do
not print credentials, copy private keys into the repository, or install an
unrelated USD Python distribution into Isaac's runtime.

Keep development in this repository and an isolated remote exporter workspace
when needed. Never modify, commit, reset, clean, push or otherwise change
`/home/ubuntu/cheese-factory-challenge` or its service. A factory fixture must be
mounted read-only, with its adapters and outputs in the exporter workspace.
Do not disturb unrelated running containers. Preserve user changes.

Local milestone commits in the exporter repository are appropriate. Inspect
untracked files before creating a baseline; do not blindly stage generated assets
or secrets. No external push, repository creation, publication or deployment is
part of this brief. Generated release ZIPs may be built locally.

### Important v0 limitations to resolve or preserve honestly

- Object mapping currently relies on unique captured leaf names and covers
  captured rigid bodies rather than every selectable object.
- The player selects the first animation clip and has no timeline or tour editor.
- The exporter and validator currently reject static-only scenes.
- The factory test was a two-second single-object conveyor movement, not the full
  factory process; it was approximately 25 MB and ~8 observed fps on SwiftShader.
- Integrated-GPU laptop performance and Firefox/Safari were not established.
- The attempted Isaac RGB reference capture returned empty data. It is not visual
  comparison evidence. New valid reference frames are required for v1.

## 3. Architecture and implementation order

Keep GLB and the bundled Three.js player. Reuse the successful capture and
converter path. Introduce modules incrementally while preserving passing v0
fixtures. An Isaac fork and a second production conversion backend are not part
of v1.

```text
Isaac stage / project adapter
  -> preflight + simulation-time capture
  -> isolated export scene + identity mapping
  -> GLB conversion + optional measured optimization
  -> validate scene, motion, metadata and local dependencies
  -> player + manifest + object catalog + experience + reports/notices
  -> folder / ZIP -> static hosting -> browser
```

Suggested layout; equivalent small, maintainable module boundaries are acceptable:

```text
src/isaac_web_exporter/{capture,conversion,packaging}/
src/isaac_web_exporter/cli.py
web/player/
web/editor/
extensions/isaac.web.exporter/
schemas/
examples/
tests/
docs/
tools/
```

Work in the checklist order: establish a reproducible baseline, prototype object
identity and player controls, harden capture, measure/optimize, add authoring UI,
then finish the customization and release gates. A technical discovery may change
the internal implementation order; record it without dropping requirements.

Investigate uncertain boundaries early: ID preservation through the converter,
articulated and nested motion, interactive Kit capture without reentrant update
loops, reference-frame capture, and access to the required test hardware.

## 4. Package and playback contracts

Define versioned schemas for the manifest, object catalog, compatibility report,
and `experience.json`. The latter contains presentation data, not a replacement
scene or newly invented motion. Keep the GLB authoritative for geometry,
hierarchy, materials, transforms and recorded animation.

The object catalog must contain all supported selectable objects, their display
names, source identities, parent relationships and GLB mappings. Use source prim
path plus a namespace, or a tested equivalent. Stability is required for repeated
exports of the same source structure, not arbitrary source renaming. Allow explicit
IDs if a developer needs identity across source reorganizations.

Do not depend on leaf-name uniqueness. Test converter metadata preservation; if
needed, use deterministic export-only names and an explicit mapping. A source
object may map to several converted nodes. Test mapping after optimization and
never merge independent moving/selectable parts at the expense of correctness.

Player behavior:

- Initially show the first frame paused. Start resumes; Start at the end plays
  from the beginning. Pause freezes the playhead. Restart seeks to the start and
  plays, preserving the current camera unless a guided chapter explicitly owns it.
- Seek uses clip-relative seconds and works before play, while playing, after
  pause and after completion. Seeking preserves playing/paused state.
- Frame step pauses playback and moves to the adjacent recorded sample time,
  clamped to clip boundaries. Support variable sample intervals explicitly.
- Speed options include 0.25x, 0.5x, 1x and 2x. Changing speed must not jump time.
- Loop is off by default. No-loop playback stops at the final frame.
- Static mode presents the scene and navigation with inactive or hidden playback
  controls; a static scene is not treated as a failed recording.
- If a source has multiple clips, allow explicit selection and record the selected
  clip in presentation state. Do not silently play an arbitrary first clip.
- Invalid URLs, object IDs, schemas or timestamps produce a clear error/fallback
  appropriate to the problem. Mandatory missing scene assets cause failure.

Proposed package contents:

```text
index.html
assets/                       # bundled player, styles, local decoders if used
scene.glb
manifest.json
scene-map.json                # complete versioned object catalog
experience.json               # default presentation; optional custom content
compatibility-report.json
THIRD_PARTY_LICENSES/
README.txt
LLM-HANDOFF.md
customization/                # readable API/schema/examples or companion kit
```

Exact names may evolve with a documented schema migration. Preserve loading of
v0 packages. New features unavailable in old packages should degrade clearly;
do not invent source IDs or mutate the original package to claim compatibility.

## 5. Evidence and checklist discipline

All **66 checkboxes** below are mandatory for **v1-ready**. All begin unchecked. Existing
v0 evidence is a baseline, not an automatic pass for modified v1 code.

Create `V1_ACCEPTANCE.md` with one row per checklist ID containing:

`ID | status | acceptance result | command/test/manual steps | evidence path | tested revision/build | limitation`

Use `TODO`, `IN_PROGRESS`, `PASS`, `FAIL`, or `BLOCKED`. Only `PASS` allows `[x]`.
For documentation items, cite the document and how its procedure was checked.
For runtime claims, save logs, screenshots, measurements or machine-readable test
results. Do not mark a feature done because its code exists, a build passes, or a
different feature's screenshot looks correct.

Keep machine-readable results and large captures under ignored `runs/v1/` (or an
equivalent output directory). Keep the acceptance summary and reproducible test
commands tracked. Record artifact hashes and fixture/environment versions. If code
changes invalidate prior evidence, reopen and rerun the affected gate. Do not
repeat unrelated passing checks without a reason.

### A — Baseline, installation and build

- [x] **A01** Inspect repository instructions, Git state and existing source; preserve user work and record the actual v0 baseline in a local commit when possible.
- [x] **A02** Verify an isolated, compatible Isaac export environment and required browser/hardware access; record versions, ownership and read-only fixture mounts.
- [x] **A03** Move the maintained player out of `checkpoint1/` into the production layout; update scripts/imports/ignore rules and keep historical evidence intact.
- [x] **A04** Provide a single documented player build and exporter packaging flow using locked dependencies; include the prebuilt player in the local exporter distribution.
- [x] **A05** A fresh checkout plus documented dependencies can build and run without ignored artifacts, ad hoc copies from prior runs, or hardcoded workstation paths.
- [x] **A06** Install the built exporter distribution into a clean compatible environment; export and validate an owned sample without requiring the exporter user to build frontend assets.

### B — Object identity, schemas and package integrity

- [x] **B01** Add versioned manifest, object-catalog, report and experience schemas with clear validation messages and a documented compatibility policy.
- [x] **B02** Map source objects to GLB nodes without leaf-name uniqueness; two branches with identically named objects remain separately selectable and correctly animated.
- [x] **B03** Include supported static and moving selectable objects, parent relationships, display names and one-to-many conversion mappings in the catalog.
- [x] **B04** Prove identity stability across two exports of unchanged source structure and across enabled optimization passes; invalid mappings fail validation.
- [x] **B05** Record mode, units/axis conventions, clip timing/sample times, versions, hashes and conversion approximations without exposing private host paths or credentials in the shared package.
- [x] **B06** Extend validation to schemas, package-contained paths, local resources, identities, animation/static mode and presentation references; malformed input produces a structured failure.
- [x] **B07** Load an unchanged v0 package in the v1 player and document which newer features are unavailable without its new metadata.

### C — Capture correctness and representative projects

- [x] **C01** Preserve bootstrap, saved animated USD and already-loaded stage inputs using the same reusable core; retain documented controller callbacks.
- [x] **C02** Add an explicit static scene mode that exports and validates successfully without fabricated animation.
- [x] **C03** Export an owned 30–60 second articulated workflow with multiple moving objects and a visible task sequence; a scripted joint trajectory is acceptable when accurately described.
- [x] **C04** Export a second unrelated project through configuration/adapter code without changing the exporter core; it exercises different hierarchy and motion characteristics.
- [x] **C05** Verify nested moving parents/children, non-identity parent transforms, rotation-only motion, repeated names, non-default units and supported up-axis conversion with focused fixtures.
- [x] **C06** Compare source and browser world transforms at first, last and at least ten interior recorded samples plus interpolation points; report position and rotation errors using the tolerances below.
- [x] **C07** Preserve authored clip ranges and explicitly handle multiple clips; source and browser duration match within the defined timing tolerance.
- [x] **C08** Capture/export leaves source files and caller-owned app/stage ownership intact; cancel and failure do not close a caller-owned Isaac app or save export-only edits into its stage.
- [x] **C09** Unsupported required motion/features and missing dependencies yield actionable errors or explicitly documented approximations; a required moving object may not silently disappear or become static.

### D — Replay player

- [x] **D01** Start, Pause, Restart and initial/end states follow the playback contract, including restart after reaching the end and camera independence.
- [x] **D02** Add a scrubber, elapsed/duration display and seeking that works while paused/playing, after completion, and at every supported playback speed.
- [x] **D03** Add backward/forward sample stepping, 0.25x/0.5x/1x/2x speed and optional looping; test boundary times and state transitions.
- [x] **D04** Keep orbit/pan/zoom, add reset view and camera bookmarks, and avoid unusable framing caused by oversized floors/helpers.
- [x] **D05** Add a searchable object tree/catalog and click selection, highlight, isolate and focus; repeated names and moving descendants target the correct objects.
- [x] **D06** Provide clip selection when needed, static-mode UI and readable compatibility information, with the recorded-playback distinction visible.
- [x] **D07** Add loading/progress/error states, keyboard operation, clear focus indicators and usable layouts at 480px and 1280px widths; verify visible scene and controls in both.
- [x] **D08** Encode/restore clip, time and selection in a URL fragment for an already-hosted package; validate malformed references and avoid automatic external requests.

### E — Performance and visual fidelity

- [x] **E01** Establish repeatable unoptimized baselines: package size, cold load, draw calls, triangles, texture sizes, frame-time distribution and available memory estimates; label unavailable metrics honestly.
- [x] **E02** Profile the representative workflow and larger scene before optimizing; record the actual limiting resource rather than assuming file size explains frame rate.
- [x] **E03** Provide an opt-in optimization preset using measured applicable transformations; retain the source/reference output and prove identities, motion and acceptable appearance survive.
- [x] **E04** Bundle all decoders/transcoders locally if compression requires them; check their version compatibility and notices. Lossy options are explicit and reported.
- [x] **E05** Meet the integrated-GPU reference performance gate below on the representative workflow; record actual hardware, graphics backend, browser, viewport and settings.
- [x] **E06** Obtain nonempty Isaac reference images for the same fixture at first, middle and final times, match camera/pose, and review geometry, scale, orientation and portable materials against browser images.
- [x] **E07** Report material approximations by affected object/material, provide visible fallback or strict-mode failure, and document the supported material/texture subset. Do not promise arbitrary RTX equivalence.

### F — Isaac panel, preview and packaging

- [x] **F01** Add a thin Isaac/Kit export panel calling the shared core: source/selection, duration/sample rate, quality preset, output destination and recording/export actions.
- [x] **F02** Preflight reports incompatible versions, missing inputs/dependencies and invalid settings before expensive work where possible; selected roots are honored.
- [ ] **F03** Recording/conversion progress remains responsive in an interactive Isaac session; cancellation restores a usable panel and leaves no false-success package. Test cancel during capture and conversion.
- [x] **F04** Add saved export presets, local browser preview and folder/ZIP output. Preview binds locally; it is not an external deployment.
- [x] **F05** Extract a generated ZIP into a new directory and serve it under a nested static URL; the default player works without Node, Isaac or Docker on the recipient machine.
- [x] **F06** Exercise the actual panel in the tested Isaac build and save UI evidence; importing the extension or testing the CLI alone does not satisfy the panel gate.

### G — Guided demo authoring

- [x] **G01** Add a simple editor for chapter times/titles, captions, camera bookmarks/transitions and object-anchored labels/highlights; save versioned `experience.json`.
- [x] **G02** Support Explore and Guided demo modes. A user can leave the tour for free camera navigation and resume without corrupting the recording or playhead.
- [x] **G03** Seeking, restarting and looping reconstruct correct chapter/label state without duplicate actions or stale highlights; labels follow the selected object correctly.
- [x] **G04** Save, reload and apply presentation edits without re-exporting Isaac or changing the GLB hash; provide browser download/import of JSON and a documented way to update the package.
- [x] **G05** Ship one owned demonstration with at least three chapters, two camera views and a label on a moving object; verify invalid time/object references are reported.

### H — Optional LLM/developer customization

- [x] **H01** Ship `LLM-HANDOFF.md`, readable schemas/object metadata and an editable source template or companion kit; document geometry, animation, identity and coordinate conventions.
- [x] **H02** Expose a small documented player API for play, pause, seek, selection, focus and camera setting; customizations use the API instead of private checkpoint globals.
- [x] **H03** Include three working examples: visual theme/captions, an object-focused guided tour, and a custom information panel. Validate each against the same recorded assets.
- [x] **H04** Validate configuration changes and document tests for custom-code edits. The default package and all examples work without a model service, account or API key.

### I — Regression, portability and failure handling

- [x] **I01** Automate the critical browser playback/control/selection/tour checks against final built packages, not only the dev server or internal helper functions.
- [x] **I02** Verify Chromium and Firefox on a recorded desktop configuration, plus Chromium on the integrated-GPU reference laptop; save browser versions and rendering backend evidence.
- [x] **I03** With external network requests blocked, copied packages and their tour/customization examples load and operate; no required CDN, remote font, texture or decoder remains.
- [x] **I04** Missing texture/body, corrupt/truncated/tampered GLB, invalid schema/ID/time, nonexistent input, unsupported schema version and conversion failure produce clear failures without false success.
- [x] **I05** Interrupted/cancelled export, unavailable converter and existing output directory are handled safely; no silent overwrite or damage to previous successful packages.
- [x] **I06** Re-run relevant v0 regressions and all affected v1 gates after final changes; record unresolved issues and do not classify a required failed test as a known harmless limitation.

### J — Documentation and local v1 release

- [x] **J01** Write installation, one complete export workflow, panel usage, hosting, customization, troubleshooting and supported-feature documentation; commands and paths match the release.
- [x] **J02** Perform a clean-room walkthrough using only the documented steps in a fresh compatible environment. Record any fixes; distinguish this agent-run test from external novice-user feedback.
- [x] **J03** Include dependency notices and asset provenance; use owned or expressly redistributable samples in the release bundle. Private factory/uncleared stock assets stay outside it.
- [x] **J04** Record the project's license status. Do not invent the user's licensing choice; if no source license is selected, label the deliverable local/private and defer public release while preserving dependency obligations.
- [x] **J05** Build a versioned local v1 exporter/player distribution and example ZIPs; record hashes, toolchain lock, supported Isaac version and exact build commands.
- [ ] **J06** Finish `V1_ACCEPTANCE.md` with every required ID passing and evidence available; create `V1_RELEASE_NOTES.md` describing supported scope and remaining out-of-scope limits.
- [x] **J07** Create coherent local exporter commits, report the final tested code revision and evidence revision, and verify no generated assets/secrets or cheese-factory changes were included.
- [x] **J08** Open the final representative package locally for review and deliver the summary, commands, artifact locations, hashes, test results and limitations. Do not push or publish.

## 6. Quantitative acceptance details

### Motion and timing

For owned reference fixtures, use meter-normalized world coordinates. At recorded
sample times, maximum translation error must be <= 1 mm and maximum orientation
error <= 0.5 degrees. Compare quaternion orientation using the shortest equivalent
rotation, not raw quaternion component differences. For scale, require <= 0.1%
relative error, using an absolute tolerance of 0.000001 near zero.

At interpolation points, compare against the recording's documented interpolation
contract. Report separately whether the captured sample density approximates the
live source motion adequately; browser interpolation cannot recover unrecorded
physics. Set clip-duration error <= 0.001 seconds. Check actual represented object
motion in the browser, not just the UI timer.

If these targets reveal a genuine conversion limitation, investigate and fix it.
Do not increase tolerances after seeing failures merely to mark a pass. A material
scope/tolerance change requires an explicit user decision and an updated plan.

### Performance and browser coverage

Use the complete 30–60 second representative articulated workflow, including its
intended scene context, at a fixed 1280x720 viewport and documented pixel ratio.
For a 30-second clip, repeat it for a 60-second measured playback window. On a
named laptop using its actual integrated GPU, require median frame rate >= 30 fps
and p95 frame interval <= 50 ms after loading/shader warm-up. Record three runs
and the range; do not discard slow runs without an explained measurement fault.

Measure cold load separately with stated cache/network conditions. Software
rendering is an additional useful stress test, not a substitute for integrated
GPU evidence. Do not replace the representative workflow with a falling box to
pass this gate. Report the tested scene budget and make no universal performance
claim for arbitrary factories.

If the required device or Firefox/interactive Isaac access is unavailable, flag
that early, continue independent work, and leave the relevant items `BLOCKED`.
An unmeasured platform cannot be marked supported. The user can explicitly amend
this gate; the agent cannot waive it on its own.

## 7. Definition of done and stopping rule

**v1 is ready locally only when every mandatory checkbox A01–J08 listed above is
checked with its own passing evidence, all final required tests pass on the
delivered build, and the local artifacts and handoff are complete.** The ID ranges
vary by section; use the actual listed items, not invented intervening IDs.

Do not stop merely because:

- the player looks finished or an isolated demo works;
- code is written but capture, packaging or UI has not been exercised;
- one milestone is done;
- the initial time estimate has been consumed;
- a required validation is inconvenient or depends on another environment.

If blocked externally, investigate safe alternatives first and finish all useful
independent tasks. Then report: incomplete IDs, exact failed/unavailable resource,
evidence, attempted recovery, and the smallest action needed to resume. Do not
claim completion, repeatedly retry unchanged failures, or conceal the blocker.
If interrupted, write a concise resumption note with the current revision,
checklist state, running services and next action so the next session can continue.

The requested persistence is an execution instruction, not a guarantee that a
single agent session has unlimited runtime or access to missing hardware.

Final handoff must state either **V1 READY — all mandatory gates passed** or
**V1 INCOMPLETE — remaining IDs and blockers**. A user-requested scope amendment
must be recorded explicitly; it must not disappear into release notes.

## 8. Effort guidance and sources

The roadmap estimated 96–188 incremental active engineering hours for its broader
beta, before contingency. This checklist formalizes that scope as v1 and makes
its tests more explicit; re-estimate after the initial audit. It is not an
8–16-hour extension of the tiny v0 or a guaranteed model runtime. Prefer reuse,
small interfaces and focused tests over building a new framework.

Official sources supporting candidate implementation techniques; verify against
the locked toolchain before adding dependencies:

- [Three.js AnimationMixer](https://threejs.org/docs/pages/AnimationMixer.html): seeking and playback time scaling.
- [Three.js GLTFLoader](https://threejs.org/docs/pages/GLTFLoader.html): GLB loading and optional decoder integration.
- [glTF Transform CLI](https://gltf-transform.dev/cli): inspection and optimization options; suitability must be measured on our assets.
- [Kit extensions](https://docs.omniverse.nvidia.com/kit/docs/kit-manual/latest/guide/extensions_advanced.html): extension packaging and lifecycle.

Verified facts come from the v0 evidence and source audit. The v1 capabilities,
performance targets, UI design and ID-preservation strategy above remain
requirements or untested proposals until their checklist evidence is produced.
