# v0 format decision: animated GLB and local Three.js player

The existing `IMPLEMENTATION_PLAN.md` proposed trying USDZ with pinned USD Web
View first, then the installed Asset Converter/GLB route if needed. Both routes
have now been exercised; **GLB is the v0 package format**.

## Evidence

- Isaac 6.1's OpenUSD 25.11 `CreateNewUsdzPackage` packaged the explicit-pose
  falling-box recording. The USDZ reopened with 61 transform samples and a
  0–60 time-code range (`runs/usdz-probe-report.json`). Pinned USD Web View at
  commit `b050c3731d1854a5980b6b4fe55ec1725dc18f51` built with its lockfile,
  loaded that USDZ in Edge/SwiftShader in about 8.2 seconds, and displayed
  distinct poses at time codes 0, 30 and 60. The browser made no external
  requests and raised no page errors (`runs/usdz-webview-browser.json` and
  `runs/usdz-view-*.png`). USDZ is therefore a technically credible route for
  the controlled fixture.
- Packaging the actual factory recorded USD as USDZ failed with an unresolved
  `OmniPBR.mdl` dependency. The first attempt also lacked the project's `/project`
  mount and reported its label PNG paths; a second attempt included the project
  as a read-only mount and narrowed the failure to `OmniPBR.mdl`
  (`runs/usdz-factory-with-project.log` on the isolated workstation). This is
  a concrete portability blocker for that route without more material surgery.
- The installed Asset Converter produced self-contained animated GLBs from the
  falling box, an unrelated inspection cell, stock Franka, and the read-only
  factory scene (`ALPHA_CHECKPOINT_REPORT.md`, `FACTORY_PROBE_REPORT.md`). The
  static Three.js player passed Edge/SwiftShader checks with network requests
  blocked. The factory GLB retained 159 meshes, 189 materials and the moving
  object's two transform channels.

## Consequences

GLB/Three.js is the only production package format for the scoped v0. The USDZ
test remains a diagnostic comparison, not a second export backend to maintain.
The smaller player and demonstrated factory conversion make this the quickest
route to a reviewable v0. GLB still has important limits: MDL fidelity is not
guaranteed; texture, light, instancing, and nested-motion results need checks;
source asset rights must be reviewed before redistributing output. The local
factory and stock Franka packages are technical artifacts, not published samples.

The pinned USD Web View checkout under `third_party/usd-webview-eval/` is ignored
by Git and is not included in GLB packages. Its upstream UI also loops animation
at the end and lacks a separate Restart button, so product control behavior
would have required a wrapper or patch even where USDZ loaded successfully.
