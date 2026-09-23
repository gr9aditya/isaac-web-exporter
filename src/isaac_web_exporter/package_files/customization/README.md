# Customize the package

No model service or API key is needed. The default `index.html` already works.
The files in `examples/` are optional scripts for an owned sorting-workflow
package. To try one, add this tag before `</body>` in `index.html`:

```html
<script src="./customization/examples/theme-captions.js" defer></script>
```

Swap the filename for `focused-tour.js` or `object-info-panel.js` to try
those examples. Each waits for `window.isaacReplay.ready`. Use object IDs from
`scene-map.json` when adapting examples to another export. The API is:

```js
await window.isaacReplay.ready;
window.isaacReplay.play();
window.isaacReplay.pause();
window.isaacReplay.seek(3.5);                 // clip-relative seconds
window.isaacReplay.selectObject('/World/Products/PartA');
window.isaacReplay.focusObject('/World/Products/PartA');
window.isaacReplay.setCamera({position:[7,6,9], target:[0,0,0]});
window.isaacReplay.setExperience({schemaVersion:'v1.0', chapters:[]});
const state = window.isaacReplay.getState();
const experience = window.isaacReplay.getExperience();
```

`setExperience` validates and saves an override in this browser's localStorage.
For a shareable change, use the editor's **Download JSON**, replace
`experience.json` with the downloaded file, validate the package, and distribute
the new folder/ZIP. No Isaac re-export is required and the GLB hash stays the
same. The imported configuration must use valid clip times and object IDs.

To test a code edit, host the folder locally (for example `python -m
http.server 8000` from the package parent), visit its URL, exercise all
controls, then run `isaac-web-package-check <package-folder>` in a Python
environment with this exporter installed. Inspect browser console errors and
network requests. Avoid CDNs, remote fonts, remote decoders, and extra `file://`
dependencies. Never paste untrusted code into a package.
