"""Import the prebuilt cogx archives into the live cognee volume.

Mounted into the cognee-import container and run once at stack startup. Each
dataset in DATASET_NAMES is imported from /import/<name> unless it already has
items, so re-running the stack skips it. A dataset whose import failed halfway
is skipped too: delete it, or start from an empty volume, to import it again.
"""

import asyncio

import cognee
from cognee.modules.migration.sources.cogx_archive import COGXArchiveSource

DATASET_NAMES = ["gammapy-cta-hgps", "hess-papers"]


async def main():
    datasets = await cognee.datasets.list_datasets()
    for name in DATASET_NAMES:
        existing = next((d for d in datasets if d.name == name), None)
        if existing:
            items = await cognee.datasets.list_data(existing.id)
            if items:
                print(f"{name} already has {len(items)} items, skipping import")
                continue

        result = await cognee.remember(
            COGXArchiveSource(f"/import/{name}", mode="preserve"),
            dataset_name=name,
        )
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
