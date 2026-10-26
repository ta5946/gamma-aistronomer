"""Gamma AIstronomer command line tools."""

import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from dotenv import dotenv_values

try:
    __version__ = version("gammai")
except PackageNotFoundError:
    __version__ = "0.0.0"


def repo_root():
    """The repository checkout, found from the package (editable install) or the cwd."""
    package_root = Path(__file__).resolve().parents[2]
    if (package_root / "prompts" / "system_prompt.md").is_file():
        return package_root
    # cwd only as a fallback, it can be stale on WSL with the repo under /mnt/c
    cwd = Path.cwd().resolve()
    for path in [cwd, *cwd.parents]:
        if (path / "prompts" / "system_prompt.md").is_file():
            return path
    raise SystemExit("gammai: repository not found, run from inside the gamma-aistronomer checkout")


def is_set(value):
    """Set and not left as a .agents.env.example placeholder."""
    return bool(value) and "your-" not in value


def describe_error(e):
    """The innermost error, readable in one line."""
    while isinstance(e, BaseExceptionGroup):
        e = e.exceptions[0]
    response = getattr(e, "response", None)
    if response is not None and getattr(response, "status_code", None):
        return f"HTTP {response.status_code}"
    return str(e) or type(e).__name__


def from_host(url):
    """Containers reach the host as host.docker.internal, the host itself as 127.0.0.1."""
    return url.replace("host.docker.internal", "127.0.0.1")


def load_agents_env():
    """The set values from .agents.env, with its proxy settings applied the way the containers see them."""
    agents = {k: v for k, v in dotenv_values(repo_root() / ".agents.env").items() if v}
    for name in ("HTTPS_PROXY", "https_proxy", "NO_PROXY", "no_proxy"):
        os.environ.pop(name, None)
    if agents.get("HTTPS_PROXY"):
        os.environ["HTTPS_PROXY"] = from_host(agents["HTTPS_PROXY"])
    if agents.get("NO_PROXY"):
        os.environ["NO_PROXY"] = agents["NO_PROXY"]
    return agents
