"""Run an agent harness container, the same way the README's compose commands do."""

import shutil
import subprocess
import sys

from gammai import repo_root

# compose file, one-shot arguments before the prompt, session stats dir in the workspace
HARNESSES = {
    "pi": ("pi-compose.yml", ["-p"], "pi_stats"),
    "opencode": ("opencode-compose.yml", ["run"], "opencode_stats"),
}
# bind-mount targets Docker leaves behind in the workspace, not run output
MOUNT_POINTS = {"AGENTS.md", "data", "paper"}


def leftovers(harness):
    workspace = repo_root() / harness / "workspace"
    stats = HARNESSES[harness][2]
    if not workspace.is_dir():
        return []
    found = []
    for entry in sorted(workspace.iterdir()):
        if entry.name in MOUNT_POINTS:
            continue
        if entry.name == stats and not any(entry.iterdir()):
            continue
        found.append(entry.name)
    return found


def run(harness, prompt=None, force=False):
    """Interactive session without a prompt, one-shot run with one."""
    compose, one_shot, _ = HARNESSES[harness]
    if not shutil.which("docker"):
        print("gammai: docker not on PATH", file=sys.stderr)
        return 1

    found = leftovers(harness)
    if found and not force:
        print(
            f"gammai: {harness}/workspace/ still holds {', '.join(found)} from an earlier run.\n"
            "Archive it with the archive-agent-workspace skill, clear it with "
            "clear-agent-workspace, or pass --force to run on top of it.",
            file=sys.stderr,
        )
        return 1

    command = ["docker", "compose", "-f", compose, "run", "--rm", "--build"]
    command += ["-it", harness] if prompt is None else [harness, *one_shot, prompt]
    return subprocess.run(command, cwd=repo_root() / harness).returncode
