"""Cognee Cloud

A reduced version of the `cognee.remember()` ingestion in `cognee_ingestion.ipynb`: the Gammapy
docs, examples and paper plus the first 20 related papers, into its own dataset on the hosted
https://platform.cognee.ai/ tenant instead of local storage.

`cognee.serve(url=..., api_key=...)` connects the SDK to it; every cognee call below runs
there instead of locally, until `cognee.disconnect()`. Credentials come from `.env`.

    cd src && python cognee_cloud_ingestion.py
"""

import asyncio
import json
import os

import cognee
from cognee.api.v1.serve.state import get_remote_client
from dotenv import load_dotenv
from tqdm import tqdm

INGEST_DATASET_NAME = "gammapy-plus"  # ingested below
RESOURCES_FILE = "../data/resources.json"


# remote remember needs file objects, not path strings
def open_files(path):
    if not os.path.isdir(path):  # is a file
        return [open(path, "rb")]

    files = []
    for root, _, names in os.walk(path):
        files.extend(open(os.path.join(root, name), "rb") for name in names)
    return files


async def main():
    load_dotenv()
    SERVICE_URL = os.environ["COGNEE_CLOUD_SERVICE_URL"]
    USER_ID = os.environ["COGNEE_CLOUD_USER_ID"]  # dashboard user, for permissions
    API_KEY = os.environ["COGNEE_CLOUD_API_KEY"]

    await cognee.serve(url=SERVICE_URL, api_key=API_KEY)

    # no dataset list call in SDK yet, use client session to call the API
    client = get_remote_client()
    session = await client._get_session()
    async with session.get(f"{client.service_url}/api/v1/datasets") as response:
        for dataset in await response.json():
            print(dataset["name"], dataset["id"])

    # Vectorstore configuration
    # No /api/v1/settings here (404), so nothing is confirmable via the API. Per cognee's
    # defaults: LLM openai/gpt-5-mini, embeddings openai/text-embedding-3-large, vector
    # store LanceDB.

    with open(RESOURCES_FILE, "r") as f:
        resources = json.load(f)

    # already downloaded by cognee_ingestion.ipynb, just point at local files
    PAPERS_DIR = "../data/cache/ingestion/related_papers"
    for paper in resources["related_papers"]:
        arxiv_id = paper["url"].rsplit("/", 1)[-1]
        paper["local_path"] = os.path.join(PAPERS_DIR, f"{arxiv_id}.pdf")

    for group in ["documentation", "examples"]:
        group_dir = f"../data/cache/ingestion/{group}"
        for item in resources[group]:
            folder_path = "/".join(item["url"].split("/")[7:])
            item["local_path"] = os.path.join(group_dir, os.path.basename(folder_path))

    # ingest only a subset of papers
    # the Gammapy paper itself belongs with the docs/examples, not the other related_papers
    gammapy_paper = [p for p in resources["related_papers"] if p["url"].endswith("2308.13584")]
    other_papers = [p for p in resources["related_papers"] if p not in gammapy_paper]

    items = resources["documentation"] + resources["examples"] + gammapy_paper + other_papers[:20]

    # reproducible as cognee uses LLM temperature = 0
    for item in tqdm(items, desc="Ingesting items"):
        files = open_files(item["local_path"])
        try:
            await cognee.remember(
                files,
                dataset_name=INGEST_DATASET_NAME,
                node_set=item["sets"],
                self_improvement=False,
                # per https://docs.cognee.ai/core-concepts/main-operations/remember#latency-and-cost
                run_in_background=False,  # default value, define explicitly anyway
            )
        finally:
            for f in files:
                f.close()

    # takes 1 hour, costs 10 dollars

    # the dataset id the permission calls need
    async with session.get(f"{client.service_url}/api/v1/datasets") as response:
        dataset_id = next(d["id"] for d in await response.json() if d["name"] == INGEST_DATASET_NAME)

    # datasets created by API are not visible to the dashboard user by default
    for permission in ["read", "write", "delete", "share"]:
        response = await session.post(
            f"{client.service_url}/api/v1/permissions/datasets/{USER_ID}",
            params={"permission_name": permission},
            json=[dataset_id],
        )
        print(permission, response.status)

    # show ingested items with the API
    response = await session.get(f"{client.service_url}/api/v1/datasets/{dataset_id}/data")
    print("Ingested items:")
    for data_item in await response.json():
        print(data_item["name"])

    # close connection to Cognee Cloud
    await cognee.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
