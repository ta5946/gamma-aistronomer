# data/

Only small, hand-maintained inputs are tracked here. Everything large or downloaded lives
under `cache/`, which is gitignored.

## Tracked

- `resources.json` — the ingestion manifest, see below.

## resources.json

The list of documents ingested into the Cognee knowledge graph. `src/cognee_ingestion.ipynb`
downloads each entry into `cache/ingestion/`. `src/cognee_cloud_ingestion.py` reuses those
same files against the hosted tenant.

- `last_updated` — date the list was last changed.
- `whitepaper` — the CTA science whitepaper, a single entry.
- `related_papers` — H.E.S.S. papers (a few joint with MAGIC and VERITAS), roughly ordered
  by date, newest first, ingested in `n_citations` order.
- `documentation`, `examples` — Gammapy documentation and tutorial folders.

Every entry has `title`, `url`, `type` (`pdf` or `folder`), `sets` (the Cognee `node_set`
tags applied on ingestion) and `n_pages`. Papers and the whitepaper also carry `n_citations`.

### Maintenance

- New paper: append to `related_papers` with a direct `arxiv.org/pdf/<id>` url.
- Different Gammapy version: change the `v2.1` ref in the `documentation` and `examples`
  urls. The notebook sparse-clones `gammapy/gammapy` at whatever ref the url names.
- Bump `last_updated` on any change.
- Kept as JSON because the pipeline reads it with the standard library. YAML would be
  easier to hand-edit but adds a `pyyaml` dependency.

## cache/

Not tracked. A fresh clone starts with an empty `cache/`. It fills from:

- `ingestion/` — the download step in `src/cognee_ingestion.ipynb`, driven by `resources.json`.
- `gammapy/` — `gammapy download datasets`, plus the internal CTAO dataset (supplied
  separately).
- `hgps/` — filled by `src/match_ctao_sources.py` on first run: the HGPS catalogue FITS and
  paper, and `sources.csv` built from the catalogue.
- `exported/` — provisioned by the deployment, not a clone (see "Knowledge sources: caching
  and ingestion" in the top-level README).
