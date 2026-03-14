from collections.abc import Mapping
from pathlib import Path

import aiofiles

from pydantic import BaseModel, TypeAdapter


_ASSET_PATH = Path(__file__).parent / "assets"
_ASSET_CATALOG_PATH = _ASSET_PATH / "catalog.json"


class CatalogEntry(BaseModel):
    id: str
    name: str
    path: Path


type Catalog = Mapping[str, CatalogEntry]


async def load() -> Catalog:
    async with aiofiles.open(_ASSET_CATALOG_PATH, "r") as stream:
        data = await stream.read()

    catalog = TypeAdapter(Catalog).validate_json(data)

    for entry in catalog.values():
        entry.path = _ASSET_PATH / entry.path

    return catalog
