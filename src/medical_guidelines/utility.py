from pathlib import Path

import aiofiles
import aiohttp

from yarl import URL


_BUFFER_SIZE = 8192


def doi_to_file_name(doi: str) -> str:
    return doi.replace("/", "_").replace(".", "_").replace("-", "_")


async def download_file(
    url: URL,
    path: Path,
    session: aiohttp.ClientSession
) -> None:
    async with session.get(url) as response:
        response.raise_for_status()
        async with aiofiles.open(path, "wb") as stream:
            async for chunk in response.content.iter_chunked(_BUFFER_SIZE):
                await stream.write(chunk)
