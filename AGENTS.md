# AGENTS.md

Guidance for coding agents (Claude Code, Codex, and others) working in this repository.

## What this is

A research prototype for an autonomous gamma-ray astronomy agent. Three pieces fit together:

1. **Cognee knowledge graph** — long-term memory built from Gammapy docs, Gammapy example notebooks, the HGPS paper, the CTA whitepaper, and a growing set of related H.E.S.S. papers (a few joint with MAGIC and VERITAS; see "Layout" below for ingestion progress). Served over HTTP and MCP.
2. **Agent harnesses** — OpenCode and pi, two LLM coding agents in containers with Gammapy installed. Both query the same knowledge graph through MCP and run the same analysis task on CTAO data, kept as separate harnesses to compare against each other.
3. **Gammapy analysis** — notebooks and scripts that define the target task, reproducing HESS Galactic Plane Survey (HGPS) source analyses on internal simulated CTAO data.

Our setup sends all LLM inference to Blablador (FZ Jülich), the DESY assistant, or GMI Cloud — none of these are an OpenAI endpoint. Blablador enforces 10 requests per minute. Cognee's own ingestion/recall pipeline only ever uses Blablador (`.env`'s `LLM_PROVIDER`); the OpenCode and pi agents share one provider from `.agents.env` (`AGENT_LLM_ENDPOINT`, `AGENT_LLM_API_KEY`, `AGENT_LLM_MODEL_ID`, `AGENT_LLM_MODEL_NAME`), filled into their config templates when the container starts; the archived runs used the DESY assistant's `reasoning` model (see "Things that bite" for the DESY proxy setup, and for why not every Blablador model works here as a fallback).

The target: given a source's catalog position, analysis region radius, spectral model, and spatial model, independently fit that source's own ra, dec, size, and differential flux at 1 TeV from the CTAO data, plus a significance map, following the rules in `prompts/system_prompt.md` (derive it, don't quote it; comparing the fit against the HGPS catalog happens afterward, outside the agent's own run, see "Evaluating agent runs" below). `env_and_dataset_check.ipynb` (the Gammapy ring background tutorial on public HESS data) shows the kind of output expected for the first of five science tasks, `prompts/source_characterization/` (see "Layout" below for the other four, and for how a task's template actually becomes the message pasted to the agent).

## Environment

```bash
# setup
python3.13 -m venv .venv && source .venv/bin/activate
pip install -e .
python -m ipykernel install --user --name gammai   # registers the venv as a Jupyter kernel
```

Python 3.13, gammapy 2.1, astropy 7.2, cognee 1.4.0. There is no test suite, linter, or build step. Scripts run directly, notebooks run in Jupyter. `pip install -e .` also installs the `gammai` CLI, which covers the analysis side only: `gammai check` tests the Python environment, `.agents.env`, the data, Docker, the LLM and Cognee MCP, `gammai derive` asks Cognee MCP for the dataset's use cases and their Gammapy breakdown, and `gammai run pi|opencode` starts a harness (see "Running things").

Copy `.env.example` to `.env` and fill in keys before anything else. Every Cognee container reads `.env` via `env_file`, except `cognee-frontend`, which only needs `NEXT_PUBLIC_LOCAL_API_URL` (hardcoded in `deploy/cognee/docker-compose.yml`). The agent harnesses read `.agents.env` instead (from `.agents.env.example`): the client-side `COGNEE_MCP_URL` plus the `AGENT_LLM_*` provider their config templates are filled with. `.env` covers ingestion, deployment and the host scripts, `.agents.env` the analysis runs, so a run against a deployed Cognee needs `.agents.env` plus `.env`'s `CTAO_DATA_PATH` for `match_ctao_sources.py`.

## Running things

Scripts in `src/` use paths relative to their own directory, so run them from `src/`:

```bash
cd src && python match_ctao_sources.py
```

Cognee stack (backend, MCP, frontend):

```bash
cd deploy/cognee && docker compose --env-file ../../.env up --build
```

`gammai run <pi|opencode> [-i | "<prompt>" | -f <file>]` wraps the compose commands below (interactive without a prompt, one-shot with one) and refuses a non-empty workspace unless `--force` is given.

OpenCode agent, which reaches Cognee MCP at `.agents.env`'s `COGNEE_MCP_URL`, a deployed instance or `http://host.docker.internal:8001/mcp` for the local stack:

```bash
cd opencode
docker compose -f opencode-compose.yml run --rm --build -it opencode
docker compose -f opencode-compose.yml run --rm --build opencode run "<prompt>"
```

`opencode.json` sets `"permission": "allow"`, so the agent runs fully autonomously with no permission prompts — this is what makes "no human is available to answer questions" in the analysis prompts actually true in practice.

pi agent, same MCP, same task:

```bash
cd pi
docker compose -f pi-compose.yml run --rm --build -it pi
docker compose -f pi-compose.yml run --rm --build pi -p "<prompt>"
```

pi has no permission-prompt setting to flip; it runs all tools by default. `pi/settings.json` sets `defaultProjectTrust: "always"` instead, since the default (`"ask"`) silently ignores project config in non-interactive `-p` mode.

See README.md for service URLs, login, volume backup and restore, and the JWT command that fills `COGNEE_JWT`.

## Layout

- `src/cognee_ingestion.ipynb` — the main ingestion pipeline. Downloads resources listed in `data/resources.json`, calls `cognee.remember()` per item into two datasets, `gammapy-cta-hgps` (Gammapy docs and examples, the Gammapy and HGPS papers, the CTA whitepaper) and `hess-papers` (related HESS papers, sorted by citation count, excluding the Gammapy and HGPS papers themselves), visualizes each dataset's graph to `plot/<dataset>_knowledge_graph.html`, exports to `data/cache/exported/` in cogx format. Host-side rebuild — the live Docker volume's datasets only reflect whatever was exported at deploy time, until this is re-exported and re-imported. Full ingestion is resumable within a kernel session; a restart loses tracking and starts over. `hess-papers` is partial as of this writing (70/239 papers).
- `src/gammai/` — the `gammai` CLI package (`cli.py`, `checks.py`, `derive.py`, `run.py`), the only installed code. Checks read `.agents.env` and the default `data/cache/` paths the compose files mount.
- `src/cognee_cloud_ingestion.py` — a reduced version of the same flow (see the corpus note below) against the hosted Cognee tenant via `cognee.serve()`. Also grants dataset permissions to the dashboard user, which the API does not do automatically.
- `src/env_and_dataset_check.ipynb` — the Gammapy ring background tutorial, run on public HESS DL3 DR1 data (`$GAMMAPY_DATA/hess-dl3-dr1/`, MSH 15-52), not the internal CTAO set. Kept as the reference for what the agent should be able to produce, and as a library / environment sanity check.
- `src/match_ctao_sources.py` — builds `data/cache/hgps/sources.csv` from the HGPS catalogue FITS (downloaded from the HESS data release on first run): trims each source to the columns the analysis code needs (`id` is ours, a 1-based index in catalogue order), then joins against CTAO pointings in the dataset's `obs-index.fits.gz` (found through `CTAO_DATA_PATH` in `.env`, via `load_dotenv()`) to add `in_ctao` and `min_offset_deg`. Thresholds come from Prod5 IRF offset validity.
- `src/plot_ctao_plane.py` — Galactic-plane strip skymap of the internal CTAO data (read through `CTAO_DATA_PATH`) in the HGPS-figure style, writes `plot/ctao_plane.png`.
- `src/plot_ctao_allsky.py` — all-sky Aitoff significance map of the internal CTAO data (read through `CTAO_DATA_PATH`), writes `plot/ctao_allsky.png`. `plot/` is created on first run and not tracked.
- `pi/` — a second agent harness running the same task as `opencode/`, for comparing implementations. `Dockerfile.gammapy` mirrors OpenCode's (same gammapy/regions pins). `settings.json`/`models.json`/`mcp.json` are pi's split equivalent of `opencode.json`, templates filled into `~/.pi/agent` when the container starts, the same way `opencode.json` is filled into OpenCode's global config, so neither lands in `/workspace`. `pi/workspace/` mirrors `opencode/workspace/` (gitignored, holds a run's output and `pi_stats/` logs) and is covered by the same skills as OpenCode, see "Evaluating agent runs".
- `prompts/derive_use_cases/` — the two prompts behind `docs/gammapy_use_cases.md` (science use cases, then their Gammapy breakdown, Prompt 2 taking Prompt 1's answer at `{{LIST_OR_TABLE_OF_USE_CASES}}`). `gammai derive` sends both to Cognee MCP, auto-routed recall on `gammapy-cta-hgps` unless `--search-type` picks one (e.g. `GRAPH_COMPLETION_COT`).
- `prompts/system_prompt.md` — the one shared, task-agnostic contract (environment, "derive it, don't quote it", the `src/`/`paper/`/`out/` layout, the generic process), mounted read-only at `/workspace/AGENTS.md` so the agent auto-loads it for every task.
- `prompts/source_characterization/` — first science task (match and characterize a source), template at `prompt_template.md`.
- `prompts/acceleration_mechanism/` — second science task (leptonic vs. hadronic emission), template at `prompt_template.md`.
- `prompts/cosmic_ray_propagation/` — third science task (energy-dependent morphology), template at `prompt_template.md`.
- `prompts/ebl_absorption/` — fourth science task (extragalactic background light absorption), `prompt_joint.md` instead of `prompt_template.md` — a joint fit across every extragalactic blazar pointing in the CTAO dataset (matched by `OBJECT` in `obs-index.fits.gz`: `BLLac`, `3C66A`, `1ES1011+496`, `IC310`) with one EBL scaling parameter (`alpha_norm`) linked across all of them, redshifts baked into the file since no local catalog has them. Needs the EBL absorption model tables mounted at `/workspace/data/ebl/`. The one task that isn't per-HGPS-source.
- `prompts/pevatron_search/` — fifth science task (emission beyond ~100 TeV, proton PeVatron evidence), template at `prompt_template.md`.
- `data/cache/hgps/` — gitignored, untracked, provisioned rather than cloned. `src/match_ctao_sources.py` fills it on first run: downloads `hgps_catalog_v1.fits.gz` (full HESS catalogue) and `1804.02432.pdf` (the HGPS paper, reference material for agent runs), and generates `sources.csv` (the trimmed 78-source table the analysis code and `write-run-breakdown` read) from the catalogue.
- `data/resources.json` — the ingestion download manifest (documented in `data/README.md`). Everything else lands in `data/cache/`, gitignored.
- `data/cache/ingestion/` — the corpus, gitignored (241 arXiv PDFs — 239 ingested, the Gammapy and HGPS papers are downloaded but excluded — plus Gammapy docs and examples). The download cell in `cognee_ingestion.ipynb` skips anything already present.
- `data/cache/exported/` — gitignored cogx exports, provisioned via the deployment side rather than a fresh clone. `cognee-import` reads this directory through `COGNEE_EXPORT_PATH` (`.env`, default `../../data/cache/exported` relative to `deploy/cognee/`). `gammapy-cta-hgps/` (271 documents, 3936 nodes, 21044 edges) and `hess-papers/` (342 documents so far, 6391 nodes, 32990 edges — split-part counts, not paper counts, see above) are both loaded into the live Docker volume — a genuinely fresh clone has nothing here until this is supplied some other way.
- `data/cache/gammapy/` — gitignored, large: the internal CTAO data plus Gammapy sample datasets. The CTAO DL3 DataStore sits at `ctao-data/data-transfer/` (hdu-index, obs-index, CALDB) and `CTAO_DATA_PATH` points straight at it; `gammapy download datasets` fills `gammapy-datasets/2.1/`.
- Not tracked, must be supplied for a working setup: `.env` (from `.env.example`), `.agents.env` (from `.agents.env.example`), and everything under `data/cache/` above. `backup/` is scratch.

The science tasks have been run on Pi (`desy/reasoning`). OpenCode is wired up the same way but has not been run on them.

Running any task means pasting a copy of that task's `prompt_template.md` as the first message, with every `{{PLACEHOLDER}}` filled by hand from the source's row in `sources.csv` (title, Context, Given, Critical constraint, Deliverables). The unfilled template is never pasted. `prompts/system_prompt.md` (mounted as `/workspace/AGENTS.md`) loads automatically underneath. `ebl_absorption` is the exception: `prompt_joint.md` alone is already the complete message.

Only a subset of the corpus is ingested by `cognee_cloud_ingestion.py` (`documentation + examples + gammapy_paper + other_papers[:20]`). `cognee_ingestion.ipynb` builds `gammapy-cta-hgps` and `hess-papers`, the two datasets deployed in the live Docker volume today.

Documentation and examples aren't vendored by hand — the notebook sparse-clones `gammapy/gammapy` at the ref given in `resources.json`'s URLs. Changing which docs are ingested means editing the URLs, not the paths.

## Evaluating agent runs

Each agent's own `opencode/workspace/` or `pi/workspace/` is writable and gitignored, so a run's output has to be captured before the next run overwrites it. Three skills under `.agents/skills/` drive this cycle. `.agents/skills/` is the cross-tool Agent Skills location — Codex and Cursor discover it automatically; Claude Code does not, so open the `SKILL.md` files there directly. `run_archive/` is gitignored. The OpenCode steps need `sqlite3` on the host for its session database.

- `archive-agent-workspace` — copies a finished run's `src/`, `out/`, `paper/`, and session stats into `run_archive/<timestamp>/`, timestamped by the run's own end time, not when archiving happened.
- `clear-agent-workspace` — wipes `opencode/workspace/` or `pi/workspace/` so the next run starts clean.
- `write-run-breakdown` — turns one archive, for any task, into a `## Run N<n>` entry in `docs/run_breakdown.md`, comparing the agent's fitted values (from `out/results.json` only, never adjusted) against the HGPS catalog where it has a matching value. Position via `astropy.coordinates.angular_separation`; flux against whichever catalog field matches the source's spectral model.

## Git

The remote is Helmholtz Codebase GitLab, not GitHub. `gh` does not apply here. Work happens on `dev`.

## Things that bite

- `LLM_MODEL` needs an `openai/` prefix for LiteLLM routing. Anything calling Blablador directly has to strip that prefix back off first.
- `LITELLM_DROP_PARAMS=true` is required — the Blablador embedding endpoint rejects extra params.
- The DESY assistant is only reachable through a SOCKS proxy over the DESY SSH gateway, and `opencode`'s runtime only understands the HTTP proxy protocol, not raw SOCKS5 — `HTTPS_PROXY` in `.agents.env` points at a local `pproxy` bridge, not the SOCKS URL directly. `HTTP_PROXY` isn't needed since the DESY endpoint is `https://` only. Bring the bridge up on the host before running an agent against the DESY assistant: `pip install --user pproxy` once, then `ssh -D 1080 -N -f <your-user>@warp.zeuthen.desy.de && pproxy -l http://127.0.0.1:8889 -r socks5://127.0.0.1:1080`. Containers reach it as `host.docker.internal:8889` (`.agents.env`'s `HTTPS_PROXY`), the host as `127.0.0.1:8889`.
- Keep `HTTPS_PROXY` in `.agents.env` only. Cognee's own traffic never needs it, and `deploy/cognee/docker-compose.yml` blanks it for the Cognee services anyway. Add the MCP host to `NO_PROXY` (e.g. `.astroagent.zeuthen.desy.de`) so MCP calls skip the bridge.
- On WSL, keep Cognee storage on the native filesystem — `/mnt/c/...` is far slower.
- Graph visualization in the frontend needs `ENABLE_BACKEND_ACCESS_CONTROL=true` — cognee's own default when unset, but breaks if something ever sets it to `false`.
- `cognee-import` recomputes vectors on first run only, imports `gammapy-cta-hgps` and `hess-papers` separately, and skips each individually if it already has items.
- `cognee-import`'s custom entrypoint overrides the image's own startup script, which normally runs `alembic upgrade head` (or falls back to a setup script) to create the SQLite schema first. On a fully empty volume, skipping that fails with `sqlite3.OperationalError: unable to open database file` — the entrypoint runs that migrate step first as a guard.
- `cognee_cloud_ingestion.py` ingests into a dataset named `gammapy-plus` on the hosted Cognee tenant — a separate deployment from the live Docker volume, unrelated despite the name overlap.
- `COGNEE_MCP_TOOL_MODE=minimal` needs `cognee-mcp` >= 1.5.0; older images ignore it and expose all 11 tools. On 1.5.0 it exposes `remember`/`recall`/`forget` plus the `search_tools`/`call_tool` discovery pair.
- `cognee-mcp` is pinned to `1.5.0` while `cognee-backend`/`cognee-import` stay on `main-38eece5`. The MCP image talks to the backend over HTTP, never touching SQLite directly, which is why the skew works — bumping the backend image too breaks it (missing `data.dataset_id` column).
- Not every Blablador model reliably returns content within a modest token budget. `alias-muse` returns HTTP 200 with empty/null content regardless. `alias-large`, `alias-huge`, and `alias-glm-huge` are heavy reasoners that burn tokens on `<think>` output before answering — give them a large `max_tokens` (500+) or they'll look broken when they aren't. Both agents use `.agents.env`'s `AGENT_LLM_MODEL_ID`; `pi/settings.json`'s `retry` block sets only attempt count and backoff, not a model fallback. `alias-fast`/`alias-code` are the lighter confirmed-working Blablador models.
- `src/plot_ctao_allsky.py` accumulates counts and background directly into arrays instead of a whole-sky `MapDataset`, avoiding PSF/energy-dispersion maps sized to the whole sky.
- Python's `csv` module writes `\r\n` line endings by default even with `open(..., newline="")` — pass `lineterminator="\n"` explicitly.
- `deploy/cognee/docker-compose.yml`'s `cognee-backend` sets `CORS_ALLOWED_ORIGINS=*`, needed for the frontend on a subdomain-routed deployment (e.g. `*.astroagent.zeuthen.desy.de`) — without it the backend only allows `http://localhost:3000`, surfacing as a generic "Cannot connect to local Cognee backend" error.
- `cognee-mcp` needs two separate env vars for the same subdomain-routed deployment: `MCP_DISABLE_DNS_REBINDING_PROTECTION=true` (FastMCP's Host/Origin allowlist can never accept an `https` origin otherwise — hardcoded to build it as `http://`) and `MCP_CORS_ALLOW_ORIGINS=*` (a separate, independent `CORSMiddleware`; defaults to `localhost:3000` if unset). Both are needed together — either alone still fails.
- `NEXT_PUBLIC_LOCAL_API_URL` still has to be set per-deployment (browser-read, client-side, can't be a wildcard) — driven by `.env`'s `COGNEE_SERVICE_URL`, since cognee's own SDK already treats that as canonical for "where's my backend."
- `${VAR}` interpolation in a compose file resolves from the process environment or a `.env` in that compose's own directory, never from the `env_file:` directive. That's why the Cognee stack command passes `--env-file ../../.env` explicitly, so `${COMPOSE_PROJECT_NAME}` / `${COGNEE_EXPORT_PATH}` / the ports come from `.env` rather than their `:-` fallbacks. `${COGNEE_JWT}` has no fallback, so without the flag `cognee-mcp` starts with an empty token and gets 401s from the backend. The agent commands pass no `--env-file`, so `${CTAO_DATA_PATH}` / `${HGPS_PAPER_PATH}` / `${GAMMAPY_EBL_DATA_PATH}` use their fallbacks, which only match if `data/cache/` has the standard layout. Export them in the shell to mount something else (`CTAO_DATA_PATH` here is the folder above the DataStore, unlike in `.env`).
- No compose file sets `container_name`, so Compose auto-names containers and `docker compose down` from the compose's own directory clears them. `deploy/cognee/docker-compose.yml` sets the project name to `${COMPOSE_PROJECT_NAME:-gamma-aistronomer}`; `cognee_data` and `cognee_internal` carry no explicit `name:`, so they derive as `<project>_cognee_data` / `<project>_cognee_internal`. `opencode-compose.yml` and `pi-compose.yml` join no Cognee network. They reach MCP by URL only, so `COMPOSE_PROJECT_NAME` never affects them.
