import asyncio
import sys

import aiofiles

from elasticsearch import AsyncElasticsearch
from medical_guidelines import catalog


_MAPPINGS = {
    "properties": {
        "name": {"type": "text"},
        "content": {"type": "text"}
    }
}


async def main(url: str, index: str) -> None:
    entries = await catalog.load()
    client = AsyncElasticsearch(url)

    try:
        await client.indices.delete(index=index, ignore_unavailable=True)
        await client.indices.create(index=index, mappings=_MAPPINGS)

        for entry in entries.values():
            async with aiofiles.open(
                entry.path, "r", encoding="utf-8"
            ) as stream:
                content = await stream.read()

            await client.index(
                index=index,
                id=entry.id,
                document={
                    "name": entry.name,
                    "content": content
                }
            )

        await client.indices.refresh(index=index)

        count = await client.count(index=index)
        print(f"Indexed {count['count']} documents into '{index}'")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
