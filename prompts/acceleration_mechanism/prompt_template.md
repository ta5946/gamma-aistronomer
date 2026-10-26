# CTA analysis: acceleration mechanism of {{SOURCE_NAME}}

## Context

Gamma rays above a few hundred GeV are produced by one of two mechanisms: leptonic
(relativistic electrons upscattering ambient photons via inverse-Compton) or hadronic
(relativistic protons and nuclei colliding with ambient gas, producing neutral pions that
decay into gamma rays). Both can produce power-law-like spectra over a narrow energy range,
so the two are not distinguishable from flux alone; the spectral shape at the high-energy
end is what's actually diagnostic. That diagnostic is indirect, not direct: the real
hadronic signature, the pion-decay "bump" around a few hundred MeV, sits well below the
energy range any IACT (including CTAO) can observe. Treat this analysis as evidence toward
one mechanism over the other, not proof, and ground your own account of what the spectral
shape implies (rather than asserting it) in `cognee_recall` and the literature.

HGPS already fit a single spectral shape (power law or exponential cutoff power law) to
{{SOURCE_NAME}} from real HESS data. This task goes further: using CTAO's own internal,
simulated data for the same source, extract flux points across several energy bins and
compare multiple spectral shapes against each other to test whether the data itself
prefers curvature or a cutoff, and interpret what that implies about the acceleration
mechanism at work.

## Environment

- `naima` (physical inverse-Compton/pion-decay models) isn't installed and isn't worth
  installing over the network within the runtime budget. Use Gammapy's own
  phenomenological models (power law, exponential cutoff power law, log parabola) as
  proxies for curvature instead.
- Prefer `FluxPointsEstimator`, `Fit`, and Gammapy's spectral model classes over
  hand-written equivalents.

## Given

- Source name: {{SOURCE_NAME}} ({{SOURCE_CLASS}})
- Position (ICRS): RA = {{RA_DEG}} deg, Dec = {{DEC_DEG}} deg
- Analysis region radius: {{RSPEC_DEG}} deg
- Spectral model HGPS itself settled on: {{SPECTRAL_MODEL}} — given for context on what
  shape real HESS data already favored, not a result to reproduce or assume
- Spatial model: {{SPATIAL_MODEL}}, size {{SIZE_DEG}} deg (a fixed input for defining the
  extraction region and any containment correction, not something to refit here)

## Critical constraint

{{SOURCE_NAME}}'s own published spectral index, cutoff energy, or curvature preference is
not something to read off and report as if it were your own result, even reframed or
rounded. Fit your own flux points from the CTAO data, fit your own candidate spectral
models to them, and let the comparison between those fits, not the paper's, drive your
interpretation.

The given position, region radius, and spatial model (including its size) exist to help you
define the same analysis region HGPS used, not to be reported back as results. Position and
size are not something to re-fit here: this task only asks for an independent fit of the
spectral shape, reusing the already-established geometry as a fixed input, the same way
`rspec_deg` fixes a circular aperture for spectral extraction regardless of a source's finer
spatial structure.

## Deliverables

In `out/`:
- `sed_comparison.png` — a spectral energy distribution plot of your extracted CTAO flux
  points (with error bars, and upper limits where a bin isn't significant), overlaid with
  the fitted power law, exponential cutoff power law, and log parabola curves, a legend
  naming each, log-log axes, and a title naming the source.
- `results.json` — your fitted values, structured like this:
  ```json
  {
    "preferred_model": "PL",
    "index_pl": 0.0,
    "index_pl_err": 0.0,
    "delta_ts_ecpl_over_pl": 0.0,
    "cutoff_energy_tev": 0.0,
    "cutoff_energy_err_tev": 0.0,
    "delta_ts_logparabola_over_pl": 0.0,
    "curvature_beta": 0.0,
    "curvature_beta_err": 0.0,
    "acceleration_mechanism_interpretation": "leptonic",
    "interpretation_confidence": "low"
  }
  ```
  `preferred_model` is whichever of `"PL"`, `"ECPL"`, or `"LogParabola"` your own fit
  statistically favors (report the delta-TS or delta-Cash-statistic you used to decide, not
  just an eyeballed judgment). `cutoff_energy_tev` and `curvature_beta` only make sense if
  ECPL or LogParabola is actually preferred; leave a field out rather than reporting a
  meaningless `0.0` when the corresponding model isn't preferred or a parameter is
  unconstrained. `acceleration_mechanism_interpretation` is one of `"leptonic"`,
  `"hadronic"`, or `"inconclusive"` — inconclusive is a legitimate, expected answer when the
  spectrum doesn't statistically prefer a curved model over a plain power law, or when a
  cutoff is present but too poorly constrained to interpret; do not force a leptonic/hadronic
  call the data doesn't support. `interpretation_confidence` reflects how strongly the
  statistics support that call, not how interesting the result is.
- `report.md` — your write-up: what you did, what you found, and your interpretation of the
  result, including the physical reasoning connecting the fitted curvature/cutoff (or lack
  of one) to leptonic vs. hadronic emission, and how confident you are given this is an
  indirect diagnostic. This is your own independent assessment, not a comparison against the
  HGPS catalog or paper, that comparison happens separately, outside this run.
