---
name: clear-agent-workspace
description: Clear opencode/workspace/ or pi/workspace/ of everything the agent wrote in its last run, so the next run starts clean.
---

# Clear the agent workspace

## Why

`opencode/workspace/` and `pi/workspace/` are each harness's writable directory
(`working_dir: /workspace` in `opencode-compose.yml`; same mount pattern for `pi-compose.yml`), so
they fill up with whatever the agent produced: scripts, an `out/` directory (plot,
`results.json`, `report.md`), and the empty leftovers of the read-only mounts (`data/ctao-data/`,
`data/ebl/`, `paper/1804.02432.pdf`, `AGENTS.md`): Docker bind-mount points, never actually
populated on the host.
File and directory names can differ between runs, so don't assume exact names. Both are
gitignored, so nothing here needs preserving between runs.

## Steps

Figure out which harness's workspace to clear: a real run writes an `out/` directory, so it's
the one that has one. If both do, take the one the user asked for, or else the most recent. Then
list what's there first:

```bash
ls -ld opencode/workspace/out pi/workspace/out 2>/dev/null
find opencode/workspace pi/workspace -mindepth 1 2>/dev/null
```

Confirm any `data/...` subdirectory is empty (it should be — just a mount point, not real data).
If it's not empty, stop and check what's in there before deleting anything.

```bash
find opencode/workspace/data pi/workspace/data -type f 2>/dev/null | wc -l
```

Then clear everything under that `workspace/`, including dotfiles, keeping the directory itself
(it's the compose volume mount point):

```bash
(cd opencode && rm -rf workspace/* workspace/.[!.]*)   # OpenCode
(cd pi && rm -rf workspace/* workspace/.[!.]*)         # Pi
```
