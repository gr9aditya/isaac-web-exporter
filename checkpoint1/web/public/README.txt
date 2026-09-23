Isaac browser exporter checkpoint 1

This is a static, recorded-playback proof using a small generated Isaac Sim scene.
It does not run physics in the browser. No Isaac Sim, Docker, or live GPU server is
needed by the viewer. The scene was authored and converted on an Isaac workstation.

Host this directory with any static HTTP server, then open its URL in a browser.
For example, from this directory: python -m http.server 8000
Opening index.html directly from a file:// URL is not supported.

Controls: Start, Pause, Restart; drag to orbit; right drag to pan; scroll to zoom.
manifest.json and scene-map.json provide machine-readable scene metadata.
compatibility-report.json states the exact scope of this checkpoint.

Third-party notice: THIRD_PARTY_LICENSES/three-MIT.txt
