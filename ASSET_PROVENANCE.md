# Asset provenance for v1 samples

The release samples built from `examples/falling_box.py`,
`examples/sort_cell_workflow.py`, `examples/static_gallery.py`,
`examples/twin_arms.py`, and `examples/centimeter_yup_cell.py` use geometry,
colors, material parameters, and motion authored specifically in this
repository. They do not import cheese-factory or stock Isaac assets.

The browser player embeds Three.js 0.185.0. Its MIT notice is shipped with
every generated package. Player CSS and exporter code are repository source;
no separate web fonts, decoder binaries, or CDN scripts are required.

The cheese-factory sample in `sample-exports/cheese-factory/` was generated
from a recorded 11-item camera/model run. Its browser package includes the
exported factory geometry, stock Franka geometry, and embedded source imagery.
The user explicitly authorized redistribution of this export on 2026-09-24.
The original project checkout, model weights, raw capture, and source USD are
not part of the sample. The package includes the bundled Three.js MIT notice.
