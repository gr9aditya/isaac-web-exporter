# Cheese-factory full-visual workflow export

This is the full-visual browser package exported from the recorded 11-item
camera/model run of the [Swiss AI Weeks cheese-factory challenge](https://github.com/Swiss-ai-Weeks/cheese-factory-challenge).
It contains the factory scene, robot geometry, embedded imagery, recorded
motion, and guided run outcomes. The user authorized redistribution of this
export on 2026-09-24.

The recording lasts 72.783 seconds and has 12 guided chapters: preparation
and one chapter for each item. The original run had **4 of 11 end-to-end
successes**. Its other outcomes are preserved in the captions. Playback is a
recording of the actual camera/model run, not live Isaac physics or a live
model call. The source project, model weights, raw camera frames, and source
USD are not bundled.

To view it, extract `package.zip`, serve the extracted folder with a static
HTTP server, and open `index.html`. The viewer offers Start/Pause/Restart,
seeking, camera navigation, object selection, and guided captions. The viewer
runs without Isaac Sim, Docker, an RTX GPU, or a live GPU server.

The PNGs in `screenshots/` show the package at recorded times 0, 35, and 70
seconds. `export-report.json` is the exporter report; `browser-check.json`
records the browser test of animation, controls, camera navigation, chapters,
and local-only resource loading.

Validation: the v1 package validator passed. The GLB contains 180 meshes,
211 materials, 16 embedded images, and one animation. `package.zip` is
8,858,099 bytes with SHA-256
`901918691a9e452e930620c6593eb0f5cd341c82e856b2a487221579a6590fb7`.
