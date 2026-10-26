"""Check what an agent analysis run depends on: Python, .agents.env, data, Docker, LLM, Cognee MCP."""

import asyncio
import re
import shutil
import subprocess
from importlib.metadata import PackageNotFoundError, requires, version
from urllib.parse import urlparse

from gammapy.data import DataStore
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from openai import OpenAI

from gammai import describe_error, from_host, is_set, load_agents_env, repo_root

OK, WARN, FAIL = "ok", "warn", "FAIL"
AGENT_VARS = [
    "COGNEE_MCP_URL",
    "AGENT_LLM_ENDPOINT",
    "AGENT_LLM_API_KEY",
    "AGENT_LLM_MODEL_ID",
    "AGENT_LLM_MODEL_NAME",
]
# the default paths the agent compose files mount
CTAO_DATA = "data/cache/gammapy/ctao-data"
HGPS_PAPER = "data/cache/hgps/1804.02432.pdf"
EBL_TABLES = "data/cache/gammapy/gammapy-datasets/2.1/ebl"
TIMEOUT = 60
# inside a container these mean the container itself, not the host
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def check_python():
    matching = 0
    for requirement in requires("gammai") or []:
        match = re.match(r"([A-Za-z0-9_.-]+)==([^;\s]+)$", requirement)
        if not match:
            continue
        name, pinned = match.groups()
        try:
            installed = version(name)
        except PackageNotFoundError:
            yield FAIL, f"{name} not installed, run `pip install -e .`"
            continue
        if installed == pinned:
            matching += 1
        else:
            yield WARN, f"{name} {installed}, pinned {pinned}"
    yield OK, f"{matching} pinned dependencies installed at their pinned version"


def check_agents_env(agents):
    if not (repo_root() / ".agents.env").is_file():
        yield FAIL, ".agents.env missing, copy it from .agents.env.example"
        return
    for name in AGENT_VARS:
        value = agents.get(name)
        if not is_set(value):
            # the display name only labels the model in the picker
            status = WARN if name == "AGENT_LLM_MODEL_NAME" else FAIL
            yield status, f"{name} not set in .agents.env"
            continue
        host = urlparse(value).hostname if name.endswith(("_URL", "_ENDPOINT")) else None
        if host in LOCAL_HOSTS:
            yield WARN, (
                f"{name} points at {host}, the containers reach the host as host.docker.internal"
            )
        else:
            yield OK, name


def check_data():
    root = repo_root()
    stores = sorted((root / CTAO_DATA).rglob("hdu-index.fits.gz"))
    if not stores:
        yield FAIL, f"no DL3 DataStore (hdu-index.fits.gz) under {CTAO_DATA}/"
    for index in stores:
        path = index.parent.relative_to(root)
        try:
            store = DataStore.from_dir(index.parent)
            yield OK, f"DataStore {path}: {len(store.obs_table)} observations"
        except Exception as e:
            yield FAIL, f"DataStore {path} does not load: {e}"

    if (root / HGPS_PAPER).is_file():
        yield OK, HGPS_PAPER
    else:
        yield FAIL, f"{HGPS_PAPER} missing, run `cd src && python match_ctao_sources.py`"

    if (root / EBL_TABLES).is_dir():
        yield OK, EBL_TABLES
    else:
        yield WARN, f"{EBL_TABLES} missing, only ebl_absorption needs it"


def check_docker():
    if not shutil.which("docker"):
        yield FAIL, "docker not on PATH"
        return
    try:
        out = subprocess.run(
            ["docker", "compose", "version", "--short"],
            capture_output=True, text=True, timeout=TIMEOUT, check=True,
        )
        yield OK, f"docker compose {out.stdout.strip()}"
    except (subprocess.SubprocessError, OSError) as e:
        yield FAIL, f"docker compose not working: {e}"
        return
    # compose version works without the daemon, docker info needs it
    try:
        out = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True, text=True, timeout=TIMEOUT, check=True,
        )
        yield OK, f"Docker daemon {out.stdout.strip()} running"
    except (subprocess.SubprocessError, OSError):
        yield FAIL, "Docker is not running, start Docker Desktop or the docker service"


def check_llm(agents):
    endpoint, key, model = (
        agents.get(f"AGENT_LLM_{n}", "") for n in ("ENDPOINT", "API_KEY", "MODEL_ID")
    )
    if not all(is_set(v) for v in (endpoint, key, model)):
        yield FAIL, "skipped, AGENT_LLM_ENDPOINT, AGENT_LLM_API_KEY or AGENT_LLM_MODEL_ID not set"
        return
    client = OpenAI(base_url=from_host(endpoint), api_key=key, timeout=TIMEOUT, max_retries=0)
    try:
        reply = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with the word OK."}],
            max_tokens=100,
        )
        content = reply.choices[0].message.content or ""
    except Exception as e:
        yield FAIL, f"{model} at {endpoint}: {describe_error(e)}"
        return
    if content.strip():
        yield OK, f"{model} at {endpoint} answered {content.strip()[:40]!r}"
    else:
        yield WARN, f"{model} at {endpoint} answered with empty content"


async def list_mcp_tools(url):
    async with asyncio.timeout(TIMEOUT):
        async with streamable_http_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                info = await session.initialize()
                tools = await session.list_tools()
    return info.server_info, [t.name for t in tools.tools]


def check_mcp(agents):
    url = agents.get("COGNEE_MCP_URL", "")
    if not is_set(url):
        yield FAIL, "skipped, COGNEE_MCP_URL not set"
        return
    url = from_host(url)
    try:
        info, tools = asyncio.run(list_mcp_tools(url))
    except Exception as e:
        yield FAIL, f"{url}: {describe_error(e)}"
        return
    status = OK if "recall" in tools else FAIL
    yield status, f"{url}: {info.name} {info.version}, tools {', '.join(tools)}"


def run_checks():
    agents = load_agents_env()
    sections = [
        ("Python environment", check_python()),
        (".agents.env", check_agents_env(agents)),
        ("Data", check_data()),
        ("Docker", check_docker()),
        ("LLM", check_llm(agents)),
        ("Cognee MCP", check_mcp(agents)),
    ]
    failed = 0
    for title, results in sections:
        print(title)
        for status, message in results:
            failed += status == FAIL
            print(f"  [{status:>4}] {message}")
    print(f"\n{failed} check(s) failed" if failed else "\nall checks passed")
    return 1 if failed else 0
