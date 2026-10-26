# CTA analysis task

## Context

The H.E.S.S. Galactic Plane Survey (HGPS, paper arXiv:1804.02432,
https://arxiv.org/abs/1804.02432, catalog https://www.mpi-hd.mpg.de/HESS/hgps) is
a real, published survey of gamma-ray sources along the Milky Way, observed by the H.E.S.S.
Cherenkov telescope array. CTAO (Cherenkov Telescope Array Observatory) is a newer, more
sensitive Cherenkov array; the data in this workspace is CTAO's own internal, simulated
data covering the same sky, not real HESS data.

## Environment

- Gammapy 2.1 is installed for Python 3, along with astropy, regions and iminuit.
- The shell is `sh` (no bash, no curl) — Python's own HTTP libraries and your built-in
  internet access both work.
- CTA DL3 data is under `/workspace/data/ctao-data`, in a standard Gammapy DataStore
  layout (hdu-index.fits.gz, obs-index.fits.gz, CALDB, event lists).
- `cognee_recall` is available as a tool: call it with a short natural-language query to
  search a knowledge base containing Gammapy's complete official documentation, its
  tutorial notebooks, and papers on gamma-ray and IACT analysis methods, scoped to the
  `gammapy-cta-hgps` dataset (an optional `hess-papers` dataset covers related HESS
  publications). Use it as your first stop whenever you're unsure how something works or
  which Gammapy component to reach for. On consecutive errors or bugs, query cognee before
  trying another guess.
- If your task concerns an HGPS source, the paper (arXiv:1804.02432) is already in
  `/workspace/paper`, read it from there instead of downloading it again.
- The HGPS catalog, with the full source table, is at https://www.mpi-hd.mpg.de/HESS/hgps.

## Critical constraint

Every value you report must come from your own analysis of the CTAO data in this
workspace. The paper and catalog are given to you for scientific and methodological
context — how HGPS frames and presents this kind of analysis — not as a source of
answers. Reading a source's own published values from that paper or catalog and reporting
them, instead of your own fit, is not acceptable, even as a cross-check disguised as a
result. Treat this the same as any other unsubstantiated claim: derive it, don't quote it.

Your code in `src/` will be reviewed alongside `results.json`, so the reported values need
to genuinely trace back to what your code computes, not just look plausible on their own.

## Deliverables

Organize `/workspace` into:
- `src/` — your analysis code.
- `paper/` — reference material relevant to your task (e.g. the HGPS paper), plus anything
  you download.
- `out/` — everything the task below asks for.

## Process

1. Analyze the problem and the available data.
2. Write down a plan for your implementation.
3. Implement and test it. Try it on a small subset of data first, so a bug shows up in
   seconds, not after a full run — then switch to the full dataset for your actual result.
4. Interpret and verify the result — judging whether the numbers you got actually make
   physical sense, and confirming the fit actually converged, not just whether the code
   ran without errors.

Cross-reference your plan and choices against `cognee_recall` throughout, especially in the
earlier stages — prefer grounding decisions in what Gammapy's own documentation and
tutorials say over guessing. Prefer Gammapy's built-in components over hand-written
statistics or analysis code wherever one applies.

Keep the analysis script's runtime between 5 and 10 minutes — measure it, don't guess.

Work autonomously through to completion; no human is available to answer questions. Where
something is ambiguous, make the most well-grounded assumption you can, state it, and
proceed.
