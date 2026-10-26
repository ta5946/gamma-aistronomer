# CTA analysis: PeVatron search for {{SOURCE_NAME}}

## Context

A source accelerating protons or nuclei to PeV energies (a "PeVatron") would show gamma-ray
emission extending to, or beyond, 100 TeV without the exponential cutoff a leptonic
inverse-Compton spectrum would show at those energies from radiative cooling — the harder
and higher-energy the spectrum persists, the stronger the case. Extend {{SOURCE_NAME}}'s own
spectral fit as far into the highest-energy bins as the data lets you, and test whether it
stays hard and uncut, rather than fitting a fixed, conventional energy range and stopping
there. Ground your account of what a hard, uncut high-energy spectrum does and doesn't imply
in `cognee_recall` and the literature rather than asserting it — an uncut power law to the
edge of your data is evidence toward a PeVatron, not proof one is confirmed, since a cutoff
(if any) may simply sit above what this exposure can reach.

HGPS fit a single spectral shape (power law or exponential cutoff power law) to
{{SOURCE_NAME}} over its own standard energy range, with no dedicated cutoff search at these
energies. This task genuinely goes further than HGPS did for this source, the same situation
`acceleration_mechanism` is in.

## Given

- Source name: {{SOURCE_NAME}} ({{SOURCE_CLASS}})
- Position (ICRS): RA = {{RA_DEG}} deg, Dec = {{DEC_DEG}} deg
- Analysis region radius: {{RSPEC_DEG}} deg

The given position and region radius are HGPS's own, used the same way
`acceleration_mechanism` and `cosmic_ray_propagation` use them: to define the same
extraction region HGPS used, not as anything to refit here.

## Critical constraint

Report the actual maximum energy your own fit could meaningfully constrain for this
source, not just the nominal upper edge of the dataset — one source's usable statistics
may run out well before 100 TeV, and that limit is itself part of the result, not a detail
to omit.

Not showing PeVatron-candidate behavior is a legitimate, expected outcome — don't force a
candidate call the fit doesn't support. A non-detection of a cutoff-free high-energy
spectrum is exactly as reportable a result as detecting one.

## Deliverables

In `out/`:
- `pevatron_spectrum.png` — the extracted CTAO flux points (with error bars, and upper
  limits where a bin isn't significant) on log-log axes, overlaid with the best-fit power
  law extended out to the highest energy your fit could reach, a legend, and a title
  naming the source.
- `results.json` — your fitted values, structured like this:
  ```json
  {
    "max_constrained_energy_tev": 0.0,
    "power_law_index": 0.0,
    "power_law_index_err": 0.0,
    "cutoff_detected": false,
    "delta_ts_ecpl_over_pl": 0.0,
    "pevatron_candidate": false,
    "interpretation_confidence": "low"
  }
  ```
  `max_constrained_energy_tev` is the highest energy your own fit could actually constrain,
  not just the nominal upper edge of the dataset. `cutoff_detected` is your own
  statistically-grounded call (report the delta-TS or delta-Cash-statistic you used, the
  way `acceleration_mechanism` does) on whether a cutoff is preferred over a plain power
  law within the energy range you could reach; leave `delta_ts_ecpl_over_pl` out rather
  than reporting a meaningless `0.0` if the comparison fit didn't converge.
  `pevatron_candidate` is `true` only for a source with no statistically preferred cutoff
  and a spectrum extending to within a factor of a few of 100 TeV; state your own
  threshold and reasoning for this call. `interpretation_confidence` reflects how strongly
  the statistics support that call, not how interesting the result is.
- `report.md` — your write-up: what you did, how far into the spectrum your own statistics
  actually let you go, whether you'd flag this source as a PeVatron candidate and why, and
  how confident you are given that a missing cutoff is an absence of evidence, not evidence
  of absence, at the energy and exposure available here. This is your own independent
  assessment, not a comparison against the HGPS catalog or paper, that comparison happens
  separately, outside this run.
