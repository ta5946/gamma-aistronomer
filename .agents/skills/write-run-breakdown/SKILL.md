---
name: write-run-breakdown
description: Turn an archived agent run (OpenCode, Pi, or another harness) for any science task into a structured `## Run N<n>` entry in docs/run_breakdown.md, comparing its fitted values against the HGPS catalog where one applies.
---

# Write a run breakdown

## Why

An archived run (see the `archive-agent-workspace` skill) is just raw files: a script, a plot, a
results file, and the harness's own session stats. This skill turns one archive into one dated
entry in `docs/run_breakdown.md`, reporting what the agent fit and comparing it against the HGPS
catalog where the catalog has a matching value, so a reader can judge the run without digging
through the archive themselves.

## Steps

Check which harness produced the archive — each harness writes its own `<harness>_stats/`
subdirectory (`opencode_stats/` or `pi_stats/`), never more than one:

```bash
find run_archive/<timestamp> -maxdepth 1 -name '*_stats'
```

Identify the task from which key `out/results.json` has: `ra_deg` for `source_characterization`,
`energy_bands_tev` for `cosmic_ray_propagation`, `preferred_model` for `acceleration_mechanism`,
`max_constrained_energy_tev` for `pevatron_search`, `alpha_norm` for `ebl_absorption`.

Identify which source this archive is for from `out/report.md`'s own title or opening line (it
always names the source, e.g. "HESS J1825-137"), then look that name up in
`data/cache/hgps/sources.csv` to get its `id` and every catalog value used below.
`ebl_absorption` has no single source.

Pull the session's model, token usage, and runtime straight from the archive's own session stats.

### OpenCode

From `opencode.db`:

```bash
sqlite3 run_archive/<timestamp>/opencode_stats/opencode.db \
  "SELECT model, tokens_input, tokens_output, time_created, time_updated FROM session;"
```

`model` comes back as JSON, e.g. `{"id":"alias-fast","providerID":"blablador"}` — write it
as `<providerID>/<id>` (`blablador/alias-fast`), not pasted as-is. Runtime is
`time_updated - time_created` in milliseconds. Count cognee calls with:

```bash
grep -c cognee_recall run_archive/<timestamp>/opencode_stats/log/opencode.log
```

### Pi

From the run's own JSONL session log (`pi_stats/--workspace--/*.jsonl`, one file per run — each
line is one event):

```python
import json

jsonl_path = "run_archive/<timestamp>/pi_stats/--workspace--/<file>.jsonl"
model = None
first_ts = last_ts = None
input_tot = output_tot = 0

with open(jsonl_path) as f:
    for line in f:
        d = json.loads(line)
        ts = d.get("timestamp")
        if ts:
            first_ts = first_ts or ts
            last_ts = ts
        if model is None and d.get("type") == "model_change":
            model = f"{d['provider']}/{d['modelId']}"
        usage = (d.get("message") or {}).get("usage")
        if usage:
            input_tot += usage.get("input", 0) or 0
            output_tot += usage.get("output", 0) or 0

print(model, input_tot, output_tot, first_ts, last_ts)
```

`first_ts`/`last_ts` are ISO 8601 UTC timestamps (e.g. `2026-08-21T20:31:21.237Z`); their
difference is the runtime. Count cognee calls with:

```bash
grep -c '"toolName":"cognee_recall"' run_archive/<timestamp>/pi_stats/--workspace--/*.jsonl
```

### Another harness

Find the same four things in its own session stats: model, input and output tokens, start and end
time, and the number of cognee calls. Add a section here for it once it works.

### Every task

The fitted values are whatever `run_archive/<timestamp>/out/results.json` says, with the keys the
task's own `prompt_template.md` (or `prompt_joint.md`) lists under Deliverables. Use these numbers
exactly as written, even if one looks wrong; a suspicious value goes in the "Wrong" bullets below,
not silently corrected. A key the agent left out stays out of the table. `report.md` and the plot
are for the "What happened" paragraph, not for pulling numbers.

The catalog values come from `data/cache/hgps/sources.csv`, matched to the source by name. Its
only values that compare against a fit are `ra_j2000`, `dec_j2000`, `size_deg`,
`flux_1tev_diff` (already the differential flux for whichever spectral model that source uses),
and `spectral_model` (PL or ECPL), so only some tasks have something to compare:

- `source_characterization` — RA, Dec, position offset, size, and flux at 1 TeV all compare.
  Compute the position offset with astropy instead of comparing RA and Dec on their own:

  ```python
  from astropy.coordinates import angular_separation
  import astropy.units as u

  angular_separation(ra_fit * u.deg, dec_fit * u.deg, ra_cat * u.deg, dec_cat * u.deg).to(u.deg)
  ```

- `cosmic_ray_propagation` — each band's size compares against the catalog's single
  `size_deg`.
- `acceleration_mechanism` — `preferred_model` compares against the catalog's `spectral_model`.
- `pevatron_search` — `cutoff_detected` compares against whether the catalog's `spectral_model`
  is ECPL.
- `ebl_absorption` — nothing in the catalog compares.

Leave the Catalog and Difference / Ratio cells as "—" for any value without a catalog match.

Check `docs/run_breakdown.md` for the highest existing run number and use the next one. If the
file doesn't exist yet, create it and start at Run N1.
Link "Prompt version" to whichever task's `prompt_template.md` was actually used for this run
(e.g. `prompts/acceleration_mechanism/prompt_template.md`, or
`prompts/ebl_absorption/prompt_joint.md`), not a source-specific filled copy.
If the run used a different prompt file, link that one as-is. Append:

```markdown
## Run N<n>

- **Task:** <task folder name>
- **Source object:** <name> (id=<id>)
- **Prompt version:** [<prompt file name>](<relative link>)
- **Harness:** <opencode, pi, or other>
- **Model:** `<provider>/<model>`
- **Agent runtime (session):** ~<duration>
- **Agent token usage:** <input> input / <output> output
- **Cognee calls:** <count>
- **Workspace archive:** [run_archive/<timestamp>](../run_archive/<timestamp>)

### CTAO fitted vs HGPS catalog values

| Quantity | Fitted | Catalog | Difference / Ratio |
|---|---|---|---|
| RA | ...° | ...° | ...° |
| Dec | ...° | ...° | ...° |
| [Position offset](https://docs.astropy.org/en/latest/api/astropy.coordinates.angular_separation.html) | — | — | ...° |
| Size | ...° | ...° | ...° |
| Flux at 1 TeV (differential) | ... | ... | ratio ... |

### Generated plot

<div align="center">

<img src="../run_archive/<timestamp>/out/<plot>.png" width="60%">

</div>

### What happened

One paragraph of 60 to 80 words: what the agent actually did (observation selection, model, fit
stages, whether it converged), grounded in the script and report, not speculation. Check whether
the fitted values actually moved away from whatever they were seeded with, rather than being
copied through unchanged. Setup detail stays in the archived `report.md`.

**Correct:**
- 2-4 bullets, concrete and specific, citing the actual number.

**Wrong:**
- 2-4 bullets, same standard.
```

The table rows above are for `source_characterization`. Other tasks swap them for their own.
For `ebl_absorption`, write the Source object line as the blazars that were fit, without an id.
Its table gets one row per shared value (`alpha_norm`, `delta_ts_absorption_over_unabsorbed`),
then one row per source for its intrinsic index. For `cosmic_ray_propagation`, one size row per
energy band. Interpretation fields (`preferred_model`, `size_trend`,
`acceleration_mechanism_interpretation`, `interpretation_confidence`, and so on) get a row each,
written as the agent's own word. `<plot>` is the task's own plot from Deliverables, e.g.
`significance_map.png` or `sed_comparison.png`.

Do not make the same point twice, once in the paragraph and again as a bullet. Differences that
follow from the data rather than the agent's own choices belong in the table, not the bullets.

Angles (RA, Dec, Position offset, Size) are in degrees, to 5 decimal places, never arcseconds.
Every other number uses 3 significant figures. RA, Dec, and Size report fitted minus catalog; Flux
reports fitted divided by catalog, labeled "ratio". No em dashes anywhere in this document, and
table labels stay plain language ("Size," "Flux at 1 TeV," "Cutoff energy"), not raw field names.
