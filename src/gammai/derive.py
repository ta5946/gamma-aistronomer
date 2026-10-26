"""Ask Cognee MCP for the dataset's science use cases, then how to do each one with Gammapy."""

import asyncio
import sys
from uuid import uuid4

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from gammai import describe_error, from_host, is_set, load_agents_env, repo_root

PROMPTS = "prompts/derive_use_cases"
# the headings docs/gammapy_use_cases.md uses for the two prompts
TITLES = [
    "Prompt 1: scientific use cases only",
    "Prompt 2: break each use case down into the Gammapy analysis it requires",
]
PLACEHOLDER = "{{LIST_OR_TABLE_OF_USE_CASES}}"
DATASET = "gammapy-cta-hgps"
# completion searches go through Cognee's own rate-limited LLM
TIMEOUT = 600


async def recall(session, query, search_type=None):
    # a fresh Cognee session per prompt, so Prompt 1's instructions don't leak into Prompt 2
    arguments = {"query": query, "datasets": DATASET, "session_id": f"gammai-derive-{uuid4()}"}
    if search_type:
        arguments["search_type"] = search_type
    async with asyncio.timeout(TIMEOUT):
        result = await session.call_tool("recall", arguments)
    text = "\n".join(c.text for c in result.content if c.type == "text").strip()
    if result.is_error:
        raise RuntimeError(text or "recall failed")
    return text


async def ask(url, prompts, show, search_type=None):
    """Send the prompts in order, Prompt 2 taking Prompt 1's answer, showing each as it comes."""
    answer = ""
    async with streamable_http_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for title, prompt in zip(TITLES, prompts):
                show(f"## {title}\n\n{prompt.strip()}\n")
                answer = await recall(session, prompt.replace(PLACEHOLDER, answer), search_type)
                show(f"{answer}\n")


def run(output=None, search_type=None):
    agents = load_agents_env()
    url = agents.get("COGNEE_MCP_URL", "")
    if not is_set(url):
        print("gammai: COGNEE_MCP_URL not set in .agents.env", file=sys.stderr)
        return 1
    prompts = [
        (repo_root() / PROMPTS / f"prompt_{n}.md").read_text(encoding="utf-8") for n in (1, 2)
    ]

    parts = []

    def show(text):
        parts.append(text)
        print(text, flush=True)

    try:
        asyncio.run(ask(from_host(url), prompts, show, search_type))
    except Exception as e:
        print(f"gammai: recall through {url} failed: {describe_error(e)}", file=sys.stderr)
        return 1

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write("\n".join(parts))
    return 0
