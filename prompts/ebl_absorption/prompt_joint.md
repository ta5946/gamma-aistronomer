# CTA analysis: extragalactic background light (EBL) absorption

## Context

Gamma rays from extragalactic sources pair-produce with photons of the Extragalactic
Background Light (starlight and dust emission accumulated over cosmic history) as they
travel to us, attenuating the observed spectrum increasingly at higher energy and higher
redshift. Measuring that attenuation is itself a measurement of the EBL's photon density —
not just a correction to apply before doing the "real" science. Ground your account of what
a measured (or absent) attenuation implies in `cognee_recall` and the literature rather than
asserting it.

A single blazar barely constrains this: its intrinsic spectral shape and the strength of EBL
absorption are largely degenerate for one source alone, since a softer intrinsic spectrum and
stronger absorption can mimic each other. This task is a **joint fit across several blazars
at different redshifts** instead of separate single-source fits — combining sources spread
across redshift breaks that degeneracy, because the same absorption strength has to explain
attenuation at multiple different distances at once. That's what "constrain the EBL scaling"
means below, and it's the actual point of this task, not an optional extra.

None of these are HGPS sources — HGPS surveys the Galactic plane, and these are extragalactic
objects, so there's no HGPS fit to build on or guard against here. CTAO's own internal,
simulated data includes its own archival pointings toward known extragalactic blazars; find
the observations toward each given source yourself (match on the `OBJECT` column in
`obs-index.fits.gz`) and reduce each one to a spectrum the same way you would for any 1D
spectral analysis.

## Environment

- Built-in EBL absorption model tables (Domínguez 2011, Franceschini, Franceschini 2017,
  Saldaña-López 2021) are at `/workspace/data/ebl/`. `EBLAbsorptionNormSpectralModel`'s own
  `read_builtin()` expects `$GAMMAPY_DATA`, which isn't set to this path — use
  `EBLAbsorptionNormSpectralModel.read(<path>, redshift=...)` with an explicit path into
  `/workspace/data/ebl/` instead.
- `EBLAbsorptionNormSpectralModel` has two parameters: `redshift` (fixed, different per
  source — freeze it at each source's given value) and `alpha_norm` (the EBL scaling this
  task is actually constraining, 1.0 by default). Create one absorption model instance per
  source (each with its own fixed redshift), then link their `alpha_norm` parameters to the
  same shared `Parameter` object so a joint `Fit()` across all datasets fits one shared
  value, not one independent value per source.
- Prefer `SpectrumDatasetOnOff` (or `SpectrumDataset`), `EBLAbsorptionNormSpectralModel`,
  `Datasets`, `FluxPointsEstimator`, and `Fit` over hand-written equivalents.

## Given

Target blazars and their redshifts (fixed inputs to the absorption model, not something to
refit here) — every known extragalactic blazar pointing in the CTAO dataset:

| Source name  | Redshift |
|--------------|----------|
| BLLac        | 0.069    |
| 1ES1011+496  | 0.212    |
| 3C66A        | 0.34     |
| IC310        | 0.019    |

## Critical constraint

Fitting each source independently and eyeballing whether each one individually "needed"
absorption defeats the point of this task — the shared `alpha_norm` has to come from one
joint fit across all sources' datasets at once, using Gammapy's own parameter-linking
mechanism, not from averaging or comparing separate per-source fits after the fact.

Applying an EBL model and reporting whatever comes out isn't the point either — whether
attenuation is actually statistically required by the joint data is itself part of the
result. Fit the joint dataset both with `alpha_norm` free and with it fixed at 1.0 (or with
absorption omitted entirely) and compare the two by fit statistic, not by which curves look
better by eye. If you compare more than one built-in EBL model, the same rule applies: let
the fit statistic pick between them, and say so.

The given redshifts are fixed inputs, not results to re-derive; this task fits each source's
intrinsic spectral shape plus the one shared `alpha_norm`, not the redshifts themselves.

## Deliverables

In `out/`:
- `sed_comparison.png` — one spectral energy distribution plot per source (a small
  multi-panel figure, one panel per blazar) of your extracted CTAO flux points (with error
  bars, and upper limits where a bin isn't significant), overlaid with that source's best-fit
  absorbed (observed) model and deabsorbed (intrinsic) model, a legend naming each, log-log
  axes, and each panel titled with its source name.
- `results.json` — your fitted values, structured like this:
  ```json
  {
    "ebl_model": "dominguez",
    "alpha_norm": 0.0,
    "alpha_norm_err": 0.0,
    "delta_ts_absorption_over_unabsorbed": 0.0,
    "absorption_interpretation": "detected",
    "interpretation_confidence": "low",
    "sources": [
      {
        "source_name": "...",
        "redshift": 0.0,
        "intrinsic_index": 0.0,
        "intrinsic_index_err": 0.0
      }
    ]
  }
  ```
  `ebl_model` is whichever built-in table you used (report on more than one if you compared
  them, and say which one you picked and why). `alpha_norm`/`alpha_norm_err` are the one
  shared, jointly-fitted EBL scaling value and its uncertainty — the actual point of this
  task. `delta_ts_absorption_over_unabsorbed` is the joint fit-statistic improvement from
  including EBL absorption over the unabsorbed joint fit — report how you computed it; leave
  it out rather than reporting a meaningless `0.0` if the fit didn't converge.
  `absorption_interpretation` is one of `"detected"`, `"not_detected"`, or `"inconclusive"` —
  your own statistically-grounded call, not just whether you included the model in the fit; a
  non-detection is a legitimate, expected outcome given limited statistics, not a failure;
  inconclusive is the honest answer when the joint fit doesn't clearly resolve either way.
  Don't force a detected/not-detected call the data doesn't support.
  `interpretation_confidence` reflects how strongly the statistics support that call, not how
  interesting the result is. `sources` has one entry per blazar you actually fit, in any
  order, with each source's given redshift echoed back alongside its own fitted intrinsic
  spectral index — leave `intrinsic_index`/`intrinsic_index_err` out for a source whose fit
  didn't converge rather than reporting `0.0`, but keep the entry (with `source_name` and
  `redshift`) so it's clear that source was attempted.
- `report.md` — your write-up: what you did, what you found, and your interpretation of the
  result, including which observations you used per source, why you picked the EBL model(s)
  you did, how the joint fit actually improved on treating sources independently, and how
  confident you are given the statistics available. This is your own independent
  assessment — there's no HGPS catalog or paper to compare against here, that comparison
  happens separately, outside this run, against external redshift/EBL literature where
  relevant.
