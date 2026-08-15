# MapLibre GL JS

VisionEval Workbench vendors MapLibre GL JS 6.0.0 for offline interactive maps.
The upstream project is https://github.com/maplibre/maplibre-gl-js and is
licensed under the BSD 3-Clause License. See `LICENSE.txt` in this directory.

`maplibre-gl.js` is the Workbench classic-browser distribution generated from
the pinned 6.0.0 npm `dist/` modules by `packaging/build_maplibre_classic.py`.
It embeds the MapLibre worker and exposes `window.maplibregl`, so the frozen
application does not perform module-relative JavaScript fetches at runtime.
