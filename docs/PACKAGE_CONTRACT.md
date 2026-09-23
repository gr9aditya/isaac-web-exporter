# v1 package and compatibility contract

All v1 package paths are relative to the package root. The package is a static
HTTP website, with `index.html`, local `assets/`, `scene.glb`, four versioned
JSON files, `schemas/`, `THIRD_PARTY_LICENSES/`, `README.txt`,
`LLM-HANDOFF.md`, and `customization/`. A ZIP contains the same files without
an outer directory. A normal web server may mount it at any URL subpath.

The authoritative geometry, node hierarchy, static materials, and recorded
clip buffers are in the GLB. `manifest.json` records the GLB SHA-256, mode,
quality preset, source stage axis/units, Y-up viewer convention, clip sample
times in relative seconds, source application version, and selected roots.
`scene-map.json` gives object IDs and node-index mappings; IDs are namespaced
source prim paths for unchanged structures. A source object can map to several
converted nodes. Display names can repeat and must not be used as keys.
`compatibility-report.json` reports conversion warnings, material fallback or
approximation by object, and successful validation. `experience.json` holds
chapters, captions, views, object highlights and anchored labels. It never
overrides the GLB's physical motion.

The v1 schemas are shipped under `schemas/*.v1.schema.json`. The offline
validator checks the keywords used in those schemas, cross-file references,
hashes, animation times, identities, GLB structure, package-local URLs, and
missing required files. A malformed package fails with structured errors.
Unknown schema versions fail. The v1 player accepts unchanged v0
`alpha-0.1` packages for basic playback and captured-object selection; v0
lacks a complete catalog and packaged guided content. New features are not
inferred from absent metadata.

Recorded mode requires an animated GLB. Static mode requires no animation and
disables transport controls. Multiple GLB clips require the viewer to choose
one explicitly; the selected clip and playhead enter the share URL fragment.
URL fragments are local state, not external requests. Invalid clip/time/object
references fall back to a clear status message without loading remote assets.

Supported content is fixed topology/population, static material bindings,
rigid/link transforms and authored USD xform animation. USD PreviewSurface is
converted approximately to glTF PBR; unbound geometry receives a visible
default material. Bound unsupported shader types fail strict export with the
affected object/material. Animated non-transform properties fail. Browser
rendering is not pixel-identical to Isaac RTX.
