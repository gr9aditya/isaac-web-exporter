# Isaac Replay browser package handoff

This folder is a complete static website. Serve it with a static HTTP server.
Do not require an LLM, Isaac Sim, Docker, an RTX card, or a live GPU server for
the recipient. Browser playback is a recording; it does not run physics,
controllers, sensors, or project Python.

`scene.glb` is authoritative for meshes, hierarchy, materials, transforms,
and animation. `manifest.json` describes the mode, axes, source units, selected
clip timing, and asset SHA-256. `scene-map.json` maps stable source prim paths
to one or more GLB node indices; `experience.json` contains only optional
chapters, captions, views and labels. The `schemas/` directory is the v1 JSON
contract. Never infer object position or motion from a caption.

Source `sourceUpAxis` and `metersPerUnit` describe the original USD stage.
The GLB and player use Y-up meters. Animation times in the GLB and manifest
are clip-relative seconds. Select an object by its `id`, not its display name:
display names can repeat. IDs remain stable for unchanged source prim paths,
but renaming a source prim can change them.

Start with [customization/README.md](customization/README.md) and its three
working examples. The public `window.isaacReplay` API supports play, pause,
seek, selection, focus, camera views and presentation edits. Wait for
`window.isaacReplay.ready` before calling it. Keep all added code and assets
local; validate the edited package before sharing it.

Do not remove third-party notices. Review the rights of the source USD and
embedded textures before distributing a package; this demo repository is
local/private until its owner chooses a source license.
