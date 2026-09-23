# Asset provenance for v1 samples

The release samples built from `examples/falling_box.py`,
`examples/sort_cell_workflow.py`, `examples/static_gallery.py`,
`examples/twin_arms.py`, and `examples/centimeter_yup_cell.py` use geometry,
colors, material parameters, and motion authored specifically in this
repository. They do not import cheese-factory or stock Isaac assets.

The browser player embeds Three.js 0.185.0. Its MIT notice is shipped with
every generated package. Player CSS and exporter code are repository source;
no separate web fonts, decoder binaries, or CDN scripts are required.

The cheese-factory source and stock Franka assets were used in private
compatibility/performance probes and a full 11-item model-run export. The
factory-specific adapter source is included here, but the project checkout,
textures, recorded USD/GLB, and browser package remain under ignored `runs/`
or on the isolated workstation. They are excluded from this public repository.
The exact source repository/license terms must be reviewed by the owner before
any third-party asset export is shared.
