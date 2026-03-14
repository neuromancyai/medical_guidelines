import asyncio
import json

from pathlib import Path

import aiohttp

from medical_guidelines.index import _ASSET_PATH
from medical_guidelines.esge import download_index
from medical_guidelines.utility import doi_to_file_name


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        esge_index = await download_index(session)

    index = {}

    for entry in esge_index:
        file_name = doi_to_file_name(entry.doi)
        md_path = _ASSET_PATH / "esge" / f"{file_name}.md"

        if not md_path.is_file():
            continue

        relative_path = md_path.relative_to(_ASSET_PATH)

        index[entry.doi] = {
            "id": entry.doi,
            "name": entry.name,
            "path": str(relative_path)
        }

    print(json.dumps(index, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
