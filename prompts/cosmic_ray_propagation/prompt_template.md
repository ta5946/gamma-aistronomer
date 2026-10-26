# CTA analysis: cosmic-ray propagation for {{SOURCE_NAME}}

## Context

Relativistic particles (electrons or protons) don't stay put once accelerated: they diffuse
away from their source, radiating as they go. A source's angular size as a function of
energy is a direct, observable trace of that transport, not just a morphological curiosity,
though what a given trend (or the absence of one) actually implies about the underlying
transport is for you to reason through and ground in `cognee_recall` and the literature, not
something to take as given here. A flat size across energy is just as real and reportable a
result as a shrinking or growing one — most sources, especially at CTAO's achievable
per-band statistics, will show no significant trend, and that's expected, not a failure.

HGPS fit a single, energy-integrated size to {{SOURCE_NAME}} from real HESS data. This task
goes further: using CTAO's own internal, simulated data for the same source, split the data
into a small number of energy bands and independently fit the source's angular size in each
one, to test whether its extent actually changes with energy. A symmetric width is the
required summary quantity below, but not every source's morphology is actually symmetric:
if the per-band maps show a clearly asymmetric or offset excess, note that in `report.md`
alongside the symmetric measurement rather than letting a single width silently average it
away.

## Environment

- Splitting the data by energy divides up an already-limited photon count. Keep the number
  of energy bands small (2 to 3 is often enough) rather than defaulting to the fine binning
  you'd use for a spectral fit; a band with too few excess counts to constrain a size fit is
  a real, expected outcome, not a bug to work around.
- Prefer `ExcessMapEstimator`, `Fit`, and Gammapy's spatial model classes over hand-written
  equivalents.

## Given

- Source name: {{SOURCE_NAME}} ({{SOURCE_CLASS}})
- Position (ICRS): RA = {{RA_DEG}} deg, Dec = {{DEC_DEG}} deg — a fixed input for centering
  the analysis region, not something to refit here
- Analysis region radius: {{RSPEC_DEG}} deg
- Energy-integrated size HGPS fit: {{SIZE_DEG}} deg ({{SPATIAL_MODEL}}) — given for context
  on what HGPS found when averaging over all energies, not a value that should hold in every
  band; testing whether it actually does is the point of this task

## Critical constraint

Size is exactly what you're independently deriving here, band by band, unlike a task that
treats geometry as a fixed input to build on. {{SOURCE_NAME}}'s own published size, or any
energy-dependence claimed for it in the literature, is not something to read off and
report as if it were your own result, even reframed or rounded. The given energy-integrated
size exists only to help you scale the analysis region, not to anchor your per-band fits.

The given position is a fixed input for this task; only size is being re-derived here, per
band. {{SPATIAL_MODEL}} is HGPS's own, full-statistics model; matching that same complexity
in each band, on a fraction of the counts, usually isn't realistic — a single Gaussian per
band, reporting its width as size, is a reasonable simplification, as long as you say
that's what you did.

## Deliverables

In `out/`:
- `morphology_vs_energy.png` — a plot of fitted angular size against energy band, with error
  bars, unconstrained bands marked separately rather than omitted silently, a log energy
  axis, and a title naming the source. A small multi-panel figure of the per-band
  significance maps alongside it is a welcome addition, not a substitute for this plot.
- `results.json` — your fitted values, structured like this:
  ```json
  {
    "energy_bands_tev": [[0.3, 1.0], [1.0, 3.0], [3.0, 10.0]],
    "size_deg": [0.0, 0.0, 0.0],
    "size_err_deg": [0.0, 0.0, 0.0],
    "size_trend": "shrinking",
    "trend_significance_sigma": 0.0,
    "morphology_interpretation": "energy_dependent",
    "interpretation_confidence": "low"
  }
  ```
  `energy_bands_tev` are the band edges you actually used, in TeV; `size_deg`/`size_err_deg`
  are per-band, same order and length as `energy_bands_tev`. Use `null` in place of a band's
  size if that band's excess wasn't significant enough to constrain a fit, rather than
  reporting a number you don't trust. `size_trend` is one of `"shrinking"`, `"growing"`, or
  `"flat"` — your own read of the pattern across bands, only meaningful together with
  `trend_significance_sigma`, the significance of that trend against a constant-size
  hypothesis (report how you computed it). If fewer than two bands produced a constrained
  fit, there's no trend to characterize; leave `size_trend` and `trend_significance_sigma`
  out entirely rather than guessing, and let `morphology_interpretation` carry that instead.
  `morphology_interpretation` is one of `"energy_dependent"`, `"no_significant_trend"`, or
  `"inconclusive"` — inconclusive is a legitimate, expected answer when too few bands were
  usable to say anything; don't force a trend the data doesn't support.
  `interpretation_confidence` reflects how strongly the statistics support that call, not how
  interesting the result is.
- `report.md` — your write-up: what you did, what you found, and your interpretation of the
  result, including how you chose the energy bands and why, and how confident you are given
  the statistics available in each one. This is your own independent assessment, not a
  comparison against the HGPS catalog or paper — that comparison happens separately, outside
  this run.
