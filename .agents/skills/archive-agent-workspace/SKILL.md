---
name: archive-agent-workspace
description: Copy the current opencode/workspace/ or pi/workspace/ contents into a timestamped folder under run_archive/, so a run's output survives before the workspace gets cleared.
---

# Archive the agent workspace

## Why

`opencode/workspace/` and `pi/workspace/` both get cleared before every rerun (see the
`clear-agent-workspace` skill), which throws away the previous run's script, `out/` (plot,
`results.json`, `report.md`), and the harness's own session stats. Archiving first keeps a record
of a run worth coming back to, e.g. to compare against a later attempt. Not everything in
`workspace/` is worth keeping though: `data/` is just an empty Docker bind-mount point, and the
static task/config file the harness copied in isn't something the agent produced.

## Steps

Run these from the repository root. Figure out which harness produced the run: a real run writes an
`out/` directory, so check which of `opencode/workspace` or `pi/workspace` has one. If both do,
take the one the user asked for, or else the most recent.

```bash
ls -ld opencode/workspace/out pi/workspace/out 2>/dev/null
```

Copy everything into a timestamped folder under `run_archive/`, then drop the parts that aren't this
run's output. Name the folder after the run's own end time, not the moment you happen to run this
command — those can drift apart if archiving gets delayed.

### OpenCode

Timestamp comes from `session.time_updated` in `opencode.db`. Exclude the empty `data/` mount and
the static `AGENTS.md` task file:

```bash
timestamp=$(sqlite3 opencode/workspace/opencode_stats/opencode.db \
  "SELECT strftime('%Y%m%d_%H%M', MAX(time_updated)/1000, 'unixepoch', 'localtime') FROM session;")
mkdir -p run_archive/$timestamp
cp -r opencode/workspace/. run_archive/$timestamp/
rm -rf run_archive/$timestamp/data run_archive/$timestamp/AGENTS.md
cp data/cache/hgps/1804.02432.pdf run_archive/$timestamp/paper/1804.02432.pdf 2>/dev/null
```

### Pi

Timestamp comes from the last line's `timestamp` field in the run's own JSONL session log
(`pi_stats/--workspace--/*.jsonl`, one file per run), converted from UTC to local time. Exclude
the empty `data/` mount and the static `AGENTS.md` task file (mounted from
`prompts/system_prompt.md`, not agent output):

```bash
ls pi/workspace/pi_stats/--workspace--/*.jsonl   # expect exactly one; if more, stop and check why
jsonl=pi/workspace/pi_stats/--workspace--/<file>.jsonl
last_ts=$(tail -1 "$jsonl" | python3 -c "import json,sys; print(json.load(sys.stdin)['timestamp'])")
timestamp=$(date -d "$last_ts" +%Y%m%d_%H%M)
mkdir -p run_archive/$timestamp
cp -r pi/workspace/. run_archive/$timestamp/
rm -rf run_archive/$timestamp/data run_archive/$timestamp/AGENTS.md
cp data/cache/hgps/1804.02432.pdf run_archive/$timestamp/paper/1804.02432.pdf 2>/dev/null
```

Confirm what landed there:

```bash
find run_archive/$timestamp -mindepth 1
```

### Another harness

Same pattern: the timestamp is the end time in the run's own session log, copy
`<harness>/workspace/.`, then drop `data/` and anything else its compose file mounts in that the
agent didn't produce (config, `AGENTS.md`). Add a section here for it once it works.
