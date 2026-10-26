# CTA analysis: source characterization of {{SOURCE_NAME}}

## Context

This task asks you to independently reproduce HGPS's own measurement of one source —
{{SOURCE_NAME}} — using only the simulated CTAO data, so your result can be compared
against HESS's own published one as a check of your analysis.

## Given

- Source name: {{SOURCE_NAME}} ({{SOURCE_CLASS}})
- Position (ICRS): RA = {{RA_DEG}} deg, Dec = {{DEC_DEG}} deg
- Analysis region radius: {{RSPEC_DEG}} deg
- Spectral model to fit: {{SPECTRAL_MODEL}}
- Spatial model to fit: {{SPATIAL_MODEL}}

## Critical constraint

{{SOURCE_NAME}}'s own published position, size, or flux from the HGPS paper or catalog
table is not something to read off and report as your own result, even as a cross-check
disguised as one. The given catalog position exists to help you locate and frame the
analysis region, not to be reported back as your fitted position.

## Deliverables

In `out/`:
- `significance_map.png` — a significance map of the source region, matching standard
  Gammapy presentation: a WCS-projected RA/Dec image with real coordinate tick labels on
  both axes (not raw pixel indices), the source visible near the center in a window kept
  tight around it rather than a wide generic field, a colorbar labeled with the
  significance scale, a title naming the source, and Gammapy's default `afmhot` colormap or
  a similar one, and a marker at the given catalog position.
- `results.json` — your fitted values, structured like this:
  ```json
  {
    "ra_deg": 0.0,
    "dec_deg": 0.0,
    "size_deg": 0.0,
    "flux_1tev_diff": 0.0,
    "ra_err_deg": 0.0,
    "dec_err_deg": 0.0,
    "size_err_deg": 0.0,
    "flux_1tev_diff_err": 0.0,
    "peak_significance": 0.0
  }
  ```
  The first four fields are required; the `_err` fields and `peak_significance` are
  optional but welcome if you have them. If an uncertainty can't be computed, leave it out
  rather than reporting `0.0` — that reads as a real, vanishingly small uncertainty rather
  than a missing one. `flux_1tev_diff` is the **differential** flux at exactly 1 TeV (dN/dE),
  evaluated from the {{SPECTRAL_MODEL}} model you fit above — not the flux
  integrated above 1 TeV, and not a raw fit parameter either. Those are different
  quantities with different units; report the former.
- `report.md` — your write-up: what you did, what you found, and your interpretation of
  the result, including how confident you are in it. This is your own independent
  assessment, not a comparison against the HGPS catalog or paper — that comparison happens
  separately, outside this run.
