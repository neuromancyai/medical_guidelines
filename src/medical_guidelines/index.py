from collections.abc import Mapping
from pathlib import Path

import aiofiles

from pydantic import BaseModel, TypeAdapter


_ASSET_PATH = Path(__file__).parent / "assets"
_ASSET_INDEX_PATH = _ASSET_PATH / "index.json"


class Entry(BaseModel):
    id: str
    name: str
    path: Path


type Index = Mapping[str, Entry]


async def load() -> Index:
    async with aiofiles.open(_ASSET_INDEX_PATH, "r") as stream:
        data = await stream.read()

    index = TypeAdapter(Index).validate_json(data)

    for entry in index.values():
        entry.path = _ASSET_PATH / entry.path

    return index
