import asyncio
import json

from pathlib import Path

import aiohttp

from medical_guidelines.catalog import _ASSET_PATH
from medical_guidelines.esge import download_catalog
from medical_guidelines.utility import doi_to_file_name


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        esge_catalog = await download_catalog(session)

    catalog = {}

    for entry in esge_catalog:
        file_name = doi_to_file_name(entry.doi)
        md_path = _ASSET_PATH / "esge" / f"{file_name}.md"

        if not md_path.is_file():
            continue

        relative_path = md_path.relative_to(_ASSET_PATH)

        catalog[entry.doi] = {
            "id": entry.doi,
            "name": entry.name,
            "path": str(relative_path)
        }

    print(json.dumps(catalog, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
